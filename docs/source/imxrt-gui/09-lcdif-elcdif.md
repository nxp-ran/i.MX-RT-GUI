# 第 9 篇：LCDIF / eLCDIF 等显示控制器如何工作？

> 系列：[从点亮屏幕到高性能 GUI：i.MX RT 图形系统实战](README.md)
>
> 上一篇：[一套可复用的屏幕点亮与排障流程](08-display-bring-up.md)
>
> 下一篇：[GUI 为什么离不开存储系统？](10-memory-system.md)
>
> 本篇目标：沿“内存读取 → 格式解释 → FIFO → 时序输出”理解显示控制器，并分清帧地址提交、事件通知和安全复用。
>
> 适用范围：以公开 eLCDIF 与 LCDIFv2 驱动及示例为参考，不把它们视为所有 i.MX RT 的统一 IP。地址与带宽算例是软件模型，不是可直接用于板卡的内存布局。

## 1. 显示控制器不是 GUI 绘制引擎

应用决定显示什么，CPU、PXP 或 GPU 生成像素，显示控制器负责把已有内容按要求输出。

在典型扫描方案中：

```text
帧缓冲区
    |
    v
读取请求与总线访问
    |
    v
像素格式解释
    |
    v
FIFO / 受支持的图层合成
    |
    v
像素时序与输出
    |
    v
RGB 接口或后续 DSI 路径
```

部分控制器有合成、颜色转换或 LUT，并不因此变成能够理解按钮、排版和事件的 GUI 框架。

扫描期间完成的合成，也不等于在内存中生成了一张新的合成帧。

## 2. 名称相近，不代表编程模型相同

| 参考路径 | 本次公开接口体现的特点 | 不能据此推断 |
| --- | --- | --- |
| eLCDIF RGB | 整体时序、像素格式、帧地址与下一帧地址 | 任意 stride、多层或所有格式都可用 |
| eLCDIF 的可选扩展 | 目标相关的 Alpha surface、LUT 等 | 每个型号都有这些能力 |
| LCDIFv2 | 显示时序与层配置分开、层 stride、地址和 shadow load | 任意 SKU 支持完全相同的层与操作 |
| DSI Host | 接收像素并组织串行传输 | 替代显示控制器读取全部图像 |

SDK 可能把硬件称为 LCDIF，而驱动名是 eLCDIF；也可能同一芯片同时包含不同版本模块。

选择代码时应确定：

- 完整器件型号与目标内核。
- 外设实例和寄存器定义。
- 对应驱动变体。
- 输出路径与板级视频路由。
- 当前 SDK 的支持条件。

不能只搜索到 `LCDIF` 这个名字就混用两套函数。

## 3. 控制器怎样从地址找到一行像素？

对本篇的普通 RGB565 模型：

```text
pixel_address(x, y) = base + y × stride + x × 2
```

控制器还需要知道尺寸、格式以及有效输出范围。

| 参数 | 影响 |
| --- | --- |
| 基地址 | 从哪里读取 |
| 像素格式 | 怎样解释内存位与字节 |
| 有效尺寸 | 每行、每帧需要多少像素 |
| stride | 下一行从哪里开始，若该模式可配置 |
| 对齐 | 地址是否满足访问与接口要求 |
| 可达性 | 控制器能否访问目标内存 |

软件中有一个有效指针，不代表外设看到的地址含义完全相同。SDK 可能提供 CPU 到 IP 地址转换，应沿用相应机制。

尤其不要把 PC 上的地址模型，或另一型号上的 RAM 起始地址直接复制到嵌入式工程。

## 4. 源格式和输出格式要分别理解

本次 eLCDIF 接口列出了 RGB565、紧凑 RGB888、XRGB8888 等源格式，并独立设置输出总线。

这些格式在内存中不同：

| 源格式 | 本篇容量模型 |
| --- | --- |
| RGB565 | 2 B/pixel |
| RGB888 紧凑排列 | 3 B/pixel |
| XRGB8888 | 4 B/pixel，最高字段不作为有效 Alpha |

格式转换或位映射发生在哪里，取决于具体控制器路径。

一个上层称为“RGB888”的参数，也可能在另一个接口中表示 32 位容器，不能靠相同名字认定布局一致。

验证时用彩色、不同强度和位置图案，检查源内容、控制器解释和实际输出是否一致。

## 5. FIFO 的作用，是缓冲延迟而不是创造带宽

控制器从总线成批读取，再按像素时钟消耗数据。

```text
突发读取 -> FIFO 中暂存 -> 按输出时序逐像素消耗
```

