# Article 9: How Do LCDIF / eLCDIF Display Controllers Work?

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [A Reusable Display Bring-Up and Troubleshooting Process](08-display-bring-up.md)
>
> Next: [Why Does GUI Performance Depend on Memory?](10-memory-system.md)
>
> Goal: Follow memory reads, pixel interpretation, FIFO, and timing output, distinguishing address submission, events, and safe reuse.
>
> Scope: Public eLCDIF/LCDIFv2 drivers and examples, not one universal i.MX RT IP. Address and bandwidth examples are software models, not ready-to-use board layouts.

## 1. Scanout Is Not GUI Rendering

Applications choose content, CPU/PXP/GPU produce pixels, and display controllers output existing content.

A typical scanout path:

```text
Frame buffer
    |
    v
Read requests and bus access
    |
    v
Pixel-format interpretation
    |
    v
FIFO / supported layer composition
    |
    v
Pixel timing and output
    |
    v
RGB or downstream DSI
```

Composition, conversion, or LUT features do not make a controller understand widgets, layout, or events.

Scan-time composition also does not necessarily create a new composited image in memory.

## 2. Similar Names, Different Programming Models

| Reference path | Public interface characteristics | Not established |
| --- | --- | --- |
| eLCDIF RGB | Timing, format, frame and next-frame addresses | Arbitrary stride, layers, all formats |
| Optional eLCDIF extensions | Device-specific Alpha surface/LUT | Availability on every model |
| LCDIFv2 | Separate display/layer settings, layer stride, address, shadow load | Identical layers/operations for every SKU |
| DSI Host | Packetize and transport incoming pixels | Replace scanout memory reads |

Hardware called LCDIF may use an eLCDIF driver. One chip can also contain different controller versions.

Identify:

- Exact device and core.
- Instance and register definitions.
- Driver variant.
- Output route and board video mux.
- SDK capability conditions.

Finding the word LCDIF is not enough to mix APIs.

## 3. How an Address Becomes a Pixel Row

For the ordinary RGB565 model:

```text
pixel_address(x, y) = base + y × stride + x × 2
```

The controller also needs dimensions, format, and output bounds.

| Parameter | Effect |
| --- | --- |
| Base | Read starting point |
| Format | Bit/byte interpretation |
| Active size | Required pixels and lines |
| Stride | Next row, if configurable in this mode |
| Alignment | Valid access and interface requirements |
| Reachability | Whether the controller can access RAM |

A valid software pointer does not prove identical device addressing. Reuse SDK CPU-to-IP translation where required.

Do not copy PC address models or another MCU's RAM base into an embedded design.

## 4. Source Versus Output Format

The public eLCDIF interface lists RGB565, packed RGB888, and XRGB8888 sources while independently configuring the output bus.

Memory differs:

| Source | Capacity model |
| --- | --- |
| RGB565 | 2 B/pixel |
| Packed RGB888 | 3 B/pixel |
| XRGB8888 | 4 B/pixel; upper field is not meaningful Alpha |

Conversion and mapping depend on the controller path.

Another API named RGB888 may mean a 32-bit container. Matching names do not prove matching layouts.

Use colors, intensity steps, and positional patterns to check source, interpretation, and output together.

## 5. FIFOs Absorb Latency, Not Create Bandwidth

Controllers read batches and consume pixels at fixed timing:

```text
Burst reads -> FIFO -> Timed pixel consumption
```

Memory need not deliver every pixel exactly on a PCLK edge, but it must refill promptly.

CPU, PXP, GPU, DMA, and other traffic can cause:

- Insufficient average bandwidth.
- Excessive latency during certain intervals.
- Invalid addresses or permissions.
- Mismatched input/output timing.

Public eLCDIF/LCDIFv2 APIs distinguish underrun, FIFO, bus, and layer-DMA states. Record the actual flags, not a generic "image error."

Changing priorities or FIFO behavior can alter symptoms, but does not replace capacity, reachability, and sustained-load validation.

## 6. From Next-Frame Submission to Scanout

### 6.1 eLCDIF

`ELCDIF_SetNextBufferAddr()` sets a next-frame address; it does not copy an image immediately.

Before submitting, establish complete, reachable, visible data that no other producer is modifying.

### 6.2 LCDIFv2

Layer-address updates and shadow loading are separate:

```text
Update layer-buffer settings
             |
             v
Request shadow load
             |
             v
Apply active settings at the specified boundary
```

The referenced driver documents activation of shadow control registers on the next frame's VSYNC.

An API return, arbitrary interrupt, or arbitrary register observation does not automatically prove activation.

### 6.3 Do Not Mix the Mechanisms

eLCDIF next-address registers and LCDIFv2 per-layer shadows are different programming models.

Do not copy another controller's initialization, event checks, and release ordering unchanged.

## 7. A Two-Frame Ownership Model

Assume A is scanned while B is available:

```text
A: SCANNING
B: FREE -> DRAWING -> READY -> PENDING

Confirm B activates through the target mechanism
and A is no longer accessed by relevant readers:

B: SCANNING
A: FREE
```

This describes software responsibilities. The controller manual, driver, and port define actual confirmation.

Common traps:

- Overwrite A immediately after submitting B.
- Treat any VSYNC as proof that B activated.
- Miss a boundary but release the old frame early.
- Clear a wait flag after submission and lose an event.
- Overwrite one pending state with several requests.

Use one explicit owner for sequence numbers, current/pending frames, and release conditions.

Avoid inconsistent copies of state in interrupts, GUI tasks, and application tasks.

