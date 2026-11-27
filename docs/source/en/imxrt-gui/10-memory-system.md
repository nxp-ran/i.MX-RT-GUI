# Article 10: Why Does GUI Performance Depend on Memory?

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [How Do LCDIF / eLCDIF Display Controllers Work?](09-lcdif-elcdif.md)
>
> Next: [Single/Double Buffering and Tearing](11-buffering-and-tearing.md)
>
> Goal: Build a memory map and access matrix, separating capacity, reachability, and bandwidth. Budgets are assumptions, not board measurements.

## 1. Memory Is Not One Freely Allocatable Array

Advertised RAM can occupy different regions shared by code, heaps, stacks, other cores, and peripherals.

CPU access does not establish display/PXP/GPU/DMA access. Latency and cache properties can also differ.

For each allocation, ask:

```text
Contents -> Writer -> Readers -> Placement -> Handoff -> Release
```

Resolution times bytes per pixel is only part of GUI design.

## 2. Three Storage Roles

| Storage | Suitable uses | Verify |
| --- | --- | --- |
| On-chip RAM | Tasks, widgets, hot data, small buffers | Partitions, ownership, peripheral access |
| External SDRAM / PSRAM | Frames, layers, decoding | Controller compatibility, timing, capacity, throughput |
| Flash / nonvolatile storage | Code, images, fonts, configuration | Read path, XIP contention, encoding |

A Flash image is not necessarily a valid direct accelerator input.

Some resources are memory mapped; others need filesystems and decoding. Compressed size does not equal runtime RAM size.

Names such as TCM or OCRAM do not replace the target access matrix.

## 3. Build an Access Matrix First

Fill this from manuals and linker layout:

| Data | Producer | Consumer | Required checks |
| --- | --- | --- | --- |
| Objects and stacks | CPU | CPU | Capacity, concurrency, peaks |
| Partial draw buffer | CPU/backend | Transfer or copy engine | Reachability, stride, cache |
| Display frame | CPU/PXP/GPU | Display controller | IP address, format, alignment, lifetime |
| Images and fonts | Flash/decoder | CPU/backend | Encoding, decoding, cache, format |
| GPU workspace | Driver/GPU | Driver/GPU | Allocator and visibility requirements |

Reuse SDK CPU-to-IP address conversion. A valid CPU pointer may not be the register's address.

Multicore sharing also requires permissions, paths, and synchronization, not merely identical pointers.

## 4. Count Concurrent Allocations

Assume 800 × 480 RGB565 double frames and separate partial buffers:

| Allocation | Assumption | KiB |
| --- | --- | --- |
| Display frames | 800 × 480 × 2 B, two | 1,500 |
| Draw buffers | 800 × 40 × 2 B, two | 125 |
| Temporary layer | 200 × 100 × 4 B | 78.125 |
| Decoder workspace | Assumed | 64 |
| Image/font cache | Assumed | 128 |
| GUI, application, stacks | Assumed | 256 |
| Total | No additional margin | 2,151.125 |

This exceeds 2 MiB, or 2,048 KiB.

Do not double-count frames used directly for rendering. Conversely, do not omit simultaneous layer/decoder allocations because they are temporary.

Budget the worst concurrent scene, not average heap usage.

## 5. Three Placement Issues

### 5.1 Alignment and Stride

Compute stride, base alignment, and allocation steps for each consumer. Padding belongs to the allocation.

Cache-line isolation may impose stronger boundaries. Avoid shared lines between maintained pixels and unrelated state.

### 5.2 Fragmentation and Dynamic Objects

Repeated widget creation, variable images, and layers can leave sufficient total free space but no large contiguous block.

Reserve fixed frames early; define limits, lifetimes, and failure policies for variable resources. Permanently caching everything is not a default solution.

### 5.3 External-Memory Initialization

Startup, heaps, and drivers must not access external RAM before it is ready.

If zero-initialized sections reside there, coordinate startup with memory initialization. Moving an array into a section is not a complete migration.

## 6. Budget Each Access Path

800 × 480 RGB565 scanout at 60 Hz reads approximately 46.08 MB/s.

Complete CPU writes at the same rate add 46.08 MB/s. Copies, blending, and intermediates add more.

```text
External Flash --asset reads--> CPU / decoder
                                    |
                                    v
External RAM <--render reads/writes-- CPU / PXP / GPU
    |
    +---scanout reads---> Display controller
```

Budget each bus independently. Summed traffic from unrelated interfaces cannot be compared to one bus's peak.

Shared XIP/asset interfaces can stall code execution. Measure hits, bursts, and waits under real workloads.

## 7. Recalculate Capacity

This is a static budget, not an address or allocator test:

```python
allocations = {
    "display_frames": 800 * 480 * 2 * 2,
    "draw_buffers": 800 * 40 * 2 * 2,
    "temporary_layer": 200 * 100 * 4,
    "decoder": 64 * 1024,
    "resource_cache": 128 * 1024,
    "application_and_stacks": 256 * 1024,
}
capacity = 2 * 1024 * 1024
total = sum(allocations.values())

print(f"Allocated: {total:,} B ({total / 1024:.3f} KiB)")
print(f"Capacity: {capacity:,} B")
print(f"Shortfall: {max(total - capacity, 0):,} B")
```

Output:

```text
Allocated: 2,202,752 B (2151.125 KiB)
Capacity: 2,097,152 B
Shortfall: 105,600 B
```

The shortfall is explicit. Actual allocation failure must use the project's error channel.

## 8. Three Placement Experiments

| Experiment | Action | Observe |
| --- | --- | --- |
| Static scanout | Fixed frame, no animation | Baseline traffic/errors |
| Resource pressure | Revisit peak-resource pages | Heap peaks, large allocations, release |
| Combined pressure | Animation, decoding, communication | Bandwidth, waits, underrun, latency |

Record regional RAM usage, heap/stack peaks, allocation failures, and access errors.

A faster region must still be reachable and coherent for all consumers without harming real-time tasks.

## 9. Summary

Memory needs capacity, reachability, and throughput, supported by real linker and startup behavior.

Next: [Single/Double Buffering and Tearing](11-buffering-and-tearing.md), determining who owns each address and when.

## References

- [NXP RT1170 memory/product entry point](https://www.nxp.com/products/i.MX-RT1170)
- [NXP LCDIFv2 buffer configuration](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/lcdifv2/fsl_lcdifv2.h)
- [LVGL 9.2 display buffers](https://docs.lvgl.io/9.2/porting/display.html)
