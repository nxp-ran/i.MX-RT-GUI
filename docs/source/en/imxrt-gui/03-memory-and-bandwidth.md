# Article 3: Budget Resolution, Display Memory, and Bandwidth Before Choosing a Screen

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [i.MX RT Graphics Capabilities and Platform Selection](02-platform-selection.md)
>
> Next: [SPI / QSPI Displays: From Commands to Partial Updates](04-spi-qspi-display.md)
>
> Goal: Establish basic display feasibility with four budgets: capacity, pixel timing, interface throughput, and memory traffic.
>
> Calculation convention: Every number is theoretical under stated assumptions, not a performance measurement for a particular chip, panel, or board.

## 1. Why Calculate Before Connecting the Screen?

A common development sequence is to choose a display, connect it, and only then discover that:

- Two complete frame buffers do not fit.
- Each full-screen SPI transfer takes more than a hundred milliseconds.
- Transparent effects saturate external-memory bandwidth.
- A clock based only on active resolution does not satisfy panel timing.

These problems need not wait until code runs.

In [Article 2](02-platform-selection.md), capacity and throughput were separate selection gates. This article makes them calculable.

Distinguish three quantities:

```text
Capacity:   How much data must exist at the same time?
Throughput: How much data must be processed or transferred per second?
Timing:     Within which time window must the data arrive?
```

Enough capacity does not establish throughput. Enough average throughput does not guarantee timely delivery during every display interval.

## 2. Budget One: Pixel Formats

A pixel can occupy different numbers of bytes at different stages.

| Format | Color representation | Tightly packed storage | Alpha |
| --- | --- | --- | --- |
| RGB565 | R: 5 bits, G: 6, B: 5 | 2 B/pixel | None |
| RGB888 | R, G, B: 8 bits each | 3 B/pixel | None |
| XRGB8888 | 32-bit container with 24-bit RGB and unused bits | 4 B/pixel | Not meaningful Alpha |
| ARGB8888 | 24-bit RGB and 8-bit Alpha | 4 B/pixel | Present |

This describes common tightly packed capacities, not every hardware layout.

Distinguish:

- Encoded asset format.
- Decoded pixel format.
- LVGL draw-target format.
- PXP / GPU input and output formats.
- Display frame-buffer storage.
- Pixel format on the display link.

For example, a compressed Flash asset can decode into ARGB8888 and then blend into an RGB565 frame:

- Flash capacity follows the compressed file.
- Decoder capacity follows ARGB8888.
- Display-frame capacity follows RGB565.
- Memory traffic includes both reads and writes.

Do not use one format for every stage.

Some hardware may not accept RGB888 as a tightly packed three-byte destination. It may require a 32-bit container or particular alignment. Budget the actual configuration.

## 3. Budget Two: Frame-Buffer Capacity

### 3.1 The Basic Full-Frame Calculation

For tightly packed storage without row padding:

```text
M_frame = W × H × b
```

Where:

- `W`: Width in pixels.
- `H`: Height in pixels.
- `b`: Bytes per pixel.

Typical capacity estimates:

| Resolution | One RGB565 frame | Two RGB565 frames | One ARGB8888 frame |
| --- | --- | --- | --- |
| 320 × 240 | 153,600 B = 150 KiB | 300 KiB | 300 KiB |
| 480 × 272 | 261,120 B = 255 KiB | 510 KiB | 510 KiB |
| 800 × 480 | 768,000 B = 750 KiB | 1,500 KiB | 1,500 KiB |
| 1024 × 600 | 1,228,800 B = 1,200 KiB | 2,400 KiB | 2,400 KiB |

Two ARGB8888 frames require twice the corresponding single-frame capacity.

Units:

```text
1 KiB = 1,024 B
1 MiB = 1,048,576 B
1 MB  = 1,000,000 B
```

Capacity uses KiB / MiB; bandwidth here uses decimal MB/s. Do not mix them in comparisons.

### 3.2 Why Stride Can Increase Capacity

Stride is the actual byte distance between successive image rows.

If every row must align to `A` bytes:

```text
row_bytes = W × b
stride = ceil(row_bytes / A) × A
M_frame = stride × H
```

