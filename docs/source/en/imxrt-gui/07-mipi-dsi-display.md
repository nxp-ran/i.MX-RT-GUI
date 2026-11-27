# Article 7: MIPI DSI Displays: The High-Speed Serial Link

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [RGB Displays: Pixel Clock and Continuous Scanout](06-rgb-display.md)
>
> Next: [A Reusable Display Bring-Up and Troubleshooting Process](08-display-bring-up.md)
>
> Goal: Separate the DSI Host, D-PHY, pixel source, and panel, then check modes, formats, budgets, and initialization layer by layer.
>
> Scope: The public i.MX RT1170 SDK path is a concrete reference, not a capability claim for every i.MX RT. Resolution, timing, rate, and wait values are assumptions, not panel or PHY recommendations.

## 1. A Serial Link Does Not Remove the Frame Problem

In [Article 6](06-rgb-display.md), a controller continuously reads a frame and generates RGB timing.

A typical DSI video-mode path retains the pixel source and adds packetization and serial transmission:

```text
CPU / PXP / GPU
       |
       v
Frame buffer
       |
       v
Display controller: Pixels and timing
       |
       v
DSI Host: Packets and scheduling
       |
       v
D-PHY: High-speed electrical link
       |
       v
Panel controller and display
```

DSI changes interface organization and throughput. It does not replace frame storage, rendering, or coherency.

DSI availability also does not make one initialization sequence valid for every module.

## 2. Four Responsibilities

| Component | Responsibility | Checks |
| --- | --- | --- |
| Display controller | Produce pixels and timing from memory | Format, clock, sync, address |
| DSI Host | Organize commands, packets, video | Mode, packet format, channel, timeout |
| D-PHY | Implement the physical link | Lanes, reference, rate, timing |
| Panel controller | Initialize and consume data | Commands, format, mode, scanout |

Video routing, clock gates, power domains, and resets can be necessary parts of the path.

A panel labeled DSI still needs a data-lane count, formats, modes, command set, and electrical specification.

## 3. Command and Video Modes

### 3.1 Command Mode

A typical command-mode panel with image storage can accept windows and image-write transactions, then scan retained contents.

The mode name alone does not establish GRAM size, partial-update capability, or synchronization.

Check:

- Required commands and update method.
- Host pixel-transfer path.
- TE or other synchronization.
- SDK and GUI-port implementation.

### 3.2 Video Mode

Video mode sends timed image data continuously. Common variants are:

- Non-burst with sync pulses.
- Non-burst with sync events.
- Burst.

They change packet organization, transmission windows, and blanking handling. Confirm the mode supported by the panel.

### 3.3 Initialization Commands Do Not Establish Command-Mode Display

Video-mode panels also need initialization commands.

Being able to send DCS or Generic commands does not prove command-mode image updates are implemented.

Likewise, working video does not prove every read command or return-direction configuration.

## 4. Lanes, LP, and HS Are Not SPI

Physical lanes and logical virtual channels are different.

| Concept | Meaning |
| --- | --- |
| Data lane | Physical serial-data path |
| Clock lane | High-speed clock path in this D-PHY model |
| Virtual Channel | Logical packet identifier |
| LP | Low-power signaling states/transport |
| HS | High-speed transport |

Some initialization commands use LP while video pixels use HS. The actual policy depends on Host, panel, and driver.

Transitions, return direction, waits, and timeouts require configuration. LP command success does not prove HS video operation.

Use appropriate equipment for high-speed differential probing. An ordinary low-speed logic analyzer is not a D-PHY validator; an undecodable trace does not by itself prove no transmission.

## 5. Keep an Explicit Clock Table

| Clock or rate | Purpose | Common confusion |
| --- | --- | --- |
| Pixel clock | Generate video timing | Active resolution alone is insufficient |
| PHY reference | Generate link timing | Not the output bit rate |
| HS bit rate per lane | Budget serial payload | Not total interface rate |
| Byte clock | Some Host counts/settings | Verify its relation to bit rate |
| Escape clock | LP control | Not pixel or HS clock |

In common D-PHY HS DDR descriptions, bit rate, clock-lane frequency, and byte clock can have factors of two or eight. Actual API units and counts must follow the driver.

Do not directly equate a requested `bitClk` value with an oscilloscope clock frequency.

The generated rate can differ from the requested rate. Base subsequent timing on the actual returned rate.

## 6. Check Three Pixel Representations

These are separate:

```text
Frame-buffer memory format
          |
          v
Display-controller-to-Host pixel representation
          |
          v
DSI pixel packet format
```

The referenced RT1170 LCDIFv2 RGB565 example uses RGB565 source frames; its board DSI support configures 24-bit DPI and RGB888 pixel packets.

Therefore:

- Memory capacity follows the actual source.
- Link traffic follows the output packets.
- 16-bit RGB565 storage cannot replace a 24-bit RGB888 link budget.

Fields such as `pixelPayloadSize` may count pixels, not bytes. Read their definitions.

RGB666 can also be tightly or loosely packed. Color depth alone does not establish wire bytes.

## 7. Budget Each Line, Not Only Each Second

Assume:

- 800 × 480 at 60 Hz.
- Horizontal total 928 and vertical total 525.
- RGB888 on the link.
- Two data lanes, each assumed at 500 Mbit/s.
- One pixel long packet per line.
- Six bytes for packet header and checksum.
- A further 2 us reserved per line for costs not individually modeled.

Average active payload:

```text
800 × 480 × 60 × 24 = 552.96 Mbit/s
Active payload per lane = 276.48 Mbit/s
```

That is not a sufficient condition.

