# Article 5: 8080 / DBI Parallel Displays with FlexIO and Other Resources

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [SPI / QSPI Displays: From Commands to Partial Updates](04-spi-qspi-display.md)
>
> Next: [RGB Displays: Pixel Clock and Continuous Scanout](06-rgb-display.md)
>
> Goal: Understand 8080-style commands, data, and read/write timing, then combine FlexIO, DMA, and partial updates into a reliable path.
>
> Scope: An 8-bit or 16-bit 8080-style display with a controller and GRAM. Verify pins, FlexIO instances, DMA routing, and panel support for the actual i.MX RT. Calculations and offline scripts are not board measurements.

## 1. What Changes When Moving from Serial to Parallel?

In [Article 4](04-spi-qspi-display.md), the MCU sets a window and writes pixels into display GRAM through a serial link.

The same logic commonly applies to an 8080-style interface:

```text
Render region -> Set window -> Send pixels -> Display GRAM -> Panel scanout
```

The transport changes: a set of data pins transfers a bus word during each read/write cycle instead of sending bits through one line.

A parallel display does not automatically become an RGB panel continuously scanned by the MCU. A GRAM-based display can still retain an image and accept only changed regions.

| Dimension | Common SPI display | This article's 8080-style display |
| --- | --- | --- |
| Transport | Bits shifted by a serial clock | Bus words transferred by WR / RD cycles |
| Commands and data | D/C or an in-word command bit | RS / D/C |
| Image storage | Display GRAM | Display GRAM |
| Partial update | Address window | Address window |
| Main MCU concerns | Clock, byte order, transaction boundaries | Width, setup/hold times, strobe cycles |

This article uses common Intel 8080-style timing. DBI is a broader display-interface concept; not every DBI mode uses these signals and operations.

## 2. Identify Each Signal

| Signal | Common purpose | Conditions to verify |
| --- | --- | --- |
| D[7:0] / D[15:0] | Data bus | Module mode, bit mapping, voltage |
| CS | Chip select | Polarity and transaction continuity |
| RS / D/C | Command/data selection | Meaning, setup, and hold |
| WR | Write strobe | Polarity, latch edge, pulse width, cycle |
| RD | Read strobe | Read timing, output enable, bus release |
| RESET | Controller reset | Power-up sequence and delays |
| BL | Backlight control | Driver circuit and control method |
| TE | Optional scan synchronization | Event meaning and update window |

A write-only design may not read pixels, but unused RD must not be left arbitrarily floating. Keep it inactive as required by the module.

A controller supporting several interfaces does not prove the module selects the desired one. Hardware straps can determine the mode.

## 3. A Write Cycle Is More Than the WR Pulse

Consider a common model where WR is active low and data is latched on its rising edge. Confirm the actual edge in the target controller documentation.

```text
Time ->

CS       __________active__________________
RS       ----stable command/data selection--
DATA     -----[valid bus word]--------------
WR       --------\________/-----------------
                  pulse    latch edge
```

Check at least:

1. Data and RS setup before the latch.
2. Hold time after the latch.
3. Minimum WR low and high intervals.
4. Minimum interval between consecutive cycles.

A controller requiring a 100 ns write cycle is not satisfied merely by a valid low pulse inside a 60 ns total cycle.

Reads also involve direction changes. Wait for the display to release the bus before the MCU drives it again; the two sides must not drive simultaneously.

A logic analyzer helps inspect ordering. Setup/hold, edge quality, and electrical margin require appropriate waveform measurements.

## 4. Eight Bits Versus Sixteen Bits

An RGB565 pixel contains 16 bits.

### 4.1 Eight-Bit Interface

With the example's high-byte-first convention, red `0xF800` takes two cycles:

```text
First cycle:  D[7:0] = F8
Second cycle: D[7:0] = 00
```

### 4.2 Sixteen-Bit Interface

With matching panel configuration and mapping, one cycle can carry:

```text
D[15:0] = F800
```

This does not mean commands and parameters can also be arbitrarily packed together.

A controller may require each eight-bit parameter to occupy its own sixteen-bit bus cycle, with upper bits handled as documented. Check the panel and driver instead of combining two address parameters as though they were a pixel.

### 4.3 Check Three Widths Separately

