# Article 8: A Reusable Display Bring-Up and Troubleshooting Process

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [MIPI DSI Displays: The High-Speed Serial Link](07-mipi-dsi-display.md)
>
> Next: [How Do LCDIF / eLCDIF Display Controllers Work?](09-lcdif-elcdif.md)
>
> Goal: Establish a hardware-to-GUI validation sequence for black screens, color errors, offsets, corruption, and tearing.
>
> Validation boundary: Checklists, patterns, and hypothetical fault investigations, not claims that a particular board has passed. Electrical/timing requirements remain device-, board-, and panel-specific.

## 1. Do Not Start by Replacing the Initialization Array

A blank display often prompts immediate changes to initialization, pixel clock, or cache.

These changes can affect symptoms without revealing the cause. Multiple changes can also destroy useful evidence.

Describe "black screen" precisely:

- Is the backlight on?
- Is there no valid output, or a valid all-black image?
- Does cold boot fail while reset succeeds?
- Is the fault intermittent?
- Do fixed patterns work while animation fails?
- What are the CPU, transfer peripheral, and panel states?

Precise symptoms make the next step evidence-driven.

## 2. Fix the Experimental Conditions

Record:

| Category | Minimum information |
| --- | --- |
| Hardware | Complete device, board revision, module/controller |
| Connections | Mode, connector, power, reset, backlight, touch |
| Software | SDK, driver, compiler, optimization |
| Clocks | Actual CPU, memory, interface, display values |
| Pixels | Resolution, format, stride, byte order, orientation, offset |
| Memory | Address, capacity, reachability, alignment, cache/MPU |
| Updates | Buffers, areas, transfer method, completion |
| Reproduction | Scene, sequence, success/failure counts |

Keep both successful and failed conditions to identify meaningful differences.

Logs need not contain credentials or unrelated sensitive information. Record only display-relevant configuration and state.

## 3. Seven Validation Gates

```text
1. Documentation and connections
               |
               v
2. Power, reset, backlight
               |
               v
3. Peripherals, clocks, interface state
               |
               v
4. Initialization or scan timing
               |
               v
5. Pixels and memory path
               |
               v
6. Completion and buffer synchronization
               |
               v
7. GUI, input, combined load
```

This reduces unknowns; it is not a universal register initialization order.

Mark unverified stages explicitly. Downloading an example does not establish that every layer works.

## 4. Documentation, Power, and Wiring

### 4.1 Documentation and Connections

Check the module interface, not only the controller name.

Controllers can support multiple modes selected by module straps, while similarly named connectors can have different pinouts.

Verify levels, IOMUX, and board jumpers to separate wiring from software problems.

### 4.2 Power and Reset

Check:

- Module and logic rails within limits.
- Supply order and settling.
- Reset polarity, duration, release timing.
- Backlight operation independent of display initialization.

A lit backlight establishes only that path, not controller initialization.

Connect, disconnect, and measure according to board/panel instructions. Temporary shorts and out-of-spec operation are not substitutes for validation.

## 5. Collect Interface-Specific Evidence

| Interface | Observe first | Verify next |
| --- | --- | --- |
| SPI / QSPI | CS, clock, command/data, width | Window, byte order, length, boundaries |
| 8080-style | CS, RS, WR/RD, bus | Setup/hold, cycle, width, final transfer |
| RGB | PCLK, DE, HSYNC, VSYNC | Timing, active data, memory reads |
| MIPI DSI | Power/reset, Host/PHY, commands | Routing, format, packets, HS |

The relevant interface articles are:

- [SPI / QSPI](04-spi-qspi-display.md)
- [8080 / DBI](05-flexio-dbi-display.md)
- [RGB](06-rgb-display.md)
- [MIPI DSI](07-mipi-dsi-display.md)

Ordinary logic analyzers serve some low-speed digital transactions, not every high-speed differential diagnosis.

Register reads need appropriate command, interface, and return-path support. One failed read does not prove panel damage.

## 6. Choose Diagnostic Patterns

| Pattern | Problems exposed | Notes |
| --- | --- | --- |
| Black/white | Basic display, large updates | Weak for byte/channel errors |
| Red/green/blue | Channels, formats, mapping | Verify individually |
| Intensity bars | Levels and data bits | Match target depth |
| Distinct corners | Orientation, offsets, active area | Avoid symmetric markers |
| Row numbers/colors | Stride and scan layout | Verify source generation |
| Checkerboard | Continuity and pixel arrangement | Compare different cell sizes |
| Moving boundary | Tearing and synchronization | Use after static correctness |
| Frame IDs/distinct alternating colors | Actual submission | Correlate with software events |

Distinct frames separate "no update" from "updated to identical content."

Verify CPU-generated source memory. For hardware test patterns, state which stages they bypass.