Consider an assumed 454 × 480 RGB565 buffer with 64-byte row alignment:

```text
Packed row length = 454 × 2 = 908 B
Actual stride = ceil(908 / 64) × 64 = 960 B

Packed capacity = 908 × 480 = 435,840 B
Actual capacity = 960 × 480 = 460,800 B = 450 KiB
Extra capacity = 24,960 B = 24.375 KiB
```

This demonstrates alignment overhead; it is not a universal 64-byte requirement for any chip.

Base-address alignment and row alignment are separate. An aligned buffer start does not prove that every row satisfies the hardware.

### 3.3 Partial Draw-Buffer Capacity

For a buffer containing `h` lines:

```text
M_draw = stride_draw × h
```

A tightly packed, 800-pixel-wide, 40-line RGB565 buffer requires:

```text
800 × 40 × 2 = 64,000 B = 62.5 KiB
```

Two such buffers require 125 KiB.

Interpret the saving within the architecture:

- A GRAM display retains the full image after region writes.
- Continuous scanout usually still needs a complete display frame.
- When rendering directly into the complete frame, do not count that same allocation again as an independent draw buffer.

**Count real allocations, not conceptual names.**

## 4. Total Memory Is More Than Twice the Frame Size

GUI memory extends beyond complete frames.

The example below explicitly assumes two complete display frames plus two separate partial draw buffers. It is a budgeting example, not a universal architecture recommendation.

| Allocation | Assumed configuration | Capacity |
| --- | --- | --- |
| Display frame buffers | 800 × 480, RGB565, two | 1,536,000 B = 1,500 KiB |
| Independent draw buffers | 800 × 40, RGB565, two | 128,000 B = 125 KiB |
| Temporary off-screen layer | 200 × 100, ARGB8888, one | 80,000 B = 78.125 KiB |
| Decoder workspace | Assumed budget | 65,536 B = 64 KiB |
| Runtime image/font caches | Assumed budget | 131,072 B = 128 KiB |
| Application, GUI heap, stacks | Assumed budget | 262,144 B = 256 KiB |
| **Total** | Excluding additional safety margin | **2,202,752 B = 2,151.125 KiB** |

This exceeds 2 MiB, or 2,097,152 B, by 105,600 B.

Looking only at two RGB565 frames, approximately 1.465 MiB, would misleadingly suggest substantial room on a 2 MiB platform.

Adjust the budget for:

- Which layers and workspaces coexist.
- Buffers that can safely share allocations.
- Resources already included in heap estimates, avoiding double counting.
- Fragmentation, alignment, and worst-case overhead.
- Regions unavailable to the display or accelerators.

Safety margin should follow measured peaks, allocation strategy, and reliability requirements, not a universal percentage.

## 5. Budget Three: Scanout Reads

For typical continuous full-frame scanout, calculate active pixel traffic:

```text
P_active = W × H × F_panel
B_scan = W × H × b_frame × F_panel
```

`F_panel` is the panel scan frequency.

For 800 × 480, RGB565, 60 Hz:

```text
P_active = 800 × 480 × 60
         = 23,040,000 pixel/s

B_scan = 800 × 480 × 2 × 60
       = 46,080,000 B/s
       = 46.08 MB/s
```

This traffic may continue with a static image because scanout repeatedly reads the existing frame.

With a 32-bit frame format:

```text
800 × 480 × 4 × 60 = 92.16 MB/s
```

Changing from RGB565 to 32-bit storage therefore increases both capacity and active scanout traffic.

These formulas estimate active pixel reads, not every bus transaction. Bursts, FIFOs, layouts, and additional reads depend on the controller and must be checked or measured.

## 6. Pixel Clock Includes More Than Active Resolution

RGB timing includes synchronization and blanking.

Common relationships are:

```text
H_total = H_active + H_sync + H_back_porch + H_front_porch
V_total = V_active + V_sync + V_back_porch + V_front_porch

PCLK = H_total × V_total × F_panel
```

The following is an **invented timing example**, not a configuration for a particular panel:

