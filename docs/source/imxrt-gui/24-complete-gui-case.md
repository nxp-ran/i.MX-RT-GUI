# 第 24 篇：完整案例——做一个可交付的 i.MX RT GUI

> 系列：[i.MX RT 图形系统实战](README.md)
>
> 上一篇：[从瓶颈出发优化，而不是盲目开加速](23-bottleneck-optimization.md)
>
> 本篇目标：以温度控制面板把系统选择、LVGL 界面、输入、资源和验收连接起来。软件示例按 LVGL 9.2.0；板级显示、触摸、字体及传感器必须实际适配。
>
> 交付边界：正文和界面代码完整；不是声称已有可直接下载到任意板卡的固件。主机软件验证不能替代 GPU、面板时序、中文字形和性能的板级验收，所有未测成绩保持“未测”。

## 1. 案例的功能范围

界面显示温度数值、进度条、状态和切换按钮，支持中英文文字。

| 功能 | 本例范围 |
| --- | --- |
| 数值 | 0..100.0 C，使用整数十分之一单位 |
| 动画 | 数值条平滑变化 |
| 输入 | 按钮点击，来自触摸或其他输入设备 |
| 多语言 | 文字切换和提供的字体 |
| 业务 | 示例本地状态；实际控制需要命令与确认 |
| 显示 | 复用已验证端口，不重复造面板驱动 |

示例按钮不是实际加热器或控制输出。真实产品必须把请求、设备确认、错误与显示状态分开。

## 2. 两条平台路径

| 路径 | 适用方向 | 必需条件 |
| --- | --- | --- |
| 320 × 240 GRAM 屏 | 局部数值和状态 | 已验证传输、足够工作 RAM |
| 800 × 480 RGB/DSI | 更丰富页面与动画 | 完整帧存储、显示时序、带宽 |

下面界面代码按 320 × 240 定位。采用更大屏幕时应调整布局和预算，不仅修改分辨率宏。

芯片、板卡、SDK、显示驱动、LVGL 和字体版本必须固定，不能只写“i.MX RT”。

## 3. 系统数据路径

```text
传感器/通信 -> 领域模型 -> GUI 消息
                                |
触摸 -> 输入设备 -> GUI 事件 ----+
                                |
                                v
                     LVGL 对象与动画
                                |
                                v
                软件或已验证的硬件后端
                                |
                                v
                   显示端口与安全交接
```

GUI 任务拥有对象。采样和通信不在任意上下文直接改控件。

## 4. 可复用的界面代码

先接入[第 17 篇的端口](17-lvgl-minimal-port.md)，再调用下面的创建函数。

需要启用 label、bar、button、动画，并提供涵盖所用中文的授权字体。示例中的 Unicode 转义让 C 文件可用 ASCII 保存，不改变运行时 UTF-8 文本要求。

```c
#include "lvgl.h"
#include <stdbool.h>
#include <stdint.h>

_Noreturn void port_fatal(const char *reason);

static lv_obj_t *case_panel;
static lv_obj_t *case_value;
static lv_obj_t *case_bar;
static lv_obj_t *case_status;
static lv_obj_t *case_button;
static lv_obj_t *case_button_text;
static bool case_english = true;
static bool case_running;

static void case_refresh_state(void)
{
    const char *status = case_running
        ? (case_english ? "Running" : "\u8fd0\u884c")
        : (case_english ? "Stopped" : "\u505c\u6b62");
    lv_label_set_text(case_status, status);
    lv_label_set_text(case_button_text,
                      case_english ? "Toggle" : "\u5207\u6362");
}

static void case_toggle(lv_event_t *event)
{
    LV_UNUSED(event);
    case_running = !case_running;
    case_refresh_state();
}

void case_ui_set_language(bool english)
{
    if(case_panel == NULL) port_fatal("UI is not initialized");
    case_english = english;
    case_refresh_state();
}

void case_ui_set_temperature(int32_t tenths)
{
    if(case_panel == NULL || tenths < 0 || tenths > 1000)
        port_fatal("Invalid UI temperature");
    lv_label_set_text_fmt(case_value, "%ld.%ld C",
                          (long)(tenths / 10), (long)(tenths % 10));
    lv_bar_set_value(case_bar, tenths, LV_ANIM_ON);
}

void case_ui_create(const lv_font_t *font)
{
    if(font == NULL || case_panel != NULL)
        port_fatal("Invalid UI initialization");
    case_panel = lv_obj_create(lv_screen_active());
    if(case_panel == NULL) port_fatal("Panel allocation failed");
    lv_obj_set_size(case_panel, 320, 240);
    lv_obj_center(case_panel);
    lv_obj_set_style_pad_all(case_panel, 0, 0);
    lv_obj_set_style_border_width(case_panel, 0, 0);
    lv_obj_set_style_text_font(case_panel, font, 0);

    case_value = lv_label_create(case_panel);
    case_bar = lv_bar_create(case_panel);
    case_status = lv_label_create(case_panel);
    case_button = lv_button_create(case_panel);
    if(!case_value || !case_bar || !case_status || !case_button)
        port_fatal("Widget allocation failed");
    case_button_text = lv_label_create(case_button);
    if(!case_button_text) port_fatal("Button label allocation failed");

    lv_obj_set_pos(case_value, 20, 20);
    lv_obj_set_pos(case_bar, 20, 62);
    lv_obj_set_size(case_bar, 280, 20);
    lv_bar_set_range(case_bar, 0, 1000);
    lv_obj_set_pos(case_status, 20, 100);
    lv_obj_set_size(case_button, 120, 44);
    lv_obj_align(case_button, LV_ALIGN_BOTTOM_MID, 0, -16);
    lv_obj_center(case_button_text);
    if(lv_obj_add_event_cb(case_button, case_toggle,
                          LV_EVENT_CLICKED, NULL) == NULL)
        port_fatal("Event registration failed");

    case_running = false;
    case_ui_set_language(true);
    case_ui_set_temperature(250);
}

void case_ui_destroy(void)
{
    if(case_panel == NULL) port_fatal("UI is not initialized");
    lv_obj_delete(case_panel);
    case_panel = case_value = case_bar = case_status = NULL;
    case_button = case_button_text = NULL;
}
```

