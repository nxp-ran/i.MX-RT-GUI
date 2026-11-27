# Article 21: Engineering Images, Fonts, and Chinese Interfaces

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Touch, RTOS, and Thread Safety](20-touch-rtos.md)
>
> Next: [Trustworthy GUI Performance Testing](22-performance-testing.md)
>
> Goal: Manage LVGL 9.2.0 formats, decoding, fonts, and lifetimes. Capacities are budgets; validate actual converter outputs.

## 1. Resource Stages

```text
Original image/licensed font -> Offline conversion/subsetting
   -> Flash/file -> Read/decode/cache -> Backend -> Pixels
```

Each stage has its own format and capacity. Small PNG files do not imply equally small runtime RAM.

Check asset/font distribution rights; no third-party font file is supplied here.

## 2. Choose Formats by Use

| Type | Use | Cost |
| --- | --- | --- |
| RGB565 | Opaque low-capacity images | Reduced depth/no Alpha |
| ARGB8888 | Transparency/composition | Capacity and traffic |
| A4/A8 mask | Single-color glyphs/icons | Drawing state supplies color |
| Compressed | Storage/update savings | Decode/cache/backend compatibility |

Backend-compatible decoded formats can reduce conversion. Storage optimization must not force repeated decoding each frame.

Global opacity, pixel Alpha, and premultiplication are distinct.

## 3. Use the 9.2.0 Descriptor

`lv_image_dsc_t` includes a header, size, and data pointer. The header contains magic, format, dimensions, and stride.

Use the pinned header/converter instead of obsolete fields/functions.

This complete 2 × 2 RGB565 constant contains red, green, blue, and white, with a 4 B stride:

```c
#include "lvgl.h"

static _Alignas(4) const uint8_t icon_pixels[] = {
    0x00, 0xF8, 0xE0, 0x07,
    0x1F, 0x00, 0xFF, 0xFF
};

const lv_image_dsc_t ui_icon = {
    .header = {
        .magic = LV_IMAGE_HEADER_MAGIC,
        .cf = LV_COLOR_FORMAT_RGB565,
        .w = 2,
        .h = 2,
        .stride = 4
    },
    .data_size = sizeof(icon_pixels),
    .data = icon_pixels
};
```

This is little-endian RGB565 memory, not a wire-order setting or universal accelerator-compatible size.

Descriptor/data lifetimes permit `lv_image_set_src()`. Do not return pointers to temporary stack descriptors.

## 4. Storage and Decoding

| Placement | Benefit | Verify |
| --- | --- | --- |
| Constant C | Simple linking/deployment | Placement, access, firmware size |
| Mapped Flash | Larger independent assets | XIP contention/reachability |
| Files | Replaceable resources | Paths, driver, decode, errors |

Return actual read lengths/errors. Do not zero-pad truncation into success.

File paths are not GPU pixel addresses. Decode or map appropriately.

## 5. Cache Policy

Bound capacity and define eviction, invalidation, and active-resource ownership.

Updated files must not retain stale entries; active tasks prevent premature release.

| Scene | Approach |
| --- | --- |
| Small permanent icons | Fixed/bounded cache |
| Large page images | Page lifetime/peak budget |
| Updated files | Version/invalidation |
| Animation | Preconversion/decode or feasible chunks |

Larger caches can crowd out frames and tasks.

## 6. Three Chinese-Font Conditions

Require:

1. Correct text encoding, normally UTF-8.
2. Glyphs and metrics.
3. Correct widget font/layout.

Latin fonts do not automatically include Chinese; a CJK subset is not full coverage.

Collect fixed/dynamic text, units, digits, punctuation, and incoming characters. Define visible missing-glyph policy rather than silent blanks.

## 7. Font Capacity

Assume full 24 × 24 glyphs at 4 bpp:

| Count | Bitmap payload |
| --- | --- |
| 200 glyphs | 57,600 B = 56.25 KiB |
| 5,000 glyphs | 1,440,000 B = 1,406.25 KiB |

Real sizes include metrics, indexes, kerning, compression, and variable glyph shapes.

Subset offline and record converter, size, bpp, licensing, and output.

Budget each font size independently.

## 8. Text and Object Lifetimes

Copied-text APIs such as `lv_label_set_text()` differ from static-text contracts. Static storage must remain valid and updates must be signaled correctly.

Reuse labels/fonts rather than recreating them for every sensor sample.

Remove timers, callbacks, and references during page destruction before releasing resources.

## 9. Validation and Summary

Check Alpha edges, backend colors, cold/warm caches, missing/truncated files, missing glyphs, page peaks, and repeated release.

One correct image does not establish cache/lifetime correctness.

Next: [Trustworthy GUI Performance Testing](22-performance-testing.md).

## References

- [LVGL 9.2 images](https://docs.lvgl.io/9.2/overview/image.html)
- [LVGL 9.2 fonts](https://docs.lvgl.io/9.2/overview/font.html)
- [Actual 9.2.0 descriptor](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/lv_image_dsc.h)
