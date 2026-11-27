# Article 12: Cache, MPU, and DMA Coherency

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Single/Double Buffering and Tearing](11-buffering-and-tearing.md)
>
> Next: [PXP Capabilities and Limits](13-pxp-capabilities.md)
>
> Goal: Design direction-specific maintenance without stale pixels, dirty writeback, or boundary damage. The model uses non-coherent Cortex-M7 peripheral access; verify other cores and cache levels separately.

## 1. Why Devices Can See Old Pixels

Write-back cache can retain CPU changes without updating RAM. Non-coherent DMA, display, or accelerators then read stale RAM.

Conversely, after hardware updates RAM, the CPU can hit an old cache copy.

```text
CPU <-> D-Cache <-> RAM <-> DMA / display / accelerator
```

`volatile` neither writes back dirty lines nor waits for hardware. Mutexes protect concurrency, not automatic device visibility.

## 2. Three Maintenance Operations

| Operation | Purpose | Risk |
| --- | --- | --- |
| Clean | Write dirty lines to RAM | Does not wait for device completion |
| Invalidate | Discard lines so future reads reload | Can discard dirty CPU data |
| Clean + Invalidate | Write back then discard | Wrong timing can overwrite hardware results |

These are not interchangeable cache-refresh commands.

Follow the actual CMSIS/SDK address, size, barrier, and alignment contract. Common M7 lines are 32 B; other architectures require verification.

## 3. CPU Writes, Device Reads

Typical handoff:

```text
CPU owns and writes
   -> Clean complete affected lines
   -> Required SDK barriers
   -> Submit device reads
   -> No CPU modifications
   -> Confirm consumer release
   -> Write again
```

An unchanged read-only resource may not need repeated cleaning if modification tracking proves it.

Cleaning a frame and immediately writing it again still risks scanout conflicts. Maintenance is not a buffer lock.

## 4. Device Writes, CPU Reads

A conservative cache-backed destination strategy:

1. Transfer ownership of complete affected lines.
2. Resolve destination dirty lines before hardware, typically with appropriate Clean + Invalidate.
3. Do not access the destination or shared boundary lines during execution.
4. Confirm actual write completion.
5. Invalidate before CPU reads to discard remaining or reloaded stale copies.

Full overwrites of exclusive lines can permit different preconditions under SDK rules. Do not generalize that to partial writes or shared lines.

**Cleaning a destination after hardware completion can write stale dirty data over the new result.**

## 5. Boundaries Matter

Maintenance uses lines, not pixels.

A 60 B range starting 3 B into a line can span two 32 B lines.

Unrelated variables sharing those lines can be lost by invalidation or overwritten by writeback.

Prefer device buffers isolated at both allocation boundaries.

Rectangles also have stride. `width × height × bytes` is not necessarily a contiguous range in padded images.

Maintain rows while accounting for repeated boundaries, or maintain the complete owned envelope including padding. Costs differ.

## 6. Calculate an Envelope Offline

This is arithmetic, not actual maintenance or proof of ownership:

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

Output:

```text
Requested: 0x20200003, 60 B
Envelope: 0x20200000..0x20200040 (exclusive end)
Maintenance length: 64 B
```

C also needs address-overflow, API size-limit, and ownership checks.

## 7. MPU Attributes Do Not Create Coherency

MPU attributes control CPU behavior, not peripheral physical reachability.

Check:

- Region size, base, priority, overlaps.
- Normal/Device memory types.
- Cacheability, buffering, sharing, permissions.
- Actual access by cores and devices.

Shareable does not automatically make arbitrary DMA coherent.

Stop relevant access and perform required maintenance/barriers before changing attributes. Avoid concurrent aliases with incompatible attributes.

## 8. Cached or Uncached?

| Strategy | Benefit | Cost |
| --- | --- | --- |
| Uncached pixel buffers | Simpler visibility model | Slower CPU accesses possible |
| Cached with range maintenance | Potentially faster rendering | Maintenance, isolation, lifetime complexity |
| Cached assets, separate device buffers | Optimize distinct uses | Layout and movement costs |

Compare complete updates, CPU cost, and bandwidth after establishing correctness. CPU fill speed alone is insufficient.

SDK/GPU hooks may already maintain caches. Identify their scopes and ownership to avoid gaps or duplication.

## 9. Experiments and Summary

Compare identical addresses, formats, and patterns for:

- CPU-write/device-read.
- Device-write/CPU-check.
- Partial versus exclusive complete lines.
- Repeated alternating patterns and long runs.

A cache-setting change that removes a symptom is evidence, not final proof. Verify direction, range, and timing.

Next: [PXP Capabilities and Limits](13-pxp-capabilities.md), building acceleration on correct handoffs.

## References

- [CMSIS Cortex-M7 D-Cache API](https://arm-software.github.io/CMSIS_6/main/Core/group__Dcache__functions__m7.html)
- [NXP RT1170 entry point](https://www.nxp.com/products/i.MX-RT1170)
- [LVGL 9.2 PXP buffer handling](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/pxp/lv_draw_buf_pxp.c)