| Layer | Question |
| --- | --- |
| Pixel format | How many meaningful bits form a pixel? |
| Physical interface | How many bits are transferred per WR cycle? |
| Memory and DMA | Are sources read as bytes, halfwords, or words? |

A sixteen-bit bus can reduce RGB565 strobe count, but throughput also depends on WR rate, gaps, memory access, and panel limits.

## 5. How FlexIO Generates the Interface

FlexIO provides configurable peripheral resources. It is not simply another name for software repeatedly writing GPIO.

A typical path is:

```text
Pixel RAM
    |
    v
CPU / DMA writes shifter buffers
    |
    v
FlexIO shifters + timer
    |
    v
Parallel data + WR
    |
    v
Display controller
```

Shifters organize data, a timer generates timing, and CS/RS may be handled by board GPIO callbacks.

The referenced NXP MCULCD driver supports eight- and sixteen-bit buses and uses a start index to describe contiguous FlexIO data pins.

Check:

- Whether the package exposes the required pins.
- Whether IOMUX can form the driver's required combination.
- Shifter counts and index restrictions.
- Timer, WR, and RD availability.
- DMA requests on the selected FlexIO instance.
- Routing to the chosen DMA channel.

**FlexIO availability does not mean any pins and any DMA channel can form a display interface.**

### 5.1 Clock Parameter Units Matter

In the referenced `flexio_mculcd_config_t` version, `baudRate_Bps` describes aggregate bit rate across all data lines, not WR strobe frequency.

Do not use an API parameter directly as a waveform frequency. Calculate or measure WR timing using that driver's divider implementation.

FlexIO module clock, register-access bus clock, and write-cycle frequency are distinct.

## 6. Reuse SDK Layers

The public NXP example separates:

```text
Panel component
   -> Command writes
   -> Parameter writes
   -> Pixel-memory writes
            |
            v
FlexIO MCULCD + eDMA
```

Short commands and parameters can use blocking APIs while pixels use eDMA.

However, the example's pixel-write wrapper still waits for DMA:

> Using DMA does not prove that the upper-layer call is asynchronous.

Examples help explain API organization. Do not copy infinite waits and simplified error handling into a product.

The generic example's board list also does not establish support on every i.MX RT board. Verify the target SDK's board configuration and instance capabilities.

## 7. Keep Windows and Source Pixels Consistent

For a window at `(20, 30)` with size `100 × 40`, RGB565:

```text
Columns: 20 through 119
Rows: 30 through 69
Pixels: 100 × 40 = 4,000
Payload: 4,000 × 2 = 8,000 B
```

Steps remain:

1. Validate coordinates, visible-area offsets, and source range.
2. Acquire exclusive access for the complete display transaction.
3. Set column and row windows.
4. Begin pixel writing.
5. Transfer the actual length.
6. Confirm completion and return buffer ownership.

A region inside a full frame usually has a source stride. Sending its rectangle byte count consecutively can be wrong.

Send rows, pack the region, or use supported DMA descriptors. Verify continuation and CS boundaries for each method.

A wider interface does not automatically fix coordinates, stride, or byte counts.

## 8. Does DMA Completion End the Last WR Cycle?

Determine separately:

- When DMA stops reading the source.
- When the shifter emits the final data.
- When WR, CS, and RS can change.
- When another transaction can start.

The referenced MCULCD header explicitly documents end-of-transfer waiting. That implementation uses a software delay to let the final data leave the shifter; insufficient waiting can lose the last bytes.

Do not blindly shorten that delay or deassert CS merely because the DMA count reached zero.

For a truly asynchronous GUI port:

- Keep source pixels and active parameters valid.
- Make CPU writes visible to DMA along the actual memory path.
- Deliver completion to the correct owner.
- Report startup failures, timeouts, and aborts explicitly.
- Reuse only after all consumers release the buffer.

Double buffering helps through overlap, not premature completion.

## 9. Compare Parallel and SPI Budgets

Assume:

- 320 × 240.
- RGB565.
- One valid parallel write cycle per 100 ns.
- Single-line SPI at 40 MHz.
- No command, gap, rendering, setup, or scan-synchronization costs.

