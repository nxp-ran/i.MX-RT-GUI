# Article 6: RGB Displays: Pixel Clock and Continuous Scanout

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [8080 / DBI Parallel Displays with FlexIO and Other Resources](05-flexio-dbi-display.md)
>
> Next: [MIPI DSI Displays: The High-Speed Serial Link](07-mipi-dsi-display.md)
>
> Goal: Map panel timing to the display controller and relate formats, frame buffers, continuous scanout, and insufficient data supply.
>
> Scope: An MCU display controller driving an RGB panel. Do not assume every display has or lacks GRAM. Timing and bandwidth are illustrative assumptions, not panel recommendations or measurements.

## 1. RGB Is Not a Wider 8080 Bus

Both interfaces may use several data lines, but they work differently.

In [Article 5](05-flexio-dbi-display.md), the MCU writes windows into display-side storage. Here, the controller continuously outputs pixels at fixed timing.

```text
CPU / renderer
      |
      v
MCU-accessible complete frame buffer
      |
      v
Display controller: Read, queue, generate timing
      |
      v
RGB data + PCLK + synchronization
      |
      v
Panel
```

The GUI can stop redrawing an unchanged image while scanout continues. No rendering tasks does not imply no memory reads.

The CPU need not act during every pixel cycle. The display controller supplies pixels continuously; the CPU generates content, manages buffers, and handles synchronization.

## 2. Five Signal Categories

| Signal | Meaning | Verify |
| --- | --- | --- |
| RGB data | Current pixel's components | Bit mapping, format, active levels |
| PCLK | Pixel clock | Frequency, sampling edge, waveform |
| HSYNC | Horizontal synchronization | Polarity and width |
| VSYNC | Vertical synchronization | Polarity and width |
| DE | Active-pixel indication | Polarity, position, width |

Panels can use DE mode, sync mode, or combinations. Wiring and configuration must match the module.

Distinguish the edge that drives data from the edge on which the panel samples it. Interpret drive/capture configuration names using both driver and panel documentation.

Do not impose one universal polarity or edge based on experience with a common panel.

## 3. Lines and Frames

One timing representation is:

```text
Line:
[HSYNC] [Back porch] [Active pixels] [Front porch]
                       <-- DE -->

Frame:
[VSYNC] [Back porch] [Active lines] [Front porch]
```

Porches and sync widths are part of panel operation, not meaningless overhead settings.

Common relationships:

```text
H_total = H_active + H_sync + H_back_porch + H_front_porch
V_total = V_active + V_sync + V_back_porch + V_front_porch

PCLK = H_total × V_total × Refresh
```

Horizontal intervals commonly use pixel-clock cycles, and vertical intervals use lines. Registers can encode counts differently; time, count, and register value are not interchangeable.

Some registers use actual counts and others count minus one. Determine which transformations the SDK already performs.

## 4. Map Panel Data to Configuration

Reuse the invented timing from [Article 3](03-memory-and-bandwidth.md):

| Panel parameter | Example | Meaning |
| --- | --- | --- |
| Active width | 800 | Pixels per active line |
| Active height | 480 | Active lines per frame |
| HSW / HBP / HFP | 48 / 40 / 40 | Horizontal sync, back porch, front porch |
| VSW / VBP / VFP | 3 / 29 / 13 | Vertical sync, back porch, front porch |
| Refresh | 60 Hz | Target scan cadence |
| Polarities and edge | Unspecified | Obtain from the actual panel |

Calculate:

```text
H_total = 928
V_total = 525
PCLK = 928 × 525 × 60 = 29.232 MHz

Line period = 928 / 29,232,000 ≈ 31.746 us
Frame period = 1 / 60 ≈ 16.667 ms
```

If the actual clock is 30 MHz with unchanged counts:

```text
Actual refresh = 30,000,000 / (928 × 525) ≈ 61.576 Hz
```

Writing "60 Hz" in software does not establish the real rate. Verify clocks and waveforms, then confirm the result remains within panel limits.

## 5. Memory Format and RGB Pin Width Are Separate

An RGB565 frame uses two bytes per pixel; that does not require a panel with only 16 color-data lines.

Supported controllers can sometimes map a narrower source to a wider output. Expansion and mapping depend on the actual path.

Likewise, 24-bit RGB output does not prove tightly packed RGB888 memory:

| Stage | One possible choice |
| --- | --- |
| Image asset | ARGB8888 |
| Draw target | RGB565 |
| Frame storage | RGB565, 2 B/pixel |
| Output bus | A supported controller/panel width |

The referenced eLCDIF example uses XRGB8888 source memory and independently configures the output bus.

### 5.1 Verify Pin Mapping

Show red, green, and blue separately, followed by varying component intensities.

Distinguish:

- Entire red/blue channel swaps.
- Missing or incorrectly mapped bits.
- Reduced levels from unused low bits.
- Mismatched memory interpretation.

Do not copy an SPI byte-swap solution blindly into RGB frame storage. A scanout controller interprets memory; it does not merely serialize every byte unchanged.

## 6. Address and Stride

For an ordinary row-major RGB565 image:

```text
pixel_address(x, y) = base + y × stride + x × 2
```

If rendering uses 1,664 B stride while scanout reads 1,600 B per row, the first row can look correct while later rows progressively shift.

Constrain address, active width, stride, and format with a consistent layout.

An important limitation:

> A generic software model containing stride does not prove that every controller mode accepts arbitrary stride.

