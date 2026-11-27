# 第 7 篇：MIPI DSI 屏——高速串行显示链路

> 系列：[从点亮屏幕到高性能 GUI：i.MX RT 图形系统实战](README.md)
>
> 上一篇：[RGB 屏——理解像素时钟与连续扫描](06-rgb-display.md)
>
> 下一篇：[一套可复用的屏幕点亮与排障流程](08-display-bring-up.md)
>
> 本篇目标：理解 DSI Host、D-PHY、像素源和面板的分工，完成模式、格式、链路预算与初始化的分层检查。
>
> 适用范围：使用 i.MX RT1170 的公开 SDK 路径作为具体参考，不推广到所有 i.MX RT。预算中的分辨率、时序、链路速率和等待时间均为假设，不是面板或 PHY 配置推荐值。

## 1. 接口变成串行，完整帧问题并没有消失

在[第 6 篇](06-rgb-display.md)中，显示控制器连续读取帧缓冲区，生成 RGB 像素时序。

在典型 DSI 视频模式中，像素源仍然需要工作，只是输出增加了打包和高速串行发送过程：

```text
CPU / PXP / GPU
       |
       v
帧缓冲区
       |
       v
显示控制器：像素流与时序
       |
       v
DSI Host：包与传输调度
       |
       v
D-PHY：高速串行电气链路
       |
       v
面板控制器与显示
```

DSI 提高的是接口组织方式和传输能力，不自动替代帧存储、绘制或数据一致性。

同样，“有 DSI 接口”不等于“所有 DSI 模组都能使用同一段初始化代码”。

## 2. 四个角色，分别解决什么问题？

| 角色 | 主要职责 | 典型检查 |
| --- | --- | --- |
| 显示控制器 | 从内存生成像素与视频时序 | 帧格式、时钟、同步和地址 |
| DSI Host | 组织命令、数据包和视频传输 | 模式、包格式、通道与超时 |
| D-PHY | 实现对应物理链路 | Lane、参考时钟、速率与时序 |
| 面板控制器 | 初始化并接收显示数据 | 模组命令、格式、模式与扫描 |

此外，芯片上的视频路由、时钟门控、电源域和复位，也可能是整条链路的必要条件。

面板标注 DSI，只说明一个接口方向。还需要确认数据 Lane 数、像素格式、工作模式、控制命令和电气要求。

## 3. 命令模式与视频模式，影响软件结构

### 3.1 命令模式

在典型的带图像存储命令模式面板上，主控可以发送设置窗口、写入图像等事务，面板根据保存内容扫描。

但不能仅凭“命令模式”就推断所有面板的 GRAM 容量、区域写入能力或同步方式。

需要核对：

- 面板是否支持需要的命令和更新方式。
- Host 能否通过所选路径传输对应像素。
- TE 或其他同步如何使用。
- SDK 和 GUI 端口是否实现了这一路径。

### 3.2 视频模式

视频模式按时序持续传输图像，常见子模式包括：

- Non-burst with sync pulses。
- Non-burst with sync events。
- Burst。

它们会改变包结构、有效传输时间和消隐处理。面板支持哪一种，应依据资料确认。

### 3.3 发送初始化命令不等于使用命令模式显示

视频模式面板也需要命令初始化。

因此，驱动能够发送 DCS 或 Generic 命令，不代表它已经能运行命令模式图像更新。

反过来，视频路径正常，也不证明所有命令读取和返回方向都已正确配置。

## 4. Lane、LP 与 HS，不能简单套用 SPI 经验

DSI 数据通过协议规定的通道和物理 Lane 传输。数据 Lane 数与虚拟通道不是同一个概念。

| 概念 | 含义 |
| --- | --- |
| 数据 Lane | 承担串行数据的物理路径 |
| 时钟 Lane | 本篇 D-PHY 模型中的高速时钟路径 |
| Virtual Channel | 数据包中的逻辑通道标识 |
| LP | 低功耗信令状态/传输机制 |
| HS | 高速传输机制 |

某些初始化命令使用 LP，视频像素使用 HS；具体选择由 Host、面板和驱动决定。

HS 与 LP 切换、总线返回方向、等待周期和超时都需要配置。不能把“LP 能发命令”当作“HS 视频链路已经正常”。

探测高速差分信号应使用适当的仪器与方法。普通低速逻辑分析仪不能替代 D-PHY 链路验证，也不应根据探不到可解码波形就判定没有传输。

## 5. 要维护一张明确的时钟表

