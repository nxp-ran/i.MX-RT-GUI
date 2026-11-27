# Article 11: Single/Double Buffering and Tearing

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Why Does GUI Performance Depend on Memory?](10-memory-system.md)
>
> Next: [Cache, MPU, and DMA Coherency](12-cache-mpu-dma.md)
>
> Goal: Separate buffer counts, modes, and synchronization through ownership. Timelines are illustrative, not measurements.

## 1. Why Another Buffer Does Not Automatically Prevent Tearing

Tearing mixes content from different update instants in one visible scan.

If scanout reads the top before a producer changes the bottom, the image can contain both versions.

GRAM can also be updated while the panel scans it. Neither GRAM nor software double buffering guarantees atomic presentation.

```text
Scanner: Read old content -------- Read new content
Writer:                  Update image
Result: One scan contains multiple image versions
```

The decisive issue is handoff timing, not capacity alone.

## 2. Three Independent Choices

| Choice | Question |
| --- | --- |
| Buffer count | How many independent allocations exist? |
| Render mode | Partial, direct, or full redraw? |
| Synchronization | When are transfer, activation, and release allowed? |

Two small buffers alternate rendering/transfer. Two full frames can support front/back presentation. They are different architectures.

A second LVGL pointer cannot by itself change panel scanning.

## 3. One Display Frame

A single frame saves memory and can suit low-frequency or regional updates.

Writing it during scanout needs a defined tearing policy. Small regions can still overlap active reads.

Options include:

- A controller-supported safe update window.
- Bounded areas and execution time.
- Explicitly accepting measurable tearing where permitted.
- Complete back frames or another supported mechanism.

Not every panel allows paused scanning. Stopping scanout is not a universal solution.

## 4. Ownership with Two Complete Frames

Typical sequence:

```text
A: SCANNING                    B: DRAWABLE
                                   |
                                   v
                              Complete B
                                   |
                                   v
                         Request boundary activation
                                   |
                                   v
                         Confirm B active and A released

B: SCANNING                    A: DRAWABLE
```

After submitting B, both may be unavailable: A is scanned and B belongs to downstream hardware.

Any VSYNC is not necessarily confirmation of this request. Use the driver contract, active address, or release callback and verify timing.

Do not clear wait state after submission and lose an already delivered event.

## 5. Partial Updates Can Expose Old Content

Suppose A is current and B is one update behind.

Updating only a button in B and presenting it can restore stale pixels elsewhere.

Synchronize inconsistent regions or redraw the complete back frame.

| Strategy | Benefit | Cost |
| --- | --- | --- |
| Full back-frame redraw | Simple content consistency | More rendering |
| Dirty-region synchronization | Useful for sparse changes | Copies, state, timing |
| One frame plus regional copy | Lower capacity | Scan/write conflicts remain |

LVGL 9.2 DIRECT double buffering includes region synchronization. Do not blindly add a second full-screen copy or release a hardware-owned frame prematurely.

## 6. GRAM and TE

Two transfer buffers protect MCU rendering against source overwrite. They do not create atomic panel-GRAM swaps.

TE requires:

- Correct event/mode interpretation.
- Scan/write direction checks.
- Actual update duration.
- Supported windows and storage mechanisms.

A 320 × 240 RGB565 payload at single-line 40 MHz takes approximately 30.72 ms, longer than a 60 Hz period of 16.67 ms.

Starting on TE alone therefore does not prove no full-screen tearing.

## 7. What Does Triple Buffering Solve?

A third frame can reduce producer waiting while introducing queue policy.

| Policy | Priority | Risk |
| --- | --- | --- |
| FIFO presentation | Preserve every frame | More input latency |
| Newest ready frame | Interactive latency | Intermediate frames dropped |
| Wait for a free frame | Simple resource/state model | Limited throughput |

Drops need explicit policy and counters. Overwriting active/pending frames is not a valid newest-frame strategy.

Track FREE, DRAWING, READY, PENDING, and SCANNING under one owner.

## 8. Diagnostic Tests

| Test | Purpose |
| --- | --- |
| Alternating complete colors | Atomic activation and mixed boundaries |
| Numbered moving rectangle | Repeats, drops, old content |
| Two independently changing regions | Missing partial-frame synchronization |
| Deliberately slower drawing/transfer | Missed-boundary behavior |
| Faster submissions | Queue limits and rejection |

Record request IDs, addresses, events, and releases. Visual observation alone does not validate all handoffs.

## 9. Summary

Tearing control aligns image versions with scanout. Counts, modes, synchronization, and queue policy must be designed together.

Next: [Cache, MPU, and DMA Coherency](12-cache-mpu-dma.md), ensuring every participant sees the same data.

## References

- [LVGL 9.2 PARTIAL/DIRECT/FULL](https://docs.lvgl.io/9.2/porting/display.html)
- [NXP LCDIFv2 shadow load](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/lcdifv2/fsl_lcdifv2.h)
