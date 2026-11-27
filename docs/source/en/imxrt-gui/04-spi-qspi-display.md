# Article 4: SPI / QSPI Displays: From Commands to Partial Updates

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [Budget Resolution, Display Memory, and Bandwidth Before Choosing a Screen](03-memory-and-bandwidth.md)
>
> Next: [8080 / DBI Parallel Displays with FlexIO and Other Resources](05-flexio-dbi-display.md)
>
> Goal: Understand command and pixel transfers to serial displays with GRAM, then establish correct region updates, DMA, and asynchronous buffer handoffs.
>
> Assumptions: A common four-wire SPI model with eight-bit commands and RGB565 window writes. Examples use the common `0x2A / 0x2B / 0x2C` meanings, not universal panel initialization. The QSPI discussion explains compatibility checks, not a preselected MCU/panel combination.
>
> Validation boundary: This article provides protocol examples, an executable offline byte-order script, and board-test methods. It does not claim board execution or publish unmeasured board performance.

## 1. Serial Displays Offer More Than Fewer Pins

[Article 3](03-memory-and-bandwidth.md) showed the full-screen throughput limits of single-line SPI.

That does not make SPI unsuitable for a GUI.

Numeric fields, menus, and status pages may leave most pixels unchanged. A serial display with GRAM can retain the full image while the MCU updates only changed regions.

Typical path:

```text
CPU / GUI rendering
         |
         v
Partial pixel buffer
         |
         v
SPI / QSPI transfer
         |
         v
Display controller and GRAM
         |
         v
Panel scanout
```

This separates generation of new pixels from repeated scanning of existing pixels.

The MCU need not always retain a complete frame or transfer one each scan cycle.

The main questions are:

1. How are commands distinguished from data?
2. Where should the pixels be written?
3. Are format, order, and count correct?
4. When can the source buffer be reused?

## 2. Identify the Actual SPI Display Mode

"SPI" on a product listing is not sufficient specification.

Verify:

- Display-controller model and module revision.
- Actual interface mode.
- Word size, clock mode, and permitted rate.
- Logical resolution, GRAM dimensions, visible-area offset.
- Pixel formats.
- Command/data indication.
- Reset, backlight, and TE signals.

### 2.1 Common Four-Wire SPI

A common connection includes:

| Signal | Purpose |
| --- | --- |
| SCLK | Serial clock |
| MOSI / SDI | MCU output for commands, parameters, pixels |
| CS | Chip select and transaction boundaries |
| D/C | Command/data distinction |
| RESET | Controller reset |
| BL | Backlight control, potentially through a driver circuit |
| MISO / SDO | Optional read path, not always exposed |
| TE | Optional scan synchronization output |

"Four-wire SPI" often counts clock, data, CS, and D/C, but vendors use different conventions. It does not establish that the module needs only four physical connections.

A common D/C convention is low for commands and high for parameters or pixels. Verify the actual controller and module.

Having both MISO and MOSI does not double write throughput. Pixel writes use the actual output path.

### 2.2 Three-Wire or Command-Bit Modes

Some modes add a command/data bit to each transfer word, for example a nine-bit word.

Check:

- Controller support for the required word length.
- DMA word layout.
- Throughput cost of the additional bit.
- Driver transaction handling.

Do not reuse an eight-bit four-wire byte-stream driver unchanged.

### 2.3 Multi-Line QSPI

QSPI typically enables multiple lines during pixel data, but transaction details vary.

Commands, addresses, parameters, and pixels may use different widths, headers, or transitions.

The matching process is examined later.

## 3. Three Software Layers

Do not put panel registers, SPI operations, and LVGL callbacks into one function.

Reuse the SDK's existing layering where possible:

| Layer | Responsibility | Not its responsibility |
| --- | --- | --- |
| Board initialization | Power, pins, clocks, reset, backlight | Widgets and invalidated regions |
| Panel driver | Initialization, orientation, format, windows | Framework-specific object structures |
| Transfer interface | Commands/data, DMA, completion, errors | Page content |

The GUI port sits above them, submitting regions and pixels.

NXP public display components demonstrate commands, data, and memory writes through a DBI interface. Check these existing components before introducing a duplicate driver for an article.

A component does not establish board compatibility. SDK version, interface implementation, and module initialization still need verification.

## 4. Initialization: Put the Controller in the Right State

A typical sequence is:

1. Check power and logic levels.
2. Initialize MCU pins and the transfer peripheral.
3. Reset according to module requirements.
4. Send the module-specific initialization sequence.
5. Configure format, orientation, and visible area.
6. Wait for required state transitions.
7. Enable display output and control the backlight appropriately.

Commands may configure sleep exit, display enable, scan direction, Gamma, and power.

These parameters are not universal constants.

Even two modules with the same controller may need different settings because their panels, supplies, and visible regions differ.

This article therefore does not offer a universal initialization array. Start with:

- Module-vendor initialization instructions.
- Controller documentation.
- SDK examples for the same module.

Validate at a conservative, documented clock first. Another board's successful overclock is not a design specification.

## 5. Address Windows: Where Do the Pixels Go?

Many common controllers use:

| Command | Common meaning |
| --- | --- |
| `0x2A` | Column address range |
| `0x2B` | Row address range |
| `0x2C` | Begin pixel-memory write |

This example assumes:

- Inclusive start and end coordinates.
- Sixteen-bit coordinate parameters, high byte first.
- Two bytes per RGB565 pixel.

Verify all three on the target controller.

### 5.1 A Specific Region

Assume a logical 320 × 240 display, correctly configured orientation, and no extra GRAM offset.

Update:

```text
x = 20
y = 30
width = 100
height = 40
```

Then:

```text
x_start = 20
x_end = 20 + 100 - 1 = 119
y_start = 30
y_end = 30 + 40 - 1 = 69
```

Transaction contents:

```text
D/C = command: 2A
D/C = data:    00 14 00 77

D/C = command: 2B
D/C = data:    00 1E 00 45

D/C = command: 2C
D/C = data:    Following pixel byte stream
```

Pixel count and bytes:

```text
100 × 40 = 4,000 pixel
4,000 × 2 = 8,000 B
```

This describes contents only. CS continuity, D/C transitions, and allowed transaction splits depend on the panel and MCU.

### 5.2 Common Boundary Errors

| Error | Consequence |
| --- | --- |
| End coordinate is `x + width` | One extra column |
| Transfer length uses pixels rather than bytes | Potentially half the RGB565 data |
| Visible-area offset ignored | Entire image shifted |
| Original mapping used after rotation | Incorrect direction, bounds, or scan order |
| Window clipped without adjusting the source | Destination and source no longer correspond |

Do not silently return on invalid regions.

Use the project's error channel to report requested bounds, display bounds, and source-buffer conditions, then let the upper layer handle failure.

## 6. RGB565 Can Still Have Different Byte Order

RGB565 red can be represented as:

```text
0xF800
```

In ordinary little-endian CPU memory, its bytes are typically:

```text
00 F8
```

If the panel expects the high byte first, the link must carry:

```text
F8 00
```

The value describes the same pixel, but direct byte transmission may be wrong.

### 6.1 Three Different Ordering Problems

1. **RGB / BGR:** Red/blue mapping.
2. **Pixel byte order:** High/low byte order within a sixteen-bit pixel.
3. **Word bit order:** MSB-first versus LSB-first SPI shifting.

MSB-first SPI does not automatically fix little-endian sixteen-bit arrays sent through eight-bit DMA.

Check SPI word size, DMA access width, and how the driver reads memory.

### 6.2 Possible Solutions

- Use supported sixteen-bit hardware/driver transmission behavior.
- Reorder bytes in a separate transfer buffer.
- Use version-appropriate GUI byte-swap helpers only when mode and lifetimes permit.

Do not blindly swap a persistent frame buffer in place.

Later rendering may still expect native pixel format, causing corruption or repeated swaps.

A separate transfer buffer preserves the source format, but adds capacity, conversion work, and memory traffic.

### 6.3 Minimal Color Checks

Under this example's high-byte-first assumption:

| Color | RGB565 value | Link bytes |
| --- | --- | --- |
| Red | `0xF800` | `F8 00` |
| Green | `0x07E0` | `07 E0` |
| Blue | `0x001F` | `00 1F` |
| White | `0xFFFF` | `FF FF` |
| Black | `0x0000` | `00 00` |

Include color and positional patterns, not just black and white. Black and white survive byte swapping unchanged and cannot expose the issue reliably.

## 7. Region Pixels May Not Be Contiguous

Suppose the full source is 320 pixels wide, RGB565, with a 640-byte stride.