## 7. Three Minimal Software Baselines

### 7.1 Baseline A: No GUI

Use a fixed frame or region with colors, bars, and markers.

This removes layout, widgets, decoding, and event scheduling from the investigation.

### 7.2 Baseline B: No Complex Pipeline

Use observable synchronous transfers where possible. For scanout, retain one fixed frame without dynamic writes.

Then introduce DMA, swaps, and asynchronous completion.

### 7.3 Baseline C: Minimal GUI

Add a few widgets without large resources or complex transparency.

Introduce input, resources, animation, acceleration, and application load progressively.

Baselines isolate variables. They do not mean products must abandon cache, DMA, or accelerators.

## 8. Record States Alongside the Timeline

Track:

```text
Update sequence
  -> Rendering starts/finishes
  -> Region or frame submitted
  -> DMA/processing completion
  -> Display event or actual swap state
  -> Buffer released
```

DMA, blanking, VSYNC, and address activation can be separate events.

Name logs by real semantics instead of calling every interrupt "refresh complete."

| Evidence | Purpose |
| --- | --- |
| Request ID and buffer address | Track content and ownership |
| Interrupt snapshot | Separate normal and error states |
| Timeout stage/duration | Locate blocking |
| Underrun/bus/protocol counters | Identify load-dependent faults |
| GPIO markers | Relate submission to interface activity |

Save state before SDK-defined acknowledgment. Clearing an error does not repair its cause.

Avoid extensive ISR printing. Record lightly or notify an owner, then handle work in task context.

## 9. Three Hypothetical Investigations

These illustrate methods, not completed board repairs.

### 9.1 Backlight On, Image Black

Assume RGB:

1. Verify power/reset.
2. Check PCLK and synchronization.
3. Check the DE active area.
4. Verify a valid scanout address.
5. Check whether source memory is actually black.
6. Check mapping and panel state.

If step 2 finds no PCLK, investigate clocks/modules rather than fonts or LVGL settings.

### 9.2 Blocking Works, DMA Sometimes Corrupts

1. Compare identical patterns/windows.
2. Check address reachability and width.
3. Check CPU-to-DMA visibility.
4. Check source/parameter lifetime.
5. Check final peripheral output and notification.

Cache changes are controlled comparisons. If maintenance is missing, fix the handoff rather than making all memory permanently uncached.

### 9.3 Animation and Network Load Cause Corruption

1. Run animation and application load separately.
2. Record FIFO/bus errors.
3. Check traffic and worst access latency.
4. Check scheduling and swap waits.
5. Change one directly related condition and retest.

A temporarily improved symptom is not proof of root cause. Repeat under equivalent conditions.

## 10. Error Handling Belongs in the Driver

Principles:

- Do not report success after failure.
- Do not free active memory before abort confirmation.
- Do not treat faulty frames as completed automatically.
- Record stage, range, and meaningful state.
- Recover through project-defined reset, initialization, or redraw.
- Give required waits timeouts and explicit failure paths.

A silently frozen GUI is harder to diagnose than an explicit failure.

After recovery, prove that owners, queues, and buffers are consistent, not just that the backlight and picture return.

## 11. Bring-Up Acceptance

| Layer | Suggested acceptance |
| --- | --- |
| Wiring/electrical | Matches documentation; reset/clocks explainable |
| Fixed patterns | Correct colors, orientation, size, regions |
| Updates | New content activates with reliable handoffs |
| Errors/recovery | Timeouts and aborts handled explicitly |
| Load | No unexplained faults in representative tasks |
| Repeatability | Cold boots, resets, repeated updates |
| Records | Conditions, evidence, limitations documented |

Set repetitions, duration, and thresholds from project requirements. One success or an arbitrary runtime does not certify every product.

"Not measured" is more useful than labeling unknowns as passed.

## 12. Summary

Troubleshooting means:

1. Fix conditions and describe symptoms.
2. Check hardware/interface before pixels/GUI.
3. Collect appropriate patterns and timelines.
4. Change one relevant variable and repeat.
5. Validate failure and recovery as well.

Next: [How Do LCDIF / eLCDIF Display Controllers Work?](09-lcdif-elcdif.md), moving inside the chip to scanout, formats, and update events.

## References

- [NXP eLCDIF RGB example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/elcdif/rgb/elcdif_rgb.c)
- [NXP MCULCD eDMA example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/flexio/mculcd/edma_transfer/flexio_mculcd_edma_transfer.c)
- [RT1170 DSI board support](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/_boards/evkbmimxrt1170/driver_examples/lcdifv2/lcdifv2_support.c)
- [LVGL 9.2 display interface](https://docs.lvgl.io/9.2/porting/display.html)

Examples illustrate paths and conditions. Product acceptance needs actual device, board, panel documentation and measurements.