所有调用都在 GUI 拥有者上下文中执行。删除前停止外部更新、timer 或消息中的对象引用。

状态切换只是本例本地演示逻辑；实际产品应发送业务命令，在确认成功后更新运行状态，失败显式显示。

## 5. 接入输入、业务和中文

输入端按[第 20 篇](20-touch-rtos.md)报告按下、松开与校准后的坐标。

业务任务发送包含数值、时间戳和有效状态的消息。GUI 消费后再调用温度更新函数；无效传感器不能默认显示正常温度。

中文需要[第 21 篇](21-images-fonts.md)的字体覆盖与编码验证。主机检查字符串切换，不证明所有中文字形已经在面板上正确显示。

动画处理依赖真实时间基准和持续调用 handler。

## 6. 资源预算

320 × 240 GRAM 基线的两块 24 行 RGB565 工作缓冲，共 30 KiB。

若换为 800 × 480、RGB565 双完整帧，仅显示帧就需要 1,500 KiB，另有控件、字体、图层和解码。

按钮状态变化与数值更新应复用已有对象。不要每次消息都重新创建整页。

内存峰值在页面切换和资源加载时验证，不只看稳态。

## 7. 引入加速的顺序

先完整验证软件基线，再根据任务类型和总成本选择 PXP/GPU。

| 步骤 | 需要证据 |
| --- | --- |
| 软件基线 | 显示、输入、时间与错误路径 |
| 单独硬件任务 | 结果、格式、缓存与完成 |
| LVGL 后端 | 接受/回退任务与实际执行 |
| 同场景对照 | 画质、延迟、CPU 与帧周期 |
| 综合运行 | 业务、资源和异常恢复 |

这个小界面可能没有足够大的绘制负载摊薄硬件固定成本。不要为了用 GPU 故意增加无用动画。

## 8. 验收矩阵

| 类别 | 检查 |
| --- | --- |
| 视觉 | 数值、条、颜色、中文、长文本 |
| 输入 | 点击、长按、拖动、释放、边缘 |
| 数据 | 边界值、过期、断连、异常 |
| 生命周期 | 创建、更新、销毁、重建 |
| 显示 | 无失效缓冲、错误/超时正确收尾 |
| 性能 | 预定场景周期、CPU、峰值内存、输入延迟 |
| 恢复 | 显示与传感器故障后状态一致 |

实际需求阈值由产品确定，测量按[第 22 篇](22-performance-testing.md)。板级结果在获得证据之前均为未测。

## 9. 什么才是“可交付”？

至少应提供：

- 完整型号、接线、版本、配置与构建方法。
- 资源来源和许可。
- 可复现的操作场景与测量边界。
- 错误策略和已知限制。
- 正确性、内存、延迟与长期运行记录。

本篇给出软件集成起点和验收路径，不用主机测试代替嵌入式实时与电气验证。

## 10. 全系列回顾

屏幕接口决定像素怎样传输，显示控制器决定怎样扫描，存储决定数据能否及时供给，PXP/GPU 改变任务执行，LVGL 组织界面与刷新。

贯穿所有层的仍然是：

**版本与能力核对、格式与布局、拥有权与一致性、真实测量与错误处理。**

24 篇正文到此完成。后续可根据具体开发板补充实测附录，不应把未测值填成理论成绩。

## 参考资料

- [LVGL 9.2.0 标签 API](https://github.com/lvgl/lvgl/blob/v9.2.0/src/widgets/label/lv_label.h)
- [LVGL 9.2.0 数值条 API](https://github.com/lvgl/lvgl/blob/v9.2.0/src/widgets/bar/lv_bar.h)
- [LVGL 9.2 输入接口](https://docs.lvgl.io/9.2/porting/indev.html)
- [LVGL 9.2 字体](https://docs.lvgl.io/9.2/overview/font.html)