A 100-pixel region requires only 200 bytes from each row.

Its next row begins at the same x coordinate on the next source line, not immediately after those 200 bytes:

```text
source_row(y) = source_base + y × source_stride + x × 2
```

Sending `100 × 40 × 2` consecutive bytes from the starting address would include unwanted pixels to the right.

Options:

1. The GUI provides a tightly packed partial buffer.
2. Send the region row by row.
3. Pack rows into a contiguous transfer buffer.
4. Use supported scatter/gather or related hardware features.

Each has costs:

- Row transfers can add transaction and scheduling gaps.
- Packing adds traffic and buffer capacity.
- Advanced descriptors impose hardware constraints.

When splitting one window into multiple transfers, verify continuation, CS behavior, and any required continue-write command.

Do not assume the next DMA continues the previous GRAM position.

## 8. Establish a Blocking Baseline Before DMA

Begin with a simple synchronous path:

```text
Validate region and source
           |
           v
Acquire exclusive display / bus access
           |
           v
Set column window and check result
           |
           v
Set row window and check result
           |
           v
Begin pixel write and check result
           |
           v
Send the correct pixel byte count
           |
           v
Confirm hardware-defined transaction completion
           |
           v
Release access and report the result
```

Any failure enters explicit cleanup:

- Stop submitting pixels.
- Terminate or recover the transaction according to the interface.
- Record the error and state.
- Confirm consumers have released the source.
- Release resources and report failure.

Do not keep writing pixels after a command failure.

The baseline is for observable correctness, not maximum speed.

Validate:

- Solid colors.
- Color bars.
- Corner markers.
- A specified window.
- Unchanged content outside that window.

Only then replace pixel transfer with DMA.

## 9. An Offline Window-Write Example

This standard-library Python script generates example command contents and RGB565 bytes.

It does not access SPI or simulate completion.

```python
screen_width, screen_height = 320, 240
x, y, width, height = 20, 30, 100, 40

if not (
    width > 0
    and height > 0
    and 0 <= x <= screen_width - width
    and 0 <= y <= screen_height - height
):
    raise ValueError("The requested rectangle is outside the logical display.")

column_command = b"\x2a" + x.to_bytes(2, "big")
column_command += (x + width - 1).to_bytes(2, "big")
row_command = b"\x2b" + y.to_bytes(2, "big")
row_command += (y + height - 1).to_bytes(2, "big")

red_pixel = (0xF800).to_bytes(2, "big")
pixel_payload = red_pixel * (width * height)

print("Column:", column_command.hex(" ").upper())
print("Row:", row_command.hex(" ").upper())
print("Memory write: 2C")
print(f"Pixel payload: {len(pixel_payload):,} B")
print("First two pixels:", pixel_payload[:4].hex(" ").upper())
```

Output:

```text
Column: 2A 00 14 00 77
Row: 2B 00 1E 00 45
Memory write: 2C
Pixel payload: 8,000 B
First two pixels: F8 00 F8 00
```

On hardware, send command bytes and parameters with the required D/C distinction, then send pixels.

Concatenation here expresses logical contents. It does not mean the array can be transmitted to a four-wire panel with D/C fixed for the entire array.

## 10. DMA Benefits and Boundaries

DMA moves source-memory data into SPI transmission:

```text
RAM -> DMA -> SPI FIFO / shift register -> Display
```

Benefits:

- Less CPU copying.
- Fewer software-induced gaps.
- Possible overlap with rendering.

DMA does not turn a single-line link into a four-line link or exceed panel timing limits.

### 10.1 Checks Before Starting DMA

| Item | Check |
| --- | --- |
| Address | DMA reachability of source RAM |
| Length | Bytes, words, or another driver unit |
| Width | DMA access width versus SPI word width |
| Format | Correct pixel byte order |
| Alignment | Address, length, hardware restrictions |
| Cache | CPU writes visible to DMA |
| Lifetime | Source remains valid and unchanged |
| Bus | Commands, window, and pixels remain controlled together |

CPU-generated data in cached memory may require Clean before non-coherent DMA reads, using the target SDK and cache-line rules.

Disabling cache is not automatically the final solution. Avoid maintaining cache lines containing unrelated data without analysis.

The later cache article covers those details.

### 10.2 DMA Completion Versus SPI Completion

DMA completion may mean data has reached the peripheral while the FIFO or shift register is still transmitting.