| Parameter | Example value |
| --- | --- |
| Horizontal active pixels | 800 |
| Horizontal sync width | 48 |
| Horizontal back porch | 40 |
| Horizontal front porch | 40 |
| Vertical active lines | 480 |
| Vertical sync width | 3 |
| Vertical back porch | 29 |
| Vertical front porch | 13 |
| Refresh rate | 60 Hz |

Then:

```text
H_total = 800 + 48 + 40 + 40 = 928
V_total = 480 + 3 + 29 + 13 = 525

PCLK = 928 × 525 × 60
     = 29,232,000 Hz
     = 29.232 MHz
```

Active resolution alone gives 23.04 MHz, below this example's required clock.

Do not count every blanking slot as a frame-buffer read:

- Pixel clock describes interface timing.
- Frame reads describe memory accesses.
- Blanking output and prefetch behavior are controller-specific.

Also verify signal polarities, sampling edges, and register count encodings. Correct totals alone do not complete the configuration.

## 7. Budget Four: Interface Throughput

### 7.1 Single-Line SPI

For single-data-line, single-edge SPI:

```text
B_link_ideal = f_sclk / 8
```

Assume a pixel-write clock of 40 MHz:

```text
40,000,000 / 8 = 5,000,000 B/s = 5 MB/s
```

A complete 320 × 240 RGB565 payload requires:

```text
T_pixel = 153,600 / 5,000,000
        = 0.03072 s
        = 30.72 ms
```

Ideal complete-payload throughput is approximately:

```text
1 / 0.03072 ≈ 32.55 transfers/s
```

This is not guaranteed visible FPS. Commands, gaps, rendering, cache maintenance, scanout, and scheduling are excluded.

At 800 × 480:

```text
T_pixel = 768,000 / 5,000,000 = 153.6 ms
Ideal complete-payload throughput ≈ 6.51 transfers/s
```

A faster CPU cannot make that same 40 MHz single-line link transfer 60 complete images per second.

### 7.2 Multiple Data Lines

If the pixel stage actually uses `n` lines and one transfer edge:

```text
B_link_ideal = f_sclk × n / 8
```

At 40 MHz with RGB565:

| Pixel-data stage | Ideal bandwidth | 320 × 240 payload time | 800 × 480 payload time |
| --- | --- | --- | --- |
| 1 data line | 5 MB/s | 30.72 ms | 153.6 ms |
| 4 data lines | 20 MB/s | 7.68 ms | 38.4 ms |

The factor of four applies to the data stage. Commands, addresses, and control can use different widths.

Panel protocol, MCU transactions, and drivers must all support this mode.

QuadSPI Flash support alone does not establish QSPI display compatibility.

### 7.3 An Explicit Efficiency Assumption

For an initial estimate, use an explicitly assumed efficiency `eta`:

```text
B_effective = B_link_ideal × eta
T_transfer = S_pixel / B_effective
```

If the single-line 40 MHz link is **assumed**, not measured, to achieve 80%:

```text
B_effective = 5 × 0.8 = 4 MB/s

320 × 240: 153,600 / 4,000,000 = 38.4 ms
800 × 480: 768,000 / 4,000,000 = 192 ms
```

80% is not a measured board result or a universal driver recommendation.

Measure effective pixel bytes divided by transfer time, then replace the assumption.

If commands and gaps are budgeted explicitly, do not also apply an efficiency factor containing the same overhead.

### 7.4 DSI Payload Versus Link Requirements

For 800 × 480, 60 Hz, with RGB888 on the link:

```text
Active payload bit rate = 800 × 480 × 60 × 24
                        = 552.96 Mbit/s
```

With two data lanes, the average active-payload share is 276.48 Mbit/s/Lane.

This is not a directly usable DSI PHY rate.

Packet structure, video mode, blanking handling, available sending windows, HS/LP transitions, and panel restrictions must also be included.

An RGB565 memory frame does not automatically mean a 16-bit link format.

## 8. Why Partial Updates Can Matter More Than Frequency

Suppose each update changes only 5% of an 800 × 480 RGB565 screen:

```text
Pixels per update = 800 × 480 × 0.05 × 2
                  = 38,400 B

At 60 updates per second:
Pixel transfer rate = 38,400 × 60
                    = 2.304 MB/s
```

