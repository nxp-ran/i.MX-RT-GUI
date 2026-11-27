# Article 17: A Minimal LVGL Port with Software Rendering

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Choosing CPU, PXP, or GPU](16-render-backend-selection.md)
>
> Next: [LVGL Refresh and Rendering](18-lvgl-refresh.md)
>
> Goal: Establish a correct software path with LVGL **9.2.0**. Actual LVGL APIs are used, but target-specific `port_*` functions are required; this is not downloadable board firmware.

## 1. Fix Versions and a Display Baseline

First validate color bars and regions without LVGL.

Record device, board, panel, memory, SDK, compiler, LVGL, formats, addresses, clocks, and completion/error contracts.

The example uses 320 × 240 RGB565 PARTIAL software rendering without LVGL worker threads. It suits a regional-transfer GRAM baseline. Continuous scanout also needs a complete frame and safe handoff.

Do not mix LVGL 8 registration with this 9.2.0 example.

## 2. Four Integration Interfaces

| Interface | Role | Error |
| --- | --- | --- |
| Timebase | Real elapsed milliseconds | Counting loops |
| Processing | `lv_timer_handler()` | Concurrent calls |
| Flush | Deliver area/pixels | Wrong format, stride, lifetime |
| Memory/configuration | Objects and drawing | Capacity/alignment/version mismatch |

Time must be independent of rendering. FreeRTOS ticks are not necessarily milliseconds; verify frequency/types or convert reliably.

Do not double-count using both a callback and increments.

## 3. Minimal Port

This C11 example requires software rendering, RGB565, and a stride compatible with its buffer sizing.

`port_write_rgb565()` handles mapping, maintenance, ordering, and synchronous writes using actual stride. Success means every source consumer has released the buffer; failure is explicit.

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

Each buffer is 15,360 B; together they use 30 KiB. The example's 64 B alignment does not replace actual hardware requirements.

Initialize once, then process in one owner context.

`port_fatal()` must log and stop or enter recovery, not return into successful completion. The baseline deliberately uses a stopping failure path.

## 4. Use Actual Stride

Regions can be narrower than the display and aligned differently.

LVGL 9.2.0's active draw-buffer descriptor provides `header.stride`; do not assume width times two.

DIRECT/FULL can reference complete frames with different region/pointer semantics. This PARTIAL port is not universal.

## 5. Moving to Asynchronous Transfers

Do not call completion at startup:

```text
Save area/source/request
   -> Start
   -> Actual completion/error
   -> Confirm source release and cleanup
   -> Notify LVGL
```

Startup failure, timeout, and abort need explicit error paths.

Two buffers help only with real background transfer. Blocking transfer does not automatically become faster.

## 6. Validate Before Benchmarking

| Scene | Check |
| --- | --- |
| Label | Objects/layout/time |
| Regional color | Area/stride/ordering |
| Image/bars | Format/resources |
| Animation | Timebase/refresh |
| Repetition | Lifetime/peak memory |

Record areas, bytes, completions, and failures. Multiple flush chunks are not multiple full frames.

## 7. RTOS Integration

Prefer one GUI owner with messages from business tasks.

Follow version-specific OSAL locking; do not introduce incompatible double locking around the handler.

`port_wait_or_timeout()` should wait/receive notification rather than spin, retaining the example's maximum 20 ms checking interval.

## 8. Summary

Validate time, processing, display, and memory with explicit failures.

Next: [LVGL Refresh and Rendering](18-lvgl-refresh.md).

## References

- [LVGL 9.2 display](https://docs.lvgl.io/9.2/porting/display.html)
- [LVGL 9.2 tick](https://docs.lvgl.io/9.2/porting/tick.html)
- [LVGL 9.2 OS/interrupts](https://docs.lvgl.io/9.2/porting/os.html)
- [LVGL 9.2.0 implementation](https://github.com/lvgl/lvgl/blob/v9.2.0/src/display/lv_display.c)