Determine separately:

- When DMA stops reading source memory.
- When D/C or CS can change.
- When another transaction may begin.
- When the driver should report completion.

The buffer may become available before the bus, but the driver needs an explicit contract. An initial implementation can perform unified cleanup after confirmed transaction completion.

Every wait needs project-standard timeout and error handling; one failure must not block the GUI indefinitely.

## 11. Asynchronous Transfers Are About Ownership

An asynchronous call generally reports submission, not completed transfer.

This sequence is incorrect:

```text
Start DMA
    -> Immediately report GUI flush completion
    -> GUI overwrites the same buffer
    -> DMA reads the overwritten data
```

It can produce random colors, old/new mixtures, or intermittent regional corruption.

### 11.1 Buffer States

```text
FREE
  |
  v
DRAWING
  |
  v
READY
  |
  v
TRANSFERRING
  |
  v
Confirm all relevant consumers have released it
  |
  v
FREE
```

Each transition needs a clear owner and event.

While transferring:

- Do not overwrite pixels.
- Do not free the source.
- Do not modify active asynchronous descriptors or parameters.
- Do not submit commands that change the active window.

Asynchronously sent command parameters also need sufficient lifetime. Protecting only the pixel array while using expired stack parameters is insufficient.

### 11.2 Lock the Whole Display Transaction

For shared resources, serialize:

```text
Set window -> Begin pixel write -> Finish pixel transaction
```

Do not release access immediately after setting the window, allowing another task to change it before pixels are sent.

Interleaving another device between chunks depends on panel protocol, CS rules, and driver design. It must not be assumed.

### 11.3 Errors Must Also Complete the Lifetime

On startup failure, timeout, or peripheral error:

1. Record failure and stop new submissions.
2. Abort through the driver.
3. Confirm DMA and related hardware no longer access the source.
4. Release or reset resources under the port contract.
5. Report failure and recover through reinitialization or redraw.

Do not mark a buffer reusable until abort completion is confirmed.

Do not announce "display success" merely to prevent GUI blocking.

LVGL completion represents a buffer handoff, not proof of correct visibility. Preserve errors through a separate explicit channel.

## 12. Pipelining with Two Small Buffers

For 320-pixel-wide, 40-line RGB565 buffers:

```text
One buffer: 320 × 40 × 2 = 25,600 B = 25 KiB
Two buffers: 50 KiB
```

Possible sequence:

```text
Time ->

CPU: Draw A | Draw B      | Wait / draw A | Draw B ...
SPI:        | Transfer A  | Transfer B    | Transfer A ...
```

Requirements:

- SPI truly runs in the background.
- Drawing does not disturb the active transfer buffer.
- Commands and pixels retain ordering.
- Transfer completion returns ownership.
- Queueing and task behavior do not reintroduce busy waiting.

These are partial draw/transfer buffers, not complete display frames.

They improve throughput and CPU availability, but do not automatically eliminate GRAM scanout tearing.

### 12.1 Buffer Size Trade-Offs

Too small:

- Frequent window setup and transfer launches.
- Greater fixed overhead.
- Greater sensitivity to scheduling gaps.

Too large:

- Higher RAM use.
- Longer buffer release times.
- No guaranteed improvement in stage overlap.

Measure end-to-end results across sizes. A fraction such as one tenth of a screen or a fixed line count is not universally optimal.

### 12.2 Correct Chunking

Setting an independent window for each chunk is easy to validate.

To set one full-screen window and send many chunks, verify continuation and CS behavior.

For a final short chunk, send its actual height and byte count, not the unused remainder of the allocation.

## 13. Transfer Only Changed Regions

For a 320 × 240 RGB565 display, a full screen contains 153,600 B. The example 100 × 40 region contains 8,000 B.

Pixel-volume reduction:

```text
153,600 / 8,000 = 19.2 times
```

At an assumed single-line 40 MHz, excluding commands and gaps:

| Area | Pixel bytes | Ideal payload time |
| --- | --- | --- |
| Full 320 × 240 | 153,600 B | 30.72 ms |
| Region 100 × 40 | 8,000 B | 1.60 ms |

At 60 updates/s for the region:

```text
8,000 × 60 = 480,000 B/s = 0.48 MB/s
```

The same SPI link therefore faces very different workloads for regional updates and full-screen animation.