## 8. What Interrupts Tell You

| Event | Evidence | Not automatically |
| --- | --- | --- |
| VSYNC edge | A synchronization instant | Every new setting applied |
| Vertical blanking entry | Scanout reached that phase | Panel response finished |
| Layer read/DMA event | A memory-access milestone | Entire image visible |
| FIFO underrun | Supply/timing failure | Normal completion |
| Bus/layer-DMA error | Address, permission, access failure | All buffers safe to reuse |

The referenced eLCDIF driver defines `CurFrameDone` as entry into vertical blanking. LCDIFv2 also separates blanking and VSYNC events.

"Done" in a name does not replace semantic analysis.

General ISR practice:

1. Snapshot relevant status.
2. Separate normal and error events.
3. Acknowledge with SDK semantics.
4. Update synchronized state or notify the owner.
5. Handle expensive work/recovery in task context.

Printing, critical sections, and notifications affect timing and must follow the RTOS rules.

## 9. Layer Composition Is Not Free Rendering

Supported LCDIFv2 paths can read and blend several layers.

| Method | Where work occurs | Main cost |
| --- | --- | --- |
| CPU/PXP/GPU precomposition | Generate a stored result before scanout | Source reads, destination writes, synchronization |
| Controller scan-time composition | Read/blend layers during scanout | Repeated layer reads |

Assume:

- Main layer: 800 × 480, RGB565, 60 Hz.
- Overlay: 200 × 100, ARGB8888, 60 Hz.
- Reads cover each active layer region; extra transactions excluded.

Active traffic:

```text
Main: 800 × 480 × 2 × 60 = 46.08 MB/s
Overlay: 200 × 100 × 4 × 60 = 4.80 MB/s
Total: 50.88 MB/s
```

Layers can avoid some precomposition work but still consume read bandwidth.

Verify counts, formats, Alpha, activation, and clipping on the actual IP. A generic driver's enum count is not a capability guarantee for all chips.

## 10. Check Frame Layout Offline

Assume RGB565 with 1,600 B stride and the example's chosen 64 B start alignment.

`0x80000000` is arithmetic only, not a board-address recommendation.

```python
width, height = 800, 480
bytes_per_pixel = 2
stride = 1600
alignment = 64
base = 0x80000000

if stride < width * bytes_per_pixel or base % alignment:
    raise ValueError("The assumed frame layout is invalid.")

frame_bytes = stride * height
allocation_step = ((frame_bytes + alignment - 1) // alignment) * alignment
second_base = base + allocation_step
last_pixel = base + (height - 1) * stride + (width - 1) * bytes_per_pixel
region_pixel = base + 30 * stride + 20 * bytes_per_pixel

print(f"Frame bytes: {frame_bytes:,}")
print(f"Buffer A: 0x{base:08X}")
print(f"Buffer B: 0x{second_base:08X}")
print(f"Last pixel in A: 0x{last_pixel:08X}")
print(f"Pixel (20, 30): 0x{region_pixel:08X}")
```

Output:

```text
Frame bytes: 768,000
Buffer A: 0x80000000
Buffer B: 0x800BB800
Last pixel in A: 0x800BB7FE
Pixel (20, 30): 0x8000BBA8
```

The last pixel's address still needs its complete two bytes. It is not the allocation's end boundary.

Physical capacity, linker layout, IP mapping, and alignment still require board checks.

## 11. Read Examples by Responsibility

The public examples illustrate:

- eLCDIF RGB: Frame generation, next address, frame events.
- LCDIFv2 RGB565: Layers, addresses, shadow loading.
- RT1170 board support: Memory, clocks, panel, DSI routing.

Find:

1. Buffer allocation.
2. Cache attributes.
3. Content generation.
4. Submission API.
5. Completion/wait event.
6. Simplifications in errors, timeouts, and concurrency.

Do not copy demonstration busy waits as a multitasking architecture or assume its event handling covers every submission instant.

## 12. Three Validations Matter More Than One FPS

| Validation | Method | Conclusion |
| --- | --- | --- |
| Fixed scanout | Known complete frame and timing | Basic reads, format, output |
| Alternating submission | Distinct frames, sequences, address events | Reliable activation and release |
| Combined load | Rendering, assets, other bus masters | Stable bandwidth/synchronization |

Record actual PCLK, event rates, errors, submission waits, and CPU cost.

Sixty-hertz scanout does not prove 60 distinct GUI images per second. Interrupt frequency does not establish visible updates.

## 13. Summary

A controller connects two cadences:

- Memory delivers bursts with variable latency.
- The panel consumes pixels at fixed timing.

Understand layout, format, FIFO, events, and update mechanisms together.

A next-frame address expresses intent. An event provides phase evidence. Old-buffer reuse requires the complete ownership contract.

Next: [Why Does GUI Performance Depend on Memory?](10-memory-system.md), examining RAM, external storage, resource layout, and contention.

## References

- [NXP eLCDIF interface](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/elcdif/fsl_elcdif.h)
- [NXP eLCDIF RGB initialization](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/elcdif/fsl_elcdif.c)
- [NXP LCDIFv2 interface](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/lcdifv2/fsl_lcdifv2.h)
- [NXP eLCDIF RGB example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/elcdif/rgb/elcdif_rgb.c)
- [NXP LCDIFv2 RGB565 example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/lcdifv2/rgb565/lcdifv2_rgb565.c)

Fixed public commits document particular interfaces. Final capabilities and events must follow the target manual, errata, and SDK.