| Transport | Ideal pixel bandwidth | Full-screen payload time | 100 × 40 region time |
| --- | --- | --- | --- |
| Single-line SPI, 40 MHz | 5 MB/s | 30.72 ms | 1.60 ms |
| Eight-bit parallel, 100 ns/cycle | 10 MB/s | 15.36 ms | 0.80 ms |
| Sixteen-bit parallel, 100 ns/cycle | 20 MB/s | 7.68 ms | 0.40 ms |

The 100 ns cycle is an assumption, not a configuration supported by any arbitrary panel.

At the same cycle length, sixteen-bit RGB565 throughput is twice eight-bit throughput. Real proportional gains require measurements.

This offline script accesses no hardware:

```python
width, height = 320, 240
bytes_per_pixel = 2
frame_bytes = width * height * bytes_per_pixel
region_bytes = 100 * 40 * bytes_per_pixel
cycle_ns = 100

rates = [
    ("SPI 1-line 40 MHz", 40_000_000 / 8),
    ("DBI 8-bit", 1_000_000_000 / cycle_ns),
    ("DBI 16-bit", 2 * 1_000_000_000 / cycle_ns),
]

for label, rate in rates:
    frame_ms = frame_bytes / rate * 1000
    region_ms = region_bytes / rate * 1000
    print(
        f"{label}: {rate / 1_000_000:.2f} MB/s, "
        f"frame {frame_ms:.2f} ms, region {region_ms:.2f} ms"
    )
```

Output:

```text
SPI 1-line 40 MHz: 5.00 MB/s, frame 30.72 ms, region 1.60 ms
DBI 8-bit: 10.00 MB/s, frame 15.36 ms, region 0.80 ms
DBI 16-bit: 20.00 MB/s, frame 7.68 ms, region 0.40 ms
```

These are payload limits, not visible GUI frame rates.

## 10. Minimal Validation Sequence

| Stage | Test | Success criterion |
| --- | --- | --- |
| Interface | Commands, parameters, small pixel region | Correct CS, RS, WR ordering |
| Format | RGB, black/white, alternating pixels | Correct channels, widths, pixel order |
| Range | Corners, single rows, short final chunks | No offsets, overrun, or stale tail |
| Data path | Same blocking and DMA patterns | Identical output, no lost final data |
| Lifetime | Alternating distinct patterns | No overwrite or transaction interleaving |
| Load | Representative CPU/memory traffic | No errors; timing is explainable |

Record setup, pixel transfer, and full-update times separately, along with measured WR cycle, bytes, CPU cost, and buffer capacity.

TE needs scan/write verification. Fast transfer or starting on an edge alone does not prove freedom from tearing.

## 11. Common Problems

| Symptom | Initial checks |
| --- | --- |
| Commands appear valid but colors are wrong | Interface mode, format, data mapping |
| Repeating errors across pairs of pixels | DMA width, byte/halfword layout, packing |
| Last pixels missing | Shifter drain, premature CS/RS changes |
| Small windows work, large windows fail | DMA length, continuation, stride |
| Blocking works, DMA does not | Instance requests, DMAMUX, channel, reachability |
| Higher rates cause intermittent corruption | Cycle, setup/hold, waveform, signal integrity |
| CPU utilization remains high | Busy waits, conversion, region packing |

Restore the minimal correct path and add DMA, speed, and pipelining separately.

## 12. Summary

An 8080-style interface is more than extra data pins. It must satisfy panel timing while coordinating packing, FlexIO resources, and ownership.

- GRAM-based parallel displays still benefit from partial updates.
- Verify bus width, pixel format, and DMA width separately.
- DMA completion does not necessarily end the final strobe.
- Reuse SDK layers and provide product-level errors and timeouts.

Next: [RGB Displays: Pixel Clock and Continuous Scanout](06-rgb-display.md), moving from writes into retained images to continuous scanout from MCU frames.

## References

- [NXP FlexIO MCULCD driver](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/flexio/mculcd/fsl_flexio_mculcd.h)
- [NXP MCULCD eDMA interface](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/flexio/mculcd/fsl_flexio_mculcd_edma.h)
- [NXP MCULCD eDMA example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/flexio/mculcd/edma_transfer/flexio_mculcd_edma_transfer.c)

Fixed public revisions illustrate interfaces and flows. Target support, timing, and behavior must follow the actual SDK, device, and module.