Do not turn the 19.2-fold pixel reduction into a claimed 19.2-fold FPS gain. Rendering, fixed overhead, scanout, and other tasks remain.

### 13.1 Should Small Regions Be Merged?

Separate regions cost more transactions. A merged bounding rectangle can contain extra pixels.

A simple model:

```text
Separate time ≈ sum(S_i) / B + n × T_setup
Merged time ≈ S_bbox / B + T_setup
```

Where:

- `S_i`: Each region's pixel bytes.
- `S_bbox`: Bounding-rectangle pixel bytes.
- `B`: Effective pixel throughput.
- `T_setup`: Fixed setup time.

Merging may help only if extra pixel time is less than saved setup time.

Do not automatically merge distant numeric fields into one large rectangle.

Moving objects require their old areas to be redrawn; shadows and antialiasing can expand invalidation. Inspect actual framework output, not nominal object dimensions.

## 14. TE Helps, but Does Not Guarantee No Tearing

A display can scan GRAM while the MCU updates it, producing mixed old/new content.

Some controllers provide TE signals for scan events.

Check:

- TE meaning and mode.
- Scan direction versus write direction.
- Position of the update region within scanout.
- Available write time versus transfer time.
- Other buffering or synchronization mechanisms.

The example complete 320 × 240 RGB565 transfer at single-line 40 MHz takes 30.72 ms for pixels alone.

A 60 Hz scan cycle is approximately 16.67 ms. Starting at a TE edge does not prove the entire update fits a safe scan window.

Analyze scan/write timing rather than only checking that a TE pin is connected.

## 15. QSPI: Match Transactions Before Expecting Four Times the Throughput

Four-line pixel data can increase same-clock throughput.

Compatibility comes from transaction details, not matching interface names.

### 15.1 Write Down the Panel Transaction

| Phase | Conditions to verify |
| --- | --- |
| Instruction | Opcode, length, width |
| Address / control | Meaning, length, order, width |
| Parameters | Byte count, width, continuity |
| Transition | Width changes, direction changes, wait cycles |
| Pixels | Format, width, length, order |
| End | CS, idle gap, completion definition |

Some documents use notation such as `1-1-4` for instruction/address/data widths. Verify the panel's notation and semantics rather than copying SPI NOR assumptions.

A display address may come from a window command, control field, or encapsulated protocol instead of linear memory addressing.

### 15.2 MCU Transaction Requirements

For the candidate i.MX RT peripheral, check:

- Width and bit count in each phase.
- Required command/wait/data combinations.
- CS and phase boundaries.
- Suitable indirect or other pixel-transfer operations.
- DMA, FIFO, and length limits.
- Existing SDK protocol support.

Some FlexSPI implementations offer configurable transactions. Suitability still depends on the specific controller, panel protocol, and driver.

Pretending the panel is ordinary NOR Flash does not establish correct mapping, operations, or timing.

### 15.3 Sharing a Controller with XIP or Resource Flash

Also check:

- Contention with instruction fetches and asset reads.
- Whether active Flash read sequences are modified.
- Busy-state effects on other accesses.
- Independent CS, pins, and clock settings.
- Explicit SDK support for the shared configuration.

Do not modify an active XIP read sequence or clock and assume that display and code execution are unaffected.

Prefer an existing supported configuration; otherwise validate sharing separately.

### 15.4 A Payload-Only Estimate

Assume four-line, single-edge pixel transfer at 40 MHz:

```text
Ideal bandwidth = 40,000,000 × 4 / 8 = 20 MB/s
320 × 240 RGB565 time = 153,600 / 20,000,000 = 7.68 ms
```

Payload throughput is approximately 130.21 transfers/s, not a guarantee that the panel or GUI displays 130.21 distinct complete images.

At 800 × 480, payload time is still 38.4 ms.

More lines improve bandwidth but do not solve every resolution and update target.

## 16. Aligning the LVGL Port

Later articles cover APIs in detail. First establish the handoff:

```text
LVGL provides a region and pixels
               |
               v
Port verifies layout and format
               |
               v
Panel layer sets the window
               |
               v
Transfer layer sends pixels
               |
               v
Complete or handle failure according to real state
               |
               v
Return buffer ownership to LVGL
```

In LVGL 9.2, `flush_cb` receives the update and `lv_display_flush_ready()` signals the handoff.

Do not call completion immediately after DMA startup.