| 时钟或速率 | 用途 | 容易混淆的地方 |
| --- | --- | --- |
| 显示像素时钟 | 生成视频时序 | 不能只按有效像素计算 |
| PHY 参考时钟 | 生成目标链路时钟 | 不等于输出位率 |
| 每 Lane 高速位率 | 估算串行数据传输 | 不等于整个接口总位率 |
| 字节时钟 | Host 的部分计数与配置 | 需确认与位率的关系 |
| Escape 时钟 | LP 相关控制 | 不等于像素或 HS 时钟 |

在常见 D-PHY HS DDR 描述下，位率、时钟 Lane 频率和字节时钟可能存在二倍或八倍关系，但 API 字段名称与实际计数单位必须以具体驱动为准。

尤其不能把一个称为 `bitClk` 的目标值，与示波器上的时钟频率直接当作相同数字。

初始化返回的实际生成速率，也可能与请求值不同。后续时序应基于实际值，而不是继续使用请求值。

## 6. 内存格式、DPI 格式、DSI 包格式分开检查

下面三项不是同一个配置：

```text
帧缓冲内存格式
       |
       v
显示控制器到 Host 的像素表示
       |
       v
DSI 链路上的像素包格式
```

本次核对的 RT1170 LCDIFv2 RGB565 示例，使用 RGB565 源帧；其板级 DSI 支持代码则配置了 24 位 DPI 和 RGB888 像素包。

这意味着：

- 内存扫描容量按实际源格式计算。
- 链路负载按实际输出包格式计算。
- 不能用 RGB565 的 16 位容量替代 RGB888 的 24 位链路负载。

DSI Host 中 `pixelPayloadSize` 一类字段还可能以像素数计，而不是字节数。必须看字段定义。

“RGB666”也可能是紧凑或松散排列，不能只凭颜色位数推断传输字节数。

## 7. 不只算每秒，还要算每行能否发完

假设：

- 800 × 480，60 Hz。
- 水平总数 928，垂直总数 525。
- DSI 输出为 RGB888。
- 使用 2 条数据 Lane，每条假设 500 Mbit/s。
- 每行一个像素长包。
- 长包头与校验合计按 6 B 计算。
- 每行额外预留 2 us，代表本模型未逐项展开的其他占用。

有效像素平均负载：

```text
800 × 480 × 60 × 24 = 552.96 Mbit/s
每 Lane 平均有效负载 = 276.48 Mbit/s
```

但这不是充分条件。

一行时间约 31.746 us；每行像素为 2,400 B，加 6 B 后，在假设的两 Lane 总位率下需要 19.248 us。

还要把其他包、状态切换和等待放入可用窗口。不能把这些假设当作完整的 DSI 协议时序验证。

下面脚本展示两个预算视角，不配置任何硬件：

```python
width, height, refresh = 800, 480, 60
h_total, v_total = 928, 525
bits_per_pixel = 24
lanes = 2
lane_rate = 500_000_000
packet_overhead_bytes = 6
reserved_us = 2

pixel_clock = h_total * v_total * refresh
line_us = h_total / pixel_clock * 1_000_000
packet_bytes = width * bits_per_pixel // 8 + packet_overhead_bytes
wire_us = packet_bytes * 8 / (lanes * lane_rate) * 1_000_000
active_rate = width * height * refresh * bits_per_pixel
timing_rate_per_lane = pixel_clock * bits_per_pixel / lanes

if wire_us + reserved_us > line_us:
    raise ValueError("The assumed packet and reserved interval exceed one line.")

print(f"Active payload per lane: {active_rate / lanes / 1_000_000:.2f} Mbit/s")
print(f"Timing-based rate per lane: {timing_rate_per_lane / 1_000_000:.3f} Mbit/s")
print(f"Line time: {line_us:.3f} us")
print(f"Packet bytes: {packet_bytes}")
print(f"Packet wire time: {wire_us:.3f} us")
print(f"Packet plus reserve: {wire_us + reserved_us:.3f} us")
```

输出：

```text
Active payload per lane: 276.48 Mbit/s
Timing-based rate per lane: 350.784 Mbit/s
Line time: 31.746 us
Packet bytes: 2406
Packet wire time: 19.248 us
Packet plus reserve: 21.248 us
```

500 Mbit/s、6 B 和 2 us 只是此模型输入。实际还需要检查 Host/PHY 支持范围、视频模式、包切分、消隐、额外协议占用及面板要求。

RT1170 板级示例还演示了按完整像素时序估算链路速率并增加余量的方法。这是具体示例的策略，不是给所有屏幕统一乘一个系数的依据。

