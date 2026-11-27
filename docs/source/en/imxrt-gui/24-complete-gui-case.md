# Article 24: A Deliverable i.MX RT GUI

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Optimize the Bottleneck, Not the Acceleration Checkbox](23-bottleneck-optimization.md)
>
> Goal: Connect platform choice, LVGL, input, resources, and acceptance in a temperature panel. Code targets LVGL 9.2.0; display, touch, fonts, and sensors require actual platform integration.
>
> Delivery boundary: Complete article/interface code, not firmware for any arbitrary board. Host validation does not certify GPU, panel timing, Chinese glyphs, or board performance. Unmeasured results remain unmeasured.

## 1. Functional Scope

Display temperature, an animated bar, status, and a toggle with Chinese/English text.

| Feature | Scope |
| --- | --- |
| Value | 0..100.0 C in integer tenths |
| Animation | Smooth bar updates |
| Input | Button click from touch/other devices |
| Languages | Text selection and supplied font |
| Business | Local demo state; production needs requests/acknowledgments |
| Output | Reuse validated port |

The button does not control a heater. Production separates requests, acknowledgments, faults, and displayed state.

## 2. Two Platform Paths

| Path | Purpose | Requirements |
| --- | --- | --- |
| 320 × 240 GRAM | Sparse values/status | Validated transfers and workspace |
| 800 × 480 RGB/DSI | Richer pages/animation | Frames, timing, bandwidth |

The code uses 320 × 240 positioning. Larger displays need layout and budget changes, not only a macro.

Fix exact device, board, SDK, drivers, LVGL, and fonts.

## 3. System Path

```text
Sensors/communication -> Domain model -> GUI messages
                                              |
Touch -> Input device -> GUI events ----------+
                                              |
                                              v
                                    LVGL objects/animation
                                              |
                                              v
                                    Software/validated hardware
                                              |
                                              v
                                    Display port and safe handoff
```

One GUI owner manages objects.

## 4. Reusable Interface Code

Use [Article 17's port](17-lvgl-minimal-port.md) before creation.

Enable labels, bars, buttons, animations, and supply a licensed font covering the Chinese strings. Unicode escapes retain ASCII C source while runtime text remains UTF-8.

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

All calls use the GUI-owner context. Stop external updates, timers, and object references before deletion.

The state toggle is local demo logic. Production sends commands and updates confirmed state, reporting failure explicitly.

## 5. Input, Business Data, Chinese

Use [Article 20](20-touch-rtos.md) for pressed/released state and calibrated input.

Business messages carry values, timestamps, and validity. Invalid sensors must not become success-shaped temperature defaults.

Use [Article 21](21-images-fonts.md) for coverage/encoding. Host string checks do not validate every panel glyph.

Animations need a real timebase and handler processing.

## 6. Resource Budget

Two 24-line RGB565 buffers for 320 × 240 use 30 KiB.

Two 800 × 480 RGB565 frames alone use 1,500 KiB, excluding widgets/fonts/layers/decoding.

Reuse objects rather than recreating pages per message. Measure loading/transition peaks.

## 7. Adding Acceleration

Validate software first, then choose hardware by tasks/cost.

| Step | Evidence |
| --- | --- |
| Software | Output/input/time/errors |
| Hardware operation | Results/formats/cache/completion |
| LVGL backend | Accepted/fallback tasks and actual execution |
| Equivalent comparison | Quality/latency/CPU/period |
| Combined operation | Business/resources/recovery |

This small UI may not amortize hardware setup. Do not add unnecessary animation merely to use a GPU.

## 8. Acceptance Matrix

| Category | Checks |
| --- | --- |
| Visual | Value/bar/colors/Chinese/long text |
| Input | Click/hold/drag/release/edges |
| Data | Limits/stale/disconnected/invalid |
| Lifetime | Create/update/delete/recreate |
| Display | Ownership/errors/timeouts |
| Performance | Defined periods/CPU/peaks/latency |
| Recovery | Consistent sensor/display recovery |

Thresholds follow the product and [Article 22](22-performance-testing.md). Board results require measurements.

## 9. Deliverable Means More Than a Demo

Provide exact parts, wiring, versions, build/configuration, resource rights, reproducible scenes, measurement boundaries, errors, limitations, and long-running evidence.

This is a software integration starting point and acceptance plan, not a substitute for electrical/real-time validation.

## 10. Series Conclusion

Interfaces transport pixels, controllers scan them, memory supplies them, PXP/GPU execute work, and LVGL organizes the interface.

Across every layer:

**Verify versions/capabilities, formats/layout, ownership/coherency, measurements/errors.**

All 24 articles are now complete. Add board measurements as appendices without replacing unmeasured results with theoretical scores.

## References

- [LVGL 9.2.0 label API](https://github.com/lvgl/lvgl/blob/v9.2.0/src/widgets/label/lv_label.h)
- [LVGL 9.2.0 bar API](https://github.com/lvgl/lvgl/blob/v9.2.0/src/widgets/bar/lv_bar.h)
- [LVGL 9.2 input](https://docs.lvgl.io/9.2/porting/indev.html)
- [LVGL 9.2 fonts](https://docs.lvgl.io/9.2/overview/font.html)
