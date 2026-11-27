# 第 17 篇：LVGL 最小移植——让软件绘制先跑起来

> 系列：[i.MX RT 图形系统实战](README.md)
>
> 上一篇：[CPU、PXP、GPU 怎么选？](16-render-backend-selection.md)
>
> 下一篇：[理解 LVGL 的刷新与绘制机制](18-lvgl-refresh.md)
>
> 本篇目标：用 LVGL **9.2.0** 建立最小正确软件路径。示例包含实际 LVGL API，但 `port_*` 必须由目标工程实现，不是可直接下载的板卡固件。

## 1. 先固定版本与显示基线

先确认不用 LVGL 时，屏幕能够稳定显示色条和区域图案。

记录：

- 芯片、开发板、屏幕和外部存储。
- SDK、编译器与 LVGL 版本。
- 目标像素格式、缓冲地址和时钟。
- 显示端口的同步和错误契约。

本篇选择 320 × 240、RGB565、PARTIAL 模式，软件绘制且无 LVGL 工作线程。它适合带 GRAM 的按区域传输基线；连续扫描屏需另外提供完整显示帧与安全交接。

不能把 LVGL 8 的驱动注册代码混进下面的 9.2.0 示例。

## 2. 四个需要接入的接口

| 接口 | 职责 | 常见错误 |
| --- | --- | --- |
| 时间基准 | 返回实际经过的毫秒 | 把循环次数当时间 |
| 任务处理 | 调用 `lv_timer_handler()` | 多任务并发调用 |
| 显示刷新 | 区域和像素交给显示 | 忽略格式、stride 或生命周期 |
| 内存与配置 | 对象及绘制分配 | 缓冲不足、对齐或 API 版本错误 |

时间必须独立于绘制执行时间。FreeRTOS tick 数不一定是毫秒，只有相应频率与类型条件成立才可直接使用；否则需可靠的转换或独立时基。

不要同时用 callback 和周期增量维护同一个时基而重复计时。

## 3. 一份最小软件端口

以下 C11 示例要求软件绘制、RGB565 支持和满足本例缓冲大小的 stride 配置。

`port_write_rgb565()` 接收真实行跨度，负责面板映射、必要缓存维护、格式/字节序与同步发送。成功返回时，所有相关消费者必须已释放源缓冲；失败进入明确的故障处理。

```c
#include "lvgl.h"
#include <stdbool.h>
#include <stdint.h>

uint32_t port_milliseconds(void);
bool port_write_rgb565(const lv_area_t *area, const uint8_t *pixels,
                       uint32_t stride_bytes);
void port_wait_or_timeout(uint32_t milliseconds);
_Noreturn void port_fatal(const char *reason);

enum { PORT_WIDTH = 320, PORT_HEIGHT = 240, PORT_ROWS = 24 };
static _Alignas(64) uint8_t draw_a[PORT_WIDTH * PORT_ROWS * 2];
static _Alignas(64) uint8_t draw_b[PORT_WIDTH * PORT_ROWS * 2];

static void flush_pixels(lv_display_t *display, const lv_area_t *area,
                         uint8_t *pixels)
{
    const lv_draw_buf_t *active = lv_display_get_buf_active(display);
    if(active == NULL ||
       !port_write_rgb565(area, pixels, active->header.stride)) {
        port_fatal("Display transfer failed");
    }
    lv_display_flush_ready(display);
}

lv_display_t *gui_port_init(void)
{
    lv_init();
    lv_tick_set_cb(port_milliseconds);
    lv_display_t *display = lv_display_create(PORT_WIDTH, PORT_HEIGHT);
    if(display == NULL) port_fatal("Display allocation failed");

    lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
    lv_display_set_flush_cb(display, flush_pixels);
    lv_display_set_buffers(display, draw_a, draw_b, sizeof(draw_a),
                           LV_DISPLAY_RENDER_MODE_PARTIAL);

    lv_obj_t *label = lv_label_create(lv_screen_active());
    if(label == NULL) port_fatal("Label allocation failed");
    lv_label_set_text(label, "LVGL 9.2 baseline");
    lv_obj_center(label);
    return display;
}

void gui_port_run_once(void)
{
    uint32_t wait_ms = lv_timer_handler();
    port_wait_or_timeout(wait_ms > 20 ? 20 : wait_ms);
}
```

两块缓冲各 15,360 B，合计 30 KiB。这里的 64 B 对齐用于本例隔离，不代替目标硬件及配置要求。

`gui_port_init()` 只调用一次；之后在同一个拥有者上下文循环调用处理函数。

`port_fatal()` 必须记录错误并停止或进入项目恢复流程，不能返回后继续通知“刷新成功”。同步基线选择停止路径，是为了避免演示代码隐藏错误。

## 4. 为什么读取真实 stride？

刷新区域宽度不一定等于屏幕宽度，缓冲也可能带对齐。

LVGL 9.2.0 提供当前 draw buffer 描述，刷新回调可以核对真实 `header.stride`。不能总用 `区域宽度 × 2` 计算下一行。

连续扫描的 DIRECT/FULL 模式则可能指向完整帧，`pixels` 与区域坐标含义不同。不要未经分析把本例 PARTIAL 端口套过去。

## 5. 从同步到异步，哪些代码要改变？

异步端口启动后不能立即调用 `lv_display_flush_ready()`。

```text
flush_cb 保存区域、源和请求
   -> 启动传输
   -> 真正完成/错误通知
   -> 确认源释放并收尾
   -> 通知 LVGL
```

启动失败、超时和中止需要独立错误通道。把故障缓冲强行通知完成不代表画面有效。

两块缓冲只有在传输真正后台执行时才能产生绘制/传输重叠。本例阻塞发送不会因为有第二块缓冲就自动变快。

## 6. 先验证，不先 benchmark

| 场景 | 检查 |
| --- | --- |
| 标签 | 创建、布局与时间处理 |
| 小区域变色 | 区域、stride、字节序 |
| 图片与色条 | 格式与资源解释 |
| 简单动画 | 时间基准与刷新 |
| 反复更新 | 生命周期与内存峰值 |

先记录提交区域、有效字节、完成次数和错误。一次刷新可能分成多个块，不能把每个 flush 都算作一帧。

## 7. 与 RTOS 集成

最简单的方式是一个 GUI 任务拥有 LVGL，业务任务通过消息传递数据。

使用 LVGL OSAL 时，按该版本锁的规则集成，避免在 `lv_timer_handler()` 外套重复且不兼容的锁。

`port_wait_or_timeout()` 应支持任务通知或等待，并保留本例最长 20 ms 的处理检查周期；它不是忙等延时。

## 8. 小结

最小移植要验证时间、处理、显示和内存四个接口，并给错误明确出口。

下一篇：[《理解 LVGL 的刷新与绘制机制》](18-lvgl-refresh.md)。

## 参考资料

- [LVGL 9.2 显示接口](https://docs.lvgl.io/9.2/porting/display.html)
- [LVGL 9.2 Tick](https://docs.lvgl.io/9.2/porting/tick.html)
- [LVGL 9.2 OS 与中断](https://docs.lvgl.io/9.2/porting/os.html)
- [LVGL 9.2.0 显示实现](https://github.com/lvgl/lvgl/blob/v9.2.0/src/display/lv_display.c)