这使总线不必精确地在每个 PCLK 边沿交付数据，但仍需足够及时地补充 FIFO。

当 CPU、PXP、GPU、DMA 或其他外设共享存储时，可能出现：

- 平均带宽不够。
- 某些访问阶段的延迟过长。
- 读取地址无效或权限不匹配。
- 输入与输出时序配置不一致。

eLCDIF 与 LCDIFv2 的公开接口提供了不同的欠载、FIFO 和总线/层 DMA 异常状态。应按目标定义记录，而不是把它们统称为“画面错误”。

增加 FIFO 使用率或仲裁优先级可能改变表现，但不能代替核对容量、访问路径和持续负载。

## 6. 从“设置下一帧”到“实际开始显示”

### 6.1 eLCDIF 路径

公开接口中的 `ELCDIF_SetNextBufferAddr()` 设置下一帧地址，不是立即拷贝图像。

提交前，应确保这块帧数据完整、可达、对控制器可见且未被其他生产者改写。

### 6.2 LCDIFv2 路径

公开 LCDIFv2 接口把层缓冲地址与 shadow load 分开：

```text
更新层缓冲配置
      |
      v
请求 shadow load
      |
      v
控制器在规定的帧边界装入有效配置
```

本次引用的驱动说明，shadow 控制寄存器在下一帧 VSYNC 更新到有效寄存器。

这不意味着任何代码调用、任意中断到来或任意时刻的读取都能证明切换已经完成。

### 6.3 不要混用两种更新方法

eLCDIF 的下一地址寄存器，与 LCDIFv2 的层 shadow 机制，是不同的编程模型。

不要照抄另一控制器的初始化、事件判断和释放顺序。

## 7. 一个可靠的双帧状态模型

假设 A 正在显示、B 可供绘制：

```text
A: SCANNING
B: FREE -> DRAWING -> READY -> PENDING

确认 B 的配置已按目标机制生效，
并确认 A 不再被相关读取路径访问：

B: SCANNING
A: FREE
```

这只是软件职责模型。具体确认机制需由控制器手册、驱动和端口共同定义。

几个常见陷阱：

- 写完 B 的地址就立即覆盖 A。
- 把一次正常 VSYNC 当作 B 一定已生效。
- 请求未赶上某个边界，却提前释放旧帧。
- 等待标志在提交之后才清零，丢失已经发生的事件。
- 多个提交覆盖了唯一 pending 状态。

建议由一个明确的拥有者管理提交序号、当前帧、待显示帧和释放条件。

不要在中断、GUI 任务和其他业务任务中各自维护一套互不一致的状态。

## 8. 中断应该告诉我们什么？

| 事件类型 | 可提供的证据 | 不应自动当作 |
| --- | --- | --- |
| VSYNC 边沿 | 某个同步时刻发生 | 所有新配置已应用 |
| 进入垂直消隐 | 扫描进入相关阶段 | 面板响应完成 |
| 层读取或 DMA 事件 | 某段内存访问相关状态 | 全部图像已经可见 |
| FIFO 欠载 | 供数或时序存在异常 | 普通帧完成 |
| 总线/层 DMA 错误 | 地址、权限或访问失败 | 可以继续复用所有缓冲 |

本次 eLCDIF 驱动把 `CurFrameDone` 描述为进入垂直消隐；LCDIFv2 也独立定义垂直消隐和 VSYNC 事件。

事件名字里的“Done”不能替代实际语义分析。

中断处理的一般原则是：

1. 读取相关状态快照。
2. 分开处理正常和错误事件。
3. 按 SDK 规则确认/清除状态。
4. 更新受同步保护的状态或通知拥有者。
5. 在任务中处理耗时工作和错误恢复。

中断打印、临界区和通知方式也会影响时间线，必须与目标 RTOS 规则一致。

## 9. 图层合成，不等于免费绘制

受支持的 LCDIFv2 路径可以读取多个层，按格式与 Alpha 配置合成输出。

| 方式 | 工作发生的位置 | 主要代价 |
| --- | --- | --- |
| CPU/PXP/GPU 预合成 | 输出前生成内存结果 | 读取源、写入目标与同步 |
| 显示控制器扫描合成 | 扫描时读取层并合成输出 | 每轮扫描读取多个层 |

例如，假设：

- 主层 800 × 480，RGB565，60 Hz。
- 覆盖层 200 × 100，ARGB8888，60 Hz。
- 两层都按其有效区域读取，不计额外事务。

有效读取量级：