The referenced eLCDIF RGB configuration has no separate stride field. LCDIFv2 layer buffers provide `strideBytes`. Arrange memory for the actual supported path.

Also verify alignment, reachability, and cache coherency. CPU access alone does not establish display-controller access.

## 7. Continuous Pixel Supply

Read paths and FIFOs typically separate variable memory latency from fixed output cadence.

```text
RAM / bus -> Controller reads -> FIFO -> PCLK-paced output
```

A FIFO absorbs brief delays, but it is finite.

Long contention can prevent refill and cause underrun. Symptoms and flags depend on the controller.

For 800 × 480 RGB565 at 60 Hz:

```text
800 × 480 × 2 × 60 = 46.08 MB/s
```

That excludes rendering and asset reads.

Sixty complete CPU writes per second add another 46.08 MB/s in a simplified model; blending and copies add more.

**Measure static scanout, dynamic rendering, and application load separately, then validate them together.**

Theoretical RAM peaks do not account for real arbitration and short stalls.

## 8. A Minimal Initialization Strategy

A verifiable baseline is:

1. Fix the panel, pins, and power design.
2. Configure system, memory, and display clocks.
3. Allocate a complete frame in reachable, aligned RAM.
4. Fill a color or pattern and establish memory visibility.
5. Configure dimensions, porches, sync, format, and bus.
6. Set a valid address and prepare required state events.
7. Start scanout, panel operation, and backlight in the hardware-required order.
8. Inspect waveforms, actual rates, and errors.

Additional panel-control interfaces and backlight order are module-specific. This is not a universal board initialization sequence.

SDK defaults illustrate structures, not the target panel's timing.

## 9. Check Timing and Scanout with a Script

This script calculates assumptions only. It neither configures registers nor measures clocks:

```python
width, height = 800, 480
hsw, hbp, hfp = 48, 40, 40
vsw, vbp, vfp = 3, 29, 13
refresh = 60
bytes_per_pixel = 2

h_total = width + hsw + hbp + hfp
v_total = height + vsw + vbp + vfp
pixel_clock = h_total * v_total * refresh
actual_clock = 30_000_000
frame_bytes = width * height * bytes_per_pixel

print(f"Totals: {h_total} pixels/line, {v_total} lines/frame")
print(f"Target PCLK: {pixel_clock / 1_000_000:.3f} MHz")
print(f"Line period: {h_total / pixel_clock * 1_000_000:.3f} us")
print(f"Frame period: {1000 / refresh:.3f} ms")
print(f"At 30 MHz: {actual_clock / (h_total * v_total):.3f} Hz")
print(f"RGB565 frame: {frame_bytes:,} B")
print(f"Active scan reads: {frame_bytes * refresh / 1_000_000:.2f} MB/s")
```

Output:

```text
Totals: 928 pixels/line, 525 lines/frame
Target PCLK: 29.232 MHz
Line period: 31.746 us
Frame period: 16.667 ms
At 30 MHz: 61.576 Hz
RGB565 frame: 768,000 B
Active scan reads: 46.08 MB/s
```

Substitute measured PCLK and verify line/frame timing, not just whether an image appears.

## 10. From Static Patterns to Updates

First validate stable scanout from one fixed complete frame.

| Pattern | Main check |
| --- | --- |
| Black/white and RGB | Basic output, channels, format |
| Color bars | Mapping and levels |
| Distinct corner markers | Orientation, active area, offsets |
| Line numbers or checkerboard | Stride and scan order |
| Moving rectangle | Scan/write conflict |
| Alternating frame colors | Submission, swapping, old-buffer release |

Writing a frame during scanout can tear. Double-frame designs need actual swap confirmation, not immediate reuse after a register write.

Partial redraw reduces rendering but does not remove complete scanout traffic.

The buffering chapter will expand synchronization; first establish who reads what and when.

## 11. Layered Troubleshooting

| Symptom | Initial investigation |
| --- | --- |
| Backlight but no valid image | Power, reset, running state, PCLK, DE, address |
| Entire image shifted | Porches, sync, active-region settings |
| Red/blue swapped | Channel order, IOMUX, mapping |
| Incorrect levels or stuck color bits | Data wiring, mapping, format |
| Progressive row shifts | Layout, stride, width, read mode |
| Static works, updates fail | Cache, tearing, bandwidth, lifetime |
| Other tasks cause corruption | Arbitration, FIFO underrun, latency |
| Debug/Release differ | Rendering time, races, CPU load, not frequency alone |

Underrun, bus errors, and frame events are evidence. Record before clearing correctly through the SDK. Clearing an error is not fixing it.

## 12. Summary

An RGB system continuously reads MCU frame storage and emits panel-specific timing.

- Calculate PCLK from complete timing.
- Configure output and memory formats separately.
- Match layouts to supported controller reads.
- Static images can still consume scanout bandwidth.
- Dynamic updates require cache, synchronization, and ownership.

Next: [MIPI DSI Displays: The High-Speed Serial Link](07-mipi-dsi-display.md). A serial physical link does not remove the continuous source-data problem.

## References

- [NXP eLCDIF configuration and interface](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/elcdif/fsl_elcdif.h)
- [NXP eLCDIF RGB example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/elcdif/rgb/elcdif_rgb.c)
- [NXP LCDIFv2 buffer configuration](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/lcdifv2/fsl_lcdifv2.h)

These sources explain existing APIs. Verify panel electrical/timing limits and controller capability against the selected device and module.
