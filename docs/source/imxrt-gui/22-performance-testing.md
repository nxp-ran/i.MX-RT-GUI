# 第 22 篇：建立可信的 GUI 性能测试方法

> 系列：[i.MX RT 图形系统实战](README.md)
>
> 上一篇：[图片、字体与中文界面的工程化](21-images-fonts.md)
>
> 下一篇：[从瓶颈出发优化，而不是盲目开加速](23-bottleneck-optimization.md)
>
> 本篇目标：明确测量边界和统计方法，让性能结论可复现。脚本数据为人为样本，不是任何开发板测量。

## 1. 先定义“帧”

GUI 可以按块刷新，也可以完整换帧。软件请求、绘制任务、flush 和实际扫描是不同事件。

| 指标 | 定义要求 |
| --- | --- |
| 面板刷新率 | 面板扫描周期 |
| GUI 更新吞吐 | 完成一轮有效更新的频率 |
| 可见新帧率 | 实际显示不同内容的频率 |
| 输入延迟 | 输入到指定区域可见变化 |
| CPU 占用 | 采样区间和统计方法 |

一次整屏分成多个 flush，不能把块数作为帧数；重复扫描旧帧也不能算成新内容。

## 2. 固定工作负载

至少记录：

- 分辨率、像素格式、stride 和缓冲模式。
- 页面、动画、更新面积、图片与字体。
- SDK、LVGL、驱动、编译器和优化。
- CPU/内存/显示/加速器实际时钟。
- Cache/MPU、内存区域和业务负载。
- 输出质量、滤波与 Alpha 语义。

软件与硬件对照必须使用等价工作，不把简化阴影或不同滤波当作免费收益。

## 3. 分段计时，保留关键路径

```text
输入
 -> 事件处理
 -> 绘制提交
 -> 绘制执行完成
 -> 显示传输/换帧请求
 -> 实际激活
 -> 区域扫描与面板响应
```

记录提交与完成两个时间。GPU API 返回可能只完成入队。

不要把能够重叠的时间段简单相加当作总延迟；使用请求编号把事件关联成同一条关键路径。

## 4. 时间源与测量开销

可使用平台高精度计时器、允许的周期计数或 GPIO 标记。

注意：

- 计数器回绕、频率改变和睡眠期间行为。
- 中断与任务上下文读取的原子性。
- 计时器单位与转换。
- 打印、探针和追踪本身的开销。

周期数除以 CPU 频率只适用于对应计数条件，不自动代表包括睡眠和外设等待的墙钟时间。

## 5. 平均值之外要看分布

平均帧率可以掩盖周期性卡顿，应报告：

- 样本数与采样时长。
- 平均、中位数、指定分位与最大值。
- 期限错过次数、丢帧和重复。
- 错误与恢复事件。

分位计算有不同方法，必须注明。小样本 p95 常接近最大值，不代表已充分刻画长尾。

## 6. 人为样本的统计脚本

这里用 nearest-rank 定义分位数，样本是完成更新间隔：

```python
from math import ceil
from statistics import mean, median

intervals_ms = [16, 17, 16, 20, 18, 16, 17, 25, 16, 19]
if not intervals_ms or any(value <= 0 for value in intervals_ms):
    raise ValueError("Completed-update intervals must be positive.")

ordered = sorted(intervals_ms)
p95 = ordered[ceil(0.95 * len(ordered)) - 1]
deadline = 1000 / 60
misses = sum(value > deadline for value in intervals_ms)
rate = len(intervals_ms) * 1000 / sum(intervals_ms)

print(f"Samples: {len(intervals_ms)}")
print(f"Mean/median: {mean(intervals_ms):.2f}/{median(intervals_ms):.2f} ms")
print(f"p95/max: {p95:.2f}/{max(intervals_ms):.2f} ms")
print(f"Completed-update rate: {rate:.2f}/s")
print(f"Intervals above 60 Hz budget: {misses}/{len(intervals_ms)}")
```

输出：

```text
Samples: 10
Mean/median: 18.00/17.00 ms
p95/max: 25.00/25.00 ms
Completed-update rate: 55.56/s
Intervals above 60 Hz budget: 6/10
```

如果输入是单次绘制耗时而不是完成间隔，就不能用同一个公式声称获得可见帧率。

## 7. CPU、内存和带宽

| 指标 | 验证方法 |
| --- | --- |
| CPU 忙时间 | RTOS 运行统计或可解释采样 |
| 堆/栈峰值 | 最坏场景与相应分配器统计 |
| 接口有效吞吐 | 有效像素字节/定义好的时间 |
| 内存压力 | 控制器计数、错误和对照负载 |
| 同步等待 | 提交到完成的事件时间线 |

LVGL 性能监视器提供特定范围内的估计，不一定等同于全部系统 CPU 占用或真实可见新帧数。

不能用 CPU 空闲等待时间反向推断加速器始终空闲。

## 8. 一份结果表

| 场景 | 软件基线 | 硬件路径 | 记录 |
| --- | --- | --- | --- |
| 小区域 | 未测 | 未测/不适用 | 面积、格式 |
| 整屏动画 | 未测 | 未测/不适用 | 周期分布与错误 |
| 透明混合 | 未测 | 未测/不适用 | 画质与带宽 |
| 综合业务 | 未测 | 未测/不适用 | CPU、延迟和内存 |

同时测试冷/热缓存、启动、页面切换和稳态。不要只选最有利场景。

## 9. 小结

可信测试先定义指标，再固定负载、标记时间边界和报告分布。吞吐、响应与资源成本不能互相替代。

下一篇：[《从瓶颈出发优化，而不是盲目开加速》](23-bottleneck-optimization.md)。

## 参考资料

- [LVGL 9.2 显示事件与模式](https://docs.lvgl.io/9.2/porting/display.html)
- [LVGL 9.2.0 刷新实现](https://github.com/lvgl/lvgl/blob/v9.2.0/src/core/lv_refr.c)
- [LVGL 9.2.0 监视器配置](https://github.com/lvgl/lvgl/blob/v9.2.0/lv_conf_template.h)