```text
主层：800 × 480 × 2 × 60 = 46.08 MB/s
覆盖层：200 × 100 × 4 × 60 = 4.80 MB/s
合计：50.88 MB/s
```

图层可以避免某些预合成操作，但不能消除层读取带宽。

层数、支持格式、Alpha 语义、更新时机与裁剪行为都要按目标 IP 核对，不根据通用驱动中出现的枚举数量宣称全部芯片支持。

## 10. 用离线模型检查帧布局

下面假设一块完整 RGB565 帧，行跨度 1,600 B，帧起始位置按本例选择的 64 B 对齐。

地址 `0x80000000` 只是算术示例，不是目标板卡的地址建议。

```python
width, height = 800, 480
bytes_per_pixel = 2
stride = 1600
alignment = 64
base = 0x80000000

if stride < width * bytes_per_pixel or base % alignment:
    raise ValueError("The assumed frame layout is invalid.")

frame_bytes = stride * height
allocation_step = ((frame_bytes + alignment - 1) // alignment) * alignment
second_base = base + allocation_step
last_pixel = base + (height - 1) * stride + (width - 1) * bytes_per_pixel
region_pixel = base + 30 * stride + 20 * bytes_per_pixel

print(f"Frame bytes: {frame_bytes:,}")
print(f"Buffer A: 0x{base:08X}")
print(f"Buffer B: 0x{second_base:08X}")
print(f"Last pixel in A: 0x{last_pixel:08X}")
print(f"Pixel (20, 30): 0x{region_pixel:08X}")
```

输出：

```text
Frame bytes: 768,000
Buffer A: 0x80000000
Buffer B: 0x800BB800
Last pixel in A: 0x800BB7FE
Pixel (20, 30): 0x8000BBA8
```

最后一个像素的起始地址还要容纳完整的 2 B；它不是整块内存的结束边界。

板卡上还要验证物理容量、链接布局、IP 地址转换和实际对齐要求；脚本不能替代这些检查。

## 11. 正确读 SDK 示例的方法

公开示例给出了以下有价值的路线：

- eLCDIF RGB：完整帧生成、下一地址和相关帧事件。
- LCDIFv2 RGB565：层配置、缓冲地址和 shadow load。
- RT1170 板级支持：存储、时钟、面板和 DSI 路由。

阅读时分别找出：

1. 帧缓冲在哪里分配。
2. Cache 属性如何设置。
3. 何时生成内容。
4. 哪个 API 提交新内容。
5. 哪个事件结束等待。
6. 示例为了简单省略了哪些超时、错误和并发处理。

不要把示例中的忙等直接作为多任务产品架构，也不要假定其事件处理能覆盖所有提交时机。

## 12. 三组验证比一个 FPS 更有价值

| 验证 | 方法 | 主要结论 |
| --- | --- | --- |
| 固定扫描 | 单个已知完整帧与正常时序 | 读取、格式、输出基本正确 |
| 交替提交 | 两帧明显不同，记录序号与地址事件 | 更新机制与释放条件可靠 |
| 综合负载 | 加入绘制、资源、其他总线主设备 | 带宽与同步是否稳定 |

记录实际像素时钟、正常事件频率、异常计数、提交等待和 CPU 成本。

显示以 60 Hz 扫描，不证明 GUI 每秒生成 60 张新画面；帧边界中断频率也不能代替可见更新测量。

## 13. 小结

显示控制器连接了两种节奏：

- 存储系统以可变延迟和突发方式交付数据。
- 面板按固定时序消耗像素。

理解这条连接，需要同时掌握布局、格式、FIFO、事件和更新机制。

“设置下一帧”是提交意图；“事件到来”提供阶段证据；“旧帧可复用”必须满足完整的所有权条件。

下一篇：[《GUI 为什么离不开存储系统？》](10-memory-system.md)。我们将进一步讨论 RAM、外部存储、资源布局和访问竞争。

## 参考资料

- [NXP eLCDIF 驱动接口](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/elcdif/fsl_elcdif.h)
- [NXP eLCDIF RGB 初始化实现](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/elcdif/fsl_elcdif.c)
- [NXP LCDIFv2 驱动接口](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/lcdifv2/fsl_lcdifv2.h)
- [NXP eLCDIF RGB 示例](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/elcdif/rgb/elcdif_rgb.c)
- [NXP LCDIFv2 RGB565 示例](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/lcdifv2/rgb565/lcdifv2_rgb565.c)

资料固定到公开提交用于说明具体接口，最终能力与事件语义应以目标芯片手册、勘误和所用 SDK 为准。