One line takes approximately 31.746 us. Its 2,400 pixel bytes plus six overhead bytes take 19.248 us at the assumed combined lane rate.

Other packets, transitions, and waits must fit the available window. These assumptions do not establish complete protocol timing.

The offline script demonstrates two budgeting views:

```python
width, height, refresh = 800, 480, 60
h_total, v_total = 928, 525
bits_per_pixel = 24
lanes = 2
lane_rate = 500_000_000
packet_overhead_bytes = 6
reserved_us = 2

pixel_clock = h_total * v_total * refresh
line_us = h_total / pixel_clock * 1_000_000
packet_bytes = width * bits_per_pixel // 8 + packet_overhead_bytes
wire_us = packet_bytes * 8 / (lanes * lane_rate) * 1_000_000
active_rate = width * height * refresh * bits_per_pixel
timing_rate_per_lane = pixel_clock * bits_per_pixel / lanes

if wire_us + reserved_us > line_us:
    raise ValueError("The assumed packet and reserved interval exceed one line.")

print(f"Active payload per lane: {active_rate / lanes / 1_000_000:.2f} Mbit/s")
print(f"Timing-based rate per lane: {timing_rate_per_lane / 1_000_000:.3f} Mbit/s")
print(f"Line time: {line_us:.3f} us")
print(f"Packet bytes: {packet_bytes}")
print(f"Packet wire time: {wire_us:.3f} us")
print(f"Packet plus reserve: {wire_us + reserved_us:.3f} us")
```

Output:

```text
Active payload per lane: 276.48 Mbit/s
Timing-based rate per lane: 350.784 Mbit/s
Line time: 31.746 us
Packet bytes: 2406
Packet wire time: 19.248 us
Packet plus reserve: 21.248 us
```

500 Mbit/s, 6 B, and 2 us are model inputs. Verify Host/PHY limits, video mode, packet splits, blanking, other protocol costs, and panel requirements.

The RT1170 board example also demonstrates estimating rate from complete pixel timing and adding headroom. This is a particular example's strategy, not a universal multiplier.

## 8. Validate Initialization in Layers

A logical investigation sequence is:

```text
Confirm connections and panel requirements
                 |
                 v
Power, isolation, resets, video routing
                 |
                 v
Pixel, reference, Escape clocks
                 |
                 v
Host and D-PHY configuration
                 |
                 v
Panel initialization and checks
                 |
                 v
Valid frame, video input, scanout
                 |
                 v
Display and backlight
```

Actual reset-release and command order must follow the target SDK and module. This is not a mechanical register sequence.

RT1170 support code configures LCDIFv2-to-DSI routing. Initializing only the Host may not connect the correct pixel source.

Check every stage, record failures, and stop progressing. Do not announce successful startup after initialization failure.

## 9. Verify Panel Control Separately from Video

Start with the SDK's supported matching module and record:

- Panel driver and resource callbacks.
- Power, reset, backlight.
- DCS/Generic types and parameters.
- Virtual Channel.
- State-transition waits such as sleep exit and display enable.
- Panel format and video mode.

Some modules also need I²C control. Not every control operation is a DSI command.

Panel-ID reads are not universally available or mandatory. They require return-path, command, wiring, and driver support. An unsuccessful read alone does not establish hardware damage.

## 10. Minimal Display Experiments

| Experiment | Main evidence | Does not establish |
| --- | --- | --- |
| Initialization succeeds | Expected control path | Correct HS video pixels |
| Host/PHY ready | Required module states | Correct source, packets, all timing |
| Solid colors and bars | Basic video path | Dynamic/cache correctness |
| Corners and row patterns | Orientation, dimensions, mapping | No underrun under load |
| Alternating frames | Submission and swapping | All workloads free of latency/tearing |
| Asset/CPU load | Bandwidth and synchronization | Long-term validation unnecessary |

Use internal test patterns only where the hardware provides them.

An internal pattern working while memory images fail narrows the problem, but document which stages it bypasses.

## 11. Typical Problems

| Symptom | Initial checks |
| --- | --- |
| Commands fail or time out | Power, reset, LP, type, channel, timeout units |
| Initialization succeeds, image remains black | Routing, source, scanout, HS, panel state |
| Colors or rows are systematically wrong | DPI, packet format, pixel count, layout |
| Changing link rate breaks output | Generated PLL rate, PHY timing, panel limits |
| Static works, updates fail | Cache, swapping, memory, FIFO |
| ECC/CRC/protocol errors | Packet/link evidence and timing |
| Interrupts occur without new content | Event meaning, address, pixels, panel scanout |

Do not reduce every DSI problem to signal integrity or every black screen to an initialization array.

## 12. Summary

Align three layers:

1. The pixel source, memory, and timing.
2. Host modes, packets, and scheduling.
3. PHY and panel requirements.

Initialization, HS video, and smooth GUI operation are different validation goals.

Next: [A Reusable Display Bring-Up and Troubleshooting Process](08-display-bring-up.md), collecting the shared methods for SPI, parallel, RGB, and DSI.

## References

- [NXP MIPI DSI interface](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/mipi_dsi/fsl_mipi_dsi.h)
- [RT1170 LCDIFv2/DSI board support](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/_boards/evkbmimxrt1170/driver_examples/lcdifv2/lcdifv2_support.c)
- [Panel and wiring notes for the RT1170 example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/_boards/evkbmimxrt1170/driver_examples/lcdifv2/lcdifv2_examples_readme.md)
- [NXP RT1170 product entry point](https://www.nxp.com/products/i.MX-RT1170)

Matching interface names do not prove matching IP. Different `fsl_mipi_dsi` variants can serve different devices; verify the actual target.