That is much less than 46.08 MB/s for 60 complete RGB565 images per second.

The benefit depends on architecture.

### 8.1 On-Demand Transfers to GRAM

Region writes directly reduce MCU-to-display pixel traffic.

They can also reduce rendering work.

### 8.2 Continuous Full-Frame Scanout

Partial rendering reduces CPU/accelerator traffic.

If the display controller still scans 800 × 480 RGB565 at 60 Hz, its 46.08 MB/s baseline active traffic remains.

> "LVGL redraws 5%" does not mean "the display controller reads 5%."

Shadows, antialiasing, and both old and new positions of moving objects can expand invalidated regions. Budget actual rendering and transfer areas, not nominal widget dimensions.

## 9. Add Every Memory Reader and Writer

Active display data is often only one part of the memory budget.

Assume:

- 800 × 480.
- 60 complete processing updates per second.
- RGB565 display frames.
- All listed source and destination accesses cross the memory path being counted.
- Cache, bursts, compression, intermediates, and internal reuse are excluded.

| Operation | Rendering accesses per pixel | Rendering bandwidth | Including scanout |
| --- | --- | --- | --- |
| RGB565 solid fill | Write 2 B | 46.08 MB/s | 92.16 MB/s |
| RGB565 image copy | Read 2 B + write 2 B | 92.16 MB/s | 138.24 MB/s |
| ARGB8888 foreground over RGB565 background | Read 4 B + read 2 B + write 2 B | 184.32 MB/s | 230.40 MB/s |

Recalculate the third row:

```text
Rendering traffic = 800 × 480 × 60 × (4 + 2 + 2)
                  = 184,320,000 B/s

Scanout reads = 46,080,000 B/s
Total = 230,400,000 B/s
```

This is not measured PXP/GPU bus utilization or a claim that every blending implementation generates identical external transactions.

It demonstrates that **blending cannot be budgeted solely from the two-byte final pixel.**

If resources use a different bus, budget that path separately. An additional complete copy adds its own reads and writes.

### 9.1 Double Buffering Does Not Automatically Double Scanout Bandwidth

Another complete frame first increases capacity.

Typical double-buffer scanout reads one selected buffer each cycle, not both simultaneously.

Background rendering, content synchronization, and copies can add traffic. Count those actual operations instead of multiplying every bandwidth by two.

### 9.2 A Faster GPU Does Not Guarantee Faster Visible Updates

A GPU can reduce CPU computation while still reading assets, writing results, and competing with scanout.

If memory or the display link is already the bottleneck, faster drawing may not improve visible updates.

Measure the full path, not only one drawing function.

## 10. Average Bandwidth Does Not Guarantee Timely Supply

A theoretical memory peak might be:

```text
16-bit bus, 100 MHz, one data transfer per cycle:
Ideal peak = 2 B × 100,000,000 = 200 MB/s
```

Do not compare that number with 230.40 MB/s or 46.08 MB/s and immediately declare the design feasible.

First verify that the memory and controller allow the assumed operating point, then include:

- Refresh, commands, and row changes.
- Read/write turnarounds.
- CPU, DMA, accelerator, and scanout contention.
- Burst lengths, access continuity, and arbitration.
- Cache maintenance and application traffic.

The display FIFO may require timely refill during particular intervals. Sufficient average bandwidth does not prevent a late line or burst.

Observe:

1. Baseline static scanout.
2. Sustained complete updates.
3. Stability with representative application load.
4. FIFO-underrun or related errors.
5. Short peaks, not just long averages.

## 11. Budget Throughput and Latency Separately

For serial rendering and transfer:

```text
T_update = T_draw + T_transfer + T_sync
```

An overlapped pipeline may approach:

```text
T_cycle ≈ max(T_draw, T_transfer) + Non-overlapping overhead
```

This is not input-to-visible-response latency.

Latency can also include:

- Input sampling waits.
- GUI scheduling.
- Queueing.
- Swap or TE waits.
- Scanout reaching the affected region.
- Panel response.

Throughput and latency optimization can point in different directions. Deeper queues may keep hardware busy while increasing input delay.