## 8. 初始化应分层验证

一套适合分析的逻辑顺序是：

```text
确认硬件连接与面板要求
       |
       v
电源域、隔离、复位与视频路由
       |
       v
像素、参考与 Escape 时钟
       |
       v
Host 和 D-PHY 配置
       |
       v
面板初始化与状态检查
       |
       v
有效帧数据、视频输入与扫描
       |
       v
显示与背光
```

实际模块复位释放和面板命令的前后关系，以目标 SDK 与模组规定为准。这个图不是可以机械照搬的寄存器操作表。

RT1170 的板级示例还处理了 LCDIFv2 到 DSI 的视频路由。这说明仅初始化 DSI Host，不一定已经连接了正确的像素源。

每个阶段都应检查结果；失败时记录并停止继续推进，不能在初始化失败后仍然显示“启动成功”。

## 9. 面板初始化与视频链路要分别确认

建议从 SDK 已支持的同型号模组开始，记录：

- 面板驱动和资源回调。
- 电源、复位与背光控制。
- DCS / Generic 事务类型和参数。
- Virtual Channel。
- 退出睡眠、显示启用等状态转换的等待。
- 面板的像素格式与视频模式。

有些模组还依赖额外 I²C 控制。不要把所有控制步骤都假定为 DSI 命令。

面板 ID 读取也不是必需且总能成功的验证方法。读取需要返回路径、对应命令、板级连接和驱动支持；不可读不能单独证明面板坏了。

## 10. 最小显示与对照实验

| 实验 | 主要验证 | 不足以证明 |
| --- | --- | --- |
| 面板初始化成功 | 命令和控制路径符合预期 | HS 视频像素已正确输出 |
| Host 状态与 PHY 就绪 | 模块达到相关状态 | 图像源、包格式和面板时序全正确 |
| 固定纯色与色条 | 基本视频数据路径 | 动态更新及缓存管理正确 |
| 四角与行图案 | 方向、尺寸、映射 | 负载下无欠载 |
| 双帧交替 | 内容提交与换帧 | 任意工作负载下无延迟或撕裂 |
| 加入资源与 CPU 负载 | 带宽和同步稳定性 | 无需进一步长期验证 |

如果 Host 或控制器有内部测试图案，可按目标硬件能力使用，但不能假定所有型号都提供。

内部图案正常而内存图像异常，可以帮助缩小问题范围；它绕过了哪些环节，也必须写清楚。

## 11. 典型问题怎样定位？

| 现象 | 优先检查 |
| --- | --- |
| 命令失败或超时 | 供电、复位、LP 路径、事务类型、通道和超时单位 |
| 初始化成功但黑屏 | 视频路由、像素源、扫描、HS 链路和面板显示状态 |
| 颜色或每行规律异常 | DPI 格式、包格式、有效像素数与布局 |
| 某些速率正常，换速率失败 | 实际 PLL 结果、PHY 时序、面板允许范围 |
| 静态正常，动态异常 | Cache、换帧、内存访问及 FIFO 状态 |
| ECC / CRC 或协议错误出现 | 包或链路问题，结合错误类型和时序分析 |
| 中断存在但看不到新内容 | 中断语义、当前帧地址、像素内容和面板扫描 |

不要把所有 DSI 问题都归为“高速信号不好”，也不要把所有黑屏都归为“初始化数组错误”。

## 12. 小结

DSI 开发需要同时对齐三个层次：

1. 像素源及其内存与时序。
2. Host 的模式、包与调度。
3. PHY 和面板的实际链路要求。

命令初始化、HS 视频工作和完整 GUI 流畅，是三个不同验证目标。

下一篇：[《一套可复用的屏幕点亮与排障流程》](08-display-bring-up.md)。我们将把 SPI、并口、RGB 与 DSI 的共同检查方法整理成工程化流程。

## 参考资料

- [NXP MIPI DSI 接口](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/mipi_dsi/fsl_mipi_dsi.h)
- [RT1170 LCDIFv2/DSI 板级支持](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/_boards/evkbmimxrt1170/driver_examples/lcdifv2/lcdifv2_support.c)
- [RT1170 对应示例的面板与接线说明](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/_boards/evkbmimxrt1170/driver_examples/lcdifv2/lcdifv2_examples_readme.md)
- [NXP RT1170 产品资料入口](https://www.nxp.com/products/i.MX-RT1170)

接口相同名字不代表 IP 相同。不同芯片上的 `fsl_mipi_dsi` 也可能属于不同驱动变体，必须核对实际目标。
