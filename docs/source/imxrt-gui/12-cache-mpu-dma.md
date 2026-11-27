# 第 12 篇：Cache、MPU 与 DMA 一致性

> 系列：[i.MX RT 图形系统实战](README.md)
>
> 上一篇：[单缓冲、双缓冲与撕裂控制](11-buffering-and-tearing.md)
>
> 下一篇：[认识 PXP——它能加速什么，不能加速什么？](13-pxp-capabilities.md)
>
> 本篇目标：按数据方向设计缓存维护，防止旧像素、脏行回写和边界数据破坏。以 Cortex-M7 非一致性外设访问为模型，其他内核及缓存层另行核对。

## 1. CPU 看见新像素，为什么外设仍读旧数据？

在写回缓存中，CPU 更新的数据可能只在 D-Cache，尚未写回外部内存。

DMA、显示控制器或加速器若不通过一致性路径，就可能读取旧 RAM。

反过来，硬件写入 RAM 后，CPU 可能仍命中旧缓存。

```text
CPU <-> D-Cache <-> RAM <-> DMA / 显示 / 加速器
```

`volatile` 不会把脏缓存写回，也不会保证硬件完成。互斥锁保护软件并发，同样不自动解决设备可见性。

## 2. 三种维护操作

| 操作 | 主要作用 | 风险 |
| --- | --- | --- |
| Clean | 把脏缓存写回 RAM | 不等待外设任务完成 |
| Invalidate | 使缓存行无效，下次重新读 | 可能丢弃未写回 CPU 数据 |
| Clean + Invalidate | 先写回，再失效 | 时机错误会覆盖硬件刚写的新数据 |

不要把这些操作当作可以随意互换的“刷新 Cache”。

维护 API 的地址、长度、屏障与对齐规则，以所用 CMSIS/SDK 为准。M7 的常见缓存行为 32 B；其他架构不沿用这个常量。

## 3. CPU 写，硬件读

典型交接：

```text
CPU 独占写入
   -> Clean 相关完整缓存行
   -> 按 SDK 要求完成屏障
   -> 提交外设读取
   -> CPU 不修改该区域
   -> 确认消费者释放
   -> 才能再次写入
```

CPU 没有再次写脏的同一份只读资源，不一定需要每次重复 Clean。是否能省略要由明确的修改记录和路径证明。

对帧缓冲 Clean 之后立即继续绘制，仍可能与扫描冲突；缓存维护不是缓冲区锁。

## 4. 硬件写，CPU 读

一条保守的共享缓存区策略是：

1. CPU 交出整个相关缓存行的拥有权。
2. 硬件开始前处理目标脏行，通常使用适当的 Clean + Invalidate。
3. 硬件运行期间 CPU 不访问目标及共享边界行。
4. 确认硬件写入真正完成。
5. CPU 读取前 Invalidate，丢弃可能残留或重新装入的旧副本。

若完整覆盖独占缓存行、无需保留旧内容，可以根据 SDK 改用不同的前置策略；不能把这种优化推广到部分写入或共享行。

**硬件完成后盲目 Clean 目标区，可能把旧脏缓存覆盖到新结果上。**

## 5. 边界比想象中重要

缓存维护按行进行，不按像素进行。

一个 60 B 区域从地址末尾偏移 3 B 处开始，可能涉及两个 32 B 缓存行。

如果边界行还放了其他变量，Invalidate 可能丢数据，Clean 也可能回写不该由当前拥有者修改的内容。

最简单的设计通常是让设备缓冲区独占完整缓存行，首地址与分配大小都满足隔离。

矩形区域还涉及 stride。不能把 `width × height × bytes` 当作带 padding 图像中一定连续的缓存范围。

可以逐行维护并处理重复边界，也可以维护包含 padding 的完整独占范围；两者成本不同。

## 6. 离线计算维护范围

下面只是算术，不访问真正内存，也不替代安全分配：

```python
address = 0x20200003
size = 60
line_size = 32

if size <= 0 or line_size <= 0 or line_size & (line_size - 1):
    raise ValueError("Use a positive size and a power-of-two cache line.")

start = address - address % line_size
end = ((address + size + line_size - 1) // line_size) * line_size

print(f"Requested: 0x{address:08X}, {size} B")
print(f"Envelope: 0x{start:08X}..0x{end:08X} (exclusive end)")
print(f"Maintenance length: {end - start} B")
```

输出：

```text
Requested: 0x20200003, 60 B
Envelope: 0x20200000..0x20200040 (exclusive end)
Maintenance length: 64 B
```

实际 C 代码还要检查地址加法溢出、API 长度范围和维护区域是否归调用者所有，不能只复制取整公式。

## 7. MPU：描述属性，不是制造一致性

MPU 可以帮助设置内存访问和缓存属性，但它不能改变外设的物理可达性。

配置需要同时考虑：

- 区域大小、基址、优先级和覆盖关系。
- Normal/Device 等内存类型。
- 可缓存、可缓冲、共享和访问权限。
- CPU、其他核心和外设的实际访问路径。

不能认为把 shareable 置位就自动让任意 DMA 与 CPU 一致。

动态改变属性前，应停止相关访问并按架构要求处理缓存及屏障。避免通过不同属性别名同时访问同一物理内存。

## 8. Cached 与 Non-cacheable 如何选？

| 方案 | 优点 | 代价 |
| --- | --- | --- |
| 不可缓存像素缓冲 | CPU/设备交接更直观 | CPU 读写可能较慢 |
| 可缓存缓冲＋范围维护 | CPU 绘制可能更快 | 维护、隔离、生命周期复杂 |
| 资源可缓存、设备缓冲独立 | 各自优化 | 布局和数据移动要预算 |

先建立正确基线，再比较整帧时间、CPU 占用和带宽。不能以一个 CPU 填充测试判断整体最优。

GPU 或 SDK 还可能自带缓存维护钩子。核对谁维护哪些范围，避免遗漏或重复，也不能覆盖驱动已经建立的拥有权。

## 9. 对照实验与小结

用相同地址、格式和图案对比：

- CPU 写后设备读取。
- 设备写后 CPU 校验。
- 非整行区域与独占完整行。
- 多次交替图案与长时间运行。

若缓存属性改变使故障消失，它只是线索；应继续验证方向、范围和时机。

下一篇：[《认识 PXP——它能加速什么，不能加速什么？》](13-pxp-capabilities.md)。正确的数据交接是加速的基础。

## 参考资料

- [CMSIS Cortex-M7 D-Cache API](https://arm-software.github.io/CMSIS_6/main/Core/group__Dcache__functions__m7.html)
- [NXP RT1170 资料入口](https://www.nxp.com/products/i.MX-RT1170)
- [LVGL 9.2 PXP 缓冲处理](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/pxp/lv_draw_buf_pxp.c)