## 12. Recalculate with a Small Script

This standard-library Python example calculates the 800 × 480 assumptions.

It neither detects device capabilities nor accesses hardware. Verify target formats, timing, and interfaces before replacing the inputs.

```python
width, height = 800, 480
bytes_per_pixel = 2
alignment = 64
frame_buffers = 2
panel_hz = 60

row_bytes = width * bytes_per_pixel
stride = ((row_bytes + alignment - 1) // alignment) * alignment
frame_bytes = stride * height
allocated_bytes = frame_bytes * frame_buffers
scan_bytes_per_second = width * height * bytes_per_pixel * panel_hz

h_total = width + 48 + 40 + 40
v_total = height + 3 + 29 + 13
pixel_clock = h_total * v_total * panel_hz

spi_clock = 40_000_000
data_lines = 1
assumed_efficiency = 0.8
link_bytes_per_second = spi_clock * data_lines * assumed_efficiency / 8
pixel_bytes = width * height * bytes_per_pixel
transfer_ms = pixel_bytes / link_bytes_per_second * 1000

print(f"Stride: {stride:,} B")
print(f"One frame: {frame_bytes:,} B ({frame_bytes / 1024:.3f} KiB)")
print(f"Frame allocation: {allocated_bytes:,} B")
print(f"Active scan payload: {scan_bytes_per_second / 1_000_000:.3f} MB/s")
print(f"Example RGB PCLK: {pixel_clock / 1_000_000:.3f} MHz")
print(f"Assumed SPI payload rate: {link_bytes_per_second / 1_000_000:.3f} MB/s")
print(f"Estimated full-screen SPI transfer: {transfer_ms:.3f} ms")
```

Output:

```text
Stride: 1,600 B
One frame: 768,000 B (750.000 KiB)
Frame allocation: 1,536,000 B
Active scan payload: 46.080 MB/s
Example RGB PCLK: 29.232 MHz
Assumed SPI payload rate: 4.000 MB/s
Estimated full-screen SPI transfer: 192.000 ms
```

RGB timing and SPI throughput here demonstrate two independent designs, not a panel running both interfaces simultaneously.

## 13. Turn the Budget into a Checklist

| Item | Calculation inputs | Validation |
| --- | --- | --- |
| Frame capacity | Resolution, actual format, stride, count | Linker layout and allocation |
| Working RAM | Partial buffers, layers, decoding, heap, stacks | Worst-case peak |
| Scanout | Frame format and refresh | Controller state and memory traffic |
| Rendering | Asset/background reads and destination writes | Timing and access path |
| Link | Width, clock, protocol, area | Payload / measured time |
| Timing | Sync, porches, polarity, clock | Panel documentation and waveforms |
| Synchronization | DMA completion, swaps, TE, cache | Timelines and errors |
| Response | Input, scheduling, queues, scanout | Event-to-visible-change measurement |

Keep theoretical, assumed, and measured figures in separate columns.

Replace assumptions only after actual validation.

## 14. Summary: One Image, Four Budgets

Before wiring and driver work, calculate:

1. **Capacity:** Which pixels and workspaces coexist?
2. **Timing:** When must the panel receive data?
3. **Link:** How many active pixels can be transferred per second?
4. **Memory:** How much do rendering, copies, blending, and scanout read and write?

Partial updates reduce change-driven work. Acceleration changes execution. Neither automatically eliminates baseline scanout traffic or replaces capacity and protocol checks.

Next: [SPI / QSPI Displays: From Commands to Partial Updates](04-spi-qspi-display.md), applying the budget to address windows, byte order, and transfers.

## References

- [LVGL 9.2 display interface](https://docs.lvgl.io/9.2/porting/display.html): Buffers, modes, and flush completion.
- [NXP RT1060 product entry point](https://www.nxp.com/products/i.MX-RT1060): Display and memory documentation.
- [NXP RT1170 product entry point](https://www.nxp.com/products/i.MX-RT1170): GPU, MIPI, and memory documentation.

These formulas are general budgeting models. Actual timing, formats, alignment, and transactions must follow the target chip and panel.