Verify:

- Whether the render mode supplies tightly packed partial pixels.
- Actual source stride.
- Rotation and GRAM offsets.
- Pixel format and byte order.
- Completion threading and synchronization.
- Error recovery and redraw.

A manageable design uses a display-owning task for state-machine cleanup, while interrupts provide only port-approved notifications. Do not put arbitrary GUI operations in interrupt handlers.

## 17. Board Validation Sequence

### 17.1 Correctness

| Test | What to verify |
| --- | --- |
| Black, white, red, green, blue | Format, channels, byte order |
| Bars and checkerboard | Continuity and pixel layout |
| Corner markers | Direction, offset, bounds |
| 100 × 40 window | Endpoints, length, mapping |
| Non-full-height final chunk | Tail length and boundaries |
| Strided source region | Row handling |
| Continuous asynchronous updates | Lifetimes and event ordering |
| Simulated failure/timeout | Abort, release, recovery |

Use successive, clearly different patterns to expose premature overwrite.

### 17.2 Performance Records

| Mode | Area | Transfer | Status |
| --- | --- | --- | --- |
| Baseline | Full screen | Blocking | Not measured |
| Comparison | Full screen | DMA | Not measured |
| Partial | 100 × 40 | DMA | Not measured |
| Chunked | Full screen, varied heights | Double-buffer DMA | Not measured |
| QSPI [when compatible] | Equivalent area | Verified four-line protocol | Not measured |

Record at least:

- Chip, board, panel, SDK, and driver.
- Measured SCLK, pixel format, effective byte count.
- Command/setup time.
- Pixel-transfer time.
- Complete-update time.
- CPU utilization and buffer capacity.
- Tearing and transfer errors.

Compare using:

```text
Effective pixel throughput = Effective pixel bytes / Measurement time
```

State whether timing includes window setup, waiting, and cache maintenance.

Use GPIO or a logic analyzer to distinguish source-read completion from actual bus completion. Measuring only submission is insufficient.

## 18. Troubleshooting

| Symptom | Initial checks |
| --- | --- |
| Backlight but no image | Power, reset, initialization, D/C, CS, clock, data |
| Red/blue swapped | RGB/BGR and channel mapping |
| Incorrect colors | Byte order, word width, pixel format |
| Shifted image | Visible region, GRAM offset, orientation |
| Row misalignment | Window width, stride, byte count |
| Blocking works, DMA fails | Reachability, cache, width, length, lifetime |
| Intermittent old/new mixtures | Premature overwrite, interleaved transactions |
| Small regions work, full screen is slow | Throughput, volume, chunk gaps |
| Tearing despite TE | TE meaning, scan/write timing, duration |
| QSPI gives no improvement | Actual four-line data, overhead, software gaps |

These are hypotheses to investigate, not automatic diagnoses.

Return to the minimal correct baseline, then reintroduce DMA, double buffering, higher clocks, and GUI integration one at a time.

## 19. Summary: Send Less, Send Correctly, and Hand Off Safely

For serial GRAM displays:

1. **Send less:** Update only necessary pixels.
2. **Send correctly:** Match windows, coordinates, format, byte order, stride, and count.
3. **Hand off safely:** Agree on lifetimes among DMA, SPI, and the GUI.
4. **Match before accelerating:** QSPI benefits depend on protocol and transaction compatibility.

Only then do DMA and double buffering provide reliable performance benefits.

Next: [8080 / DBI Parallel Displays with FlexIO and Other Resources](05-flexio-dbi-display.md), applying the same region-update ideas to parallel timing, pins, and DMA.

## References

- [NXP public ILI9341 component](https://github.com/nxp-mcuxpresso/mcux-component/blob/d22e3898220769f82d177d8c036e003be8efbad1/display/ili9341/fsl_ili9341.c)
- [NXP public ST7796S component](https://github.com/nxp-mcuxpresso/mcux-component/blob/d22e3898220769f82d177d8c036e003be8efbad1/display/st7796s/fsl_st7796s.c)
- [LVGL 9.2 display interface](https://docs.lvgl.io/9.2/porting/display.html)
- [NXP RT1060 product entry point](https://www.nxp.com/products/i.MX-RT1060)

The public components support command and layering checks, not a claim that this article has adopted a particular module's initialization. Actual opcodes, delays, formats, and CS rules must follow the controller and module.
