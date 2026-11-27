# Article 2: i.MX RT Graphics Capabilities and Platform Selection

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Previous: [What Makes Up an Embedded GUI System?](01-gui-system-overview.md)
>
> Next: [Budget Resolution, Display Memory, and Bandwidth Before Choosing a Screen](03-memory-and-bandwidth.md)
>
> Goal: Translate product requirements into display, rendering, memory, and software requirements, using a reusable selection process.
>
> Sources: NXP public product pages and SDKs for representative devices, checked on 2026-11-26. This is not a complete ordering-code catalog and contains no board performance measurements.

## 1. Why CPU Frequency Alone Is Not Enough

[Article 1](01-gui-system-overview.md) separated the GUI into application, rendering, memory, and display-output layers.

Does that mean you should simply choose the fastest i.MX RT?

CPU frequency matters, but it does not answer:

- Can the device connect to the chosen display?
- Where will complete frames reside, and can scanout access them?
- Who handles translucent images, rotation, and scaling?
- Are reusable SDK drivers available?
- Can the chosen LVGL version use the accelerator?
- How much CPU and memory remain for control, communication, and other tasks?

If the output link can transfer only a few complete images each second, a faster CPU cannot make that same link transfer dozens.

If two frame buffers are required but only one fits, frequency does not solve the capacity shortfall.

A better selection sequence is:

```text
Product experience requirements
              |
              v
Display and update strategy
              |
              v
Capacity, bandwidth, and rendering workload
              |
              v
Device, package, memory, and board
              |
              v
SDK, drivers, and GUI integration
```

Do not choose a chip first and assume optimization will solve every remaining mismatch.

## 2. Make the Requirements Checkable

"Smooth," "attractive," and "Chinese support" are not specific enough.

Document at least these requirements before choosing hardware:

| Dimension | Information required | Selection impact |
| --- | --- | --- |
| Display | Resolution, interface, controller, orientation | Output path and baseline data volume |
| Updates | Numeric fields, lists, full-screen animation | Actual rendering and transfer area |
| Experience | Update rate, latency, tearing policy | Throughput and synchronization |
| Graphics | Transparency, scaling, rotation, vector graphics | Software workload and acceleration |
| Resources | Images, Chinese fonts, update mechanism | Flash, RAM, and loading overhead |
| Application | Control cycles, communication, real-time needs | GUI resource budget |
| Engineering | Package, PCB, power, cost, supply | Practical implementation |
| Software | SDK, LVGL, RTOS, compiler versions | Integration and maintenance |

Two 320 × 240 interfaces can have very different requirements.

**Interface A: Temperature control panel**

- Numeric values and icons update on demand.
- Most pixels remain static.
- Continuous full-screen animation is unnecessary.
- CPU time should remain available for control and communication.

**Interface B: Image browser with animated transitions**

- Large areas change frequently.
- Images require decoding, scaling, and blending.
- Full-update throughput, loading, and peak memory matter more.

Equal resolution does not imply equal rendering, resource, or bandwidth requirements.

## 3. Four Different Meanings of "Supported"

An unqualified claim of support is risky.

### 3.1 Layer One: Silicon Capability

Verify that the actual ordering code provides:

- The display controller or transfer peripheral.
- Required PXP, GPU, or other graphics capability.
- Adequate on-chip RAM and external-memory interfaces.
- Viable access paths among the relevant modules.

The object being checked is a specific device, not just "RT10xx" or "RT11xx."

Members of a family can differ in peripherals, memory, package, and clock limits.

### 3.2 Layer Two: Package and Board Connectivity

An internal interface does not prove that the package or board exposes it.

Check:

- Required pins are available in the selected package.
- Pin multiplexing does not conflict with Flash, memory, or application peripherals.
- Voltages, connectors, and pin assignments match the display.
- Power, reset, backlight, and touch are connected appropriately.
- PCB and signal-integrity conditions meet high-speed requirements.

Two boards advertising RGB support can still have incompatible connectors.

### 3.3 Layer Three: SDK Drivers

Check:

- The SDK supports this device and board revision.
- The controller driver and target-panel component exist.
- DMA, asynchronous completion, and error handling are available.
- Examples use equivalent display, memory, and clock conditions.
- Board initialization or additional interface layers need adapting.

A display example does not mean every panel can be connected unchanged.

### 3.4 Layer Four: LVGL Integration

Finally, check the GUI layer:

- Render mode and buffer strategy.
- Backend availability in the selected LVGL version.
- SDK/backend compatibility with that version.
- Actual hardware execution for the target format and tasks.
- Software handling of unsupported tasks.
- Threading, cache, and asynchronous lifetimes.

Track these layers separately:

| Feature | Silicon | Board | SDK | LVGL |
| --- | --- | --- | --- | --- |
| Target display output | Verify | Verify | Verify | Verify |
| PXP acceleration | Verify | Verify clocks and memory | Verify | Verify |
| GPU acceleration | Verify | Verify clocks and memory | Verify | Verify |
| External frame buffer | Verify access path | Verify memory and wiring | Verify initialization | Verify placement |

Attach evidence to every confirmed entry. Leave unfinished checks marked as such.

## 4. Representative Devices, Not One Undifferentiated Family

The following tables separate basic resources from graphics paths.

They demonstrate the selection process and do not replace datasheets, manuals, errata, or ordering-code information.

### 4.1 CPU and On-Chip RAM

| Family and representative device | Maximum CPU frequency reference | On-chip RAM reference | GUI implication |
| --- | --- | --- | --- |
| [RT1010, represented by RT1011](https://www.nxp.com/products/i.MX-RT1010) | Cortex-M7, up to 500 MHz | 128 KiB | Favor GRAM and chunked rendering when RAM is limited |
| [RT1020, represented by RT1021](https://www.nxp.com/products/i.MX-RT1020) | Cortex-M7, up to 500 MHz | 256 KiB | More workspace, but strict budgeting remains necessary |
| [RT1050, represented by RT1052](https://www.nxp.com/products/i.MX-RT1050) | Cortex-M7, up to 600 MHz | 512 KiB | Large complete frames often require external RAM |
| [RT1060, represented by RT1062](https://www.nxp.com/products/i.MX-RT1060) | Cortex-M7, up to 600 MHz | 1 MiB | Useful for display/PXP exercises, but capacity is finite |
| [RT1064](https://www.nxp.com/products/i.MX-RT1064) | Cortex-M7, up to 600 MHz | 1 MiB | Product-rated 4 MB Flash is not working RAM |
| [RT1160, represented by RT1166](https://www.nxp.com/products/i.MX-RT1160) | Cortex-M7 / M4, up to 600 / 240 MHz | 1 MiB | Account for graphics modules and multicore allocation |
| [RT1170, represented by RT1176](https://www.nxp.com/products/i.MX-RT1170) | Cortex-M7 / M4, up to 1 GHz / 400 MHz | 2 MiB | Broader graphics paths, but still check the memory map |
| [RT1180, represented by RT1189](https://www.nxp.com/products/i.MX-RT1180) | Cortex-M7 / M33, up to 800 / 300 MHz | 1.5 MiB | Industrial connectivity emphasis; numbering does not prove graphics features |

RAM is expressed in binary units. Address maps, partitions, and configurable regions remain device-specific. Maximum frequencies are product capability references, not guarantees for every ordering code, temperature grade, and supply condition.

**Total on-chip RAM is not a contiguous allocation available entirely to the GUI.**

It can include TCM, ordinary RAM, memory assigned to another core, and regions occupied by code data, heaps, stacks, or shared data.

### 4.2 Display and Acceleration

Evidence labels:

- **Listed:** The public product information or target SDK explicitly identifies the capability.
- **Not listed:** This check does not establish the capability; exclude it from the initial budget. A missing macro alone does not prove hardware absence.
- Entries apply only to the representative device, not every member of its family.

| Device | SPI path | Native RGB path | Native MIPI DSI | PXP | Separate GPU / vector graphics | External-memory controller entry points |
| --- | --- | --- | --- | --- | --- | --- |
| RT1011 | LPSPI listed | Not listed | Not listed | Not listed | Not listed | FlexSPI listed; SEMC not listed |
| RT1021 | LPSPI listed | Not listed | Not listed | Not listed | Not listed | FlexSPI and SEMC listed |
| RT1052 | LPSPI listed | LCDIF / eLCDIF path listed | Not listed | Listed | Not listed | FlexSPI and SEMC listed |
| RT1062 | LPSPI listed | LCDIF / eLCDIF path listed | Not listed | Listed | Not listed | FlexSPI and SEMC listed |
| RT1064 | LPSPI listed | LCDIF / eLCDIF path listed | Not listed | Listed | Not listed | FlexSPI and SEMC listed |
| RT1166 | LPSPI listed | eLCDIF and LCDIFv2 listed | Listed | Listed | Vector graphics listed | FlexSPI and SEMC listed |
| RT1176 | LPSPI listed | eLCDIF and LCDIFv2 listed | Listed | Listed | 2D GPU listed | FlexSPI and SEMC listed |
| RT1189 | LPSPI listed | Not listed | Not listed | Not listed | Not listed | FlexSPI and SEMC listed |

Use the table as follows:

1. Shortlist devices with listed evidence for a required native interface or accelerator.
2. Verify the complete manuals and actual SKU.
3. Do not turn "Not listed" into an assumed feature; obtain official evidence when necessary.
4. FlexSPI presence does not imply compatibility with any QSPI display.
5. SEMC presence does not imply every memory type, bus width, or package is usable.

Interfaces emulated with FlexIO or other resources require separate timing, pin, DMA, and driver evaluation. They are not equivalent to dedicated display interfaces.

### 4.3 A Useful Family-Level Difference

The [RT1040 product page](https://www.nxp.com/products/i.MX-RT1040) specifically mentions LCD support on RT1043 while describing other family members.

A family page can combine capabilities from several members. An LCD entry does not establish identical display support on every RT104x and package.

This table deliberately excludes RT104x members that were not individually checked. Add other four-digit models using the same evidence-based process, not numerical inference.

## 5. Three GUI Architecture Strategies

Classifying systems by architecture is more useful than ranking chips by frequency alone.

### 5.1 Software Rendering with Display GRAM

Typical path:

```text
LVGL / application
        |
        v
CPU renders into a small buffer
        |
        v
LPSPI + DMA
        |
        v
Display controller with GRAM
```

Consider this for small displays, numeric fields, menus, and status interfaces.

Advantages:

- Partial draw buffers can reduce MCU memory use.
- Interfaces usually require relatively few pins.
- The display side performs panel scanout.

Limits:

- Large continuous updates can saturate the serial link.
- Image processing and rendering can still occupy the CPU.
- Writes to display GRAM can conflict with scanout.

RT1011 and RT1021 are candidates for this architecture. Validate actual scenes and links; a working demo does not prove the required experience.

### 5.2 Display Controller, External RAM, and PXP

Typical path:

```text
CPU / PXP
    |
    v
MCU-accessible complete frame buffer
    |
    v
Display controller
    |
    v
RGB panel
```

RT1052, RT1062, and RT1064 are representative candidates.

The questions extend beyond transfer speed:

- Can memory continuously supply scanout?
- Do rendering and scanout contend for the same memory?
- Does PXP support the required operation?
- Are swaps and cache handoffs correct?

This can suit larger display areas while increasing memory, routing, and synchronization requirements.

### 5.3 GPU, Complex Graphics, and Multiple Outputs

Verified RT1166 and RT1176 platforms enable investigation of GPU/vector graphics, PXP, RGB, and DSI paths.

More execution options do not mean every GUI should use every module.

Check:

- Actual GPU task coverage.
- Supported formats and memory layouts.
- Submission, execution, synchronization, and cache overhead.
- CPU/GPU/display memory contention.
- Graphics-resource management in multicore systems.

**More modules provide more choices, not automatic performance gains.**

## 6. Three Requirement-Driven Selection Exercises

These are architecture exercises, not board performance guarantees.

### 6.1 Scenario A: 320 × 240, Mostly Numeric and Status Updates

Assume RGB565.

A complete frame requires:

```text
320 × 240 × 2 = 153,600 B = 150 KiB
```

Two partial buffers, each 20 lines high, require:

```text
320 × 20 × 2 × 2 = 25,600 B = 25 KiB
```

For a platform with 128 KiB total on-chip RAM:

- A 150 KiB MCU frame buffer exceeds total capacity.
- Two partial buffers totaling 25 KiB are more plausible.
- GUI heap, task stacks, font caches, and application data must still be subtracted.

With display GRAM, evaluate CPU rendering, small buffers, and DMA region transfers first.

Budget link throughput separately. Feasible numeric updates do not establish equivalent full-screen transition performance.

### 6.2 Scenario B: 800 × 480 with Frequent Page Animation

Two complete RGB565 buffers require:

```text
800 × 480 × 2 × 2 = 1,536,000 B = 1,500 KiB
```

Compare with total on-chip capacities:

| Capacity reference | What it establishes |
| --- | --- |
| 512 KiB | These two complete buffers do not fit |
| 1 MiB, or 1,024 KiB | Still insufficient |
| 2 MiB, or 2,048 KiB | Nominally 548 KiB remains, but feasibility is not yet established |

The last case still needs answers:

- Can display and accelerator accesses reach both buffers?
- Is the memory contiguous, or can buffers be allocated separately as required?
- How much RAM do application tasks need?
- Does animation require off-screen layers?

Evaluate external RAM, scanout, and suitable rendering backends carefully.

### 6.3 Scenario C: 800 × 480 with Complex Blending and Transforms

Two complete ARGB8888 buffers require:

```text
800 × 480 × 4 × 2 = 3,072,000 B = 3,000 KiB
```

That exceeds 2 MiB.

Blending reads foreground and background before writing the result, adding far more traffic than a solid fill.

Evaluate:

1. Whether every complete frame really needs ARGB8888.
2. Whether Alpha can be limited to partial off-screen layers.
3. GPU/PXP format and operation combinations.
4. Actual external-RAM bandwidth.
5. LVGL backend coverage.

Buying a GPU-equipped chip does not eliminate capacity or bandwidth limits.

## 7. Memory Interfaces Determine Where Resources Can Go

Separate at least three storage uses:

| Use | Common placement | Main checks |
| --- | --- | --- |
| Code, images, fonts, static resources | Flash or other nonvolatile storage | Capacity, read speed, encoding, access method |
| Runtime data and working buffers | On-chip or external RAM | Capacity, peaks, fragmentation, latency |
| Pixels consumed by scanout or accelerators | RAM reachable by those modules | Addresses, format, alignment, cache, bandwidth |

Avoid two common misunderstandings.

### 7.1 More Flash Does Not Mean More Frame-Buffer RAM

Flash holds programs and resources; it is not ordinary RAM for frequent frame-buffer writes.

Flash-resident resources can still require RAM during rendering or decoding, and graphics operations may allocate outputs.

RT1064 Flash capacity helps code/resource placement, not direct expansion of GUI working RAM.

### 7.2 CPU Access Does Not Prove Peripheral Access

The CPU, DMA, display controller, PXP, and GPU may have different memory paths.

For each buffer, verify:

```text
Writer -> Reader -> Address reachability -> Data visibility -> Release owner
```

Do not allocate memory to every consumer solely because it is called TCM or SRAM.

Memory and cache articles will examine platform-specific access and configuration.

## 8. Display Interface and Platform Selection Are Connected

| Interface | Conditions to evaluate first | Typical cost |
| --- | --- | --- |
| Single-line SPI + GRAM | Small update area or modest throughput | Large updates limited by serial throughput |
| Multi-line QSPI display | Verified panel/MCU transaction compatibility | Protocol, driver, and resource-sharing complexity |
| 8080-style parallel | Available pins, timing, and DMA path | More pins and implementation work |
| RGB scanout | Native controller and complete-frame storage | Continuous memory traffic, timing, synchronization |
| MIPI DSI | Host, PHY, panel mode, and software match | Link and panel configuration complexity |

There is no universal ranking from "low-end" to "high-end" interfaces.

Small numeric interfaces may benefit from on-demand serial updates and GRAM. Continuous full-screen animation may require greater output throughput and a stable frame-storage path.

Panel price, touch, connectors, and initialization support also influence the decision.

## 9. What SDK Examples Prove

An SDK example is a valuable known starting point, but its conclusions have boundaries.

A running LVGL benchmark demonstrates that its particular platform, panel, memory, driver, and configuration can execute that workload.

It does not automatically establish:

- Identical initialization and timing for another panel.
- Sufficient memory and bandwidth at a higher resolution.
- Hardware acceleration of every widget.
- Equivalence between benchmark and product workloads.
- Compatibility after changing LVGL major versions.

Reuse an example by:

1. Recording its complete conditions.
2. Identifying display and memory paths.
3. Preserving a stable baseline.
4. Changing one requirement-related condition at a time.
5. Remeasuring correctness, resource use, and performance.

Do not present one example's FPS as the chip's universal GUI performance.

## 10. Organizing Platforms for This Series

To avoid a different environment in every article, organize experiments into a basic path and an advanced path.

| Path | Representative candidates | Main topics |
| --- | --- | --- |
| Basic display and pixel processing | Verified platforms such as RT1062 | RGB, frames, PXP, memory/cache, LVGL baseline |
| GPU and DSI | Verified platforms such as RT1176 | GPU/VG-Lite, DSI, complex drawing, comparisons |
| Small-memory serial supplement | RT1011, RT1021 | Partial buffers, GRAM, SPI throughput, DMA |

This is an experiment-organization suggestion, not a finalized board selection or a requirement to replace existing hardware.

Another four-digit i.MX RT board can remain the main platform. Build its own capability table and conditions instead of inheriting another device's features or results.

Before board-specific work, fix:

- Complete device ordering code and board revision.
- Display module, controller, interface, resolution.
- External-memory device and connections.
- SDK, LVGL, RTOS, compiler versions.
- CPU, memory, and display clocks.
- Buffer layout and cache/MPU attributes.

## 11. A Project Selection Card

Use this card in project planning or article experiment records.

| Item | Information to fill in |
| --- | --- |
| Interface | Pages, animation, translucent layers, Chinese fonts |
| Experience | Visible-update target, latency target, tearing requirements |
| Display | Module, controller, interface, resolution, orientation |
| Chip | Complete ordering code, package, temperature grade |
| Output | Controller/peripheral, DMA, synchronization events |
| Rendering | CPU, PXP, GPU, unsupported-task handling |
| Memory | Regions, frame capacity, workspaces, peak budget |
| External resources | Flash/RAM devices, buses, reachability |
| Software | SDK, LVGL, RTOS, drivers, toolchain |
| Evidence | Manual sections, errata, schematic, examples, measurements |
| Unverified items | Missing checks, risks, next validation steps |

Apply four gates:

1. **Connection:** Protocol and pins actually match.
2. **Capacity:** Required buffers and application data can be allocated.
3. **Throughput:** Output, memory, and rendering meet the workload.
4. **Software:** Drivers, framework, and synchronization can be reliable.

Excellence in one gate cannot compensate for failure in another.

## 12. Summary: Select the Data Path Before the Device

A good GUI choice matches the whole pixel path to the product, not just the best individual specification.

- Small, partial updates favor evaluating small buffers and display GRAM.
- Large continuous updates require scanout, complete-frame storage, and bandwidth checks.
- Complex graphics require actual accelerator task coverage, not a GPU label.
- Multicore processing, Flash capacity, and frequency matter, but do not replace access-path and software validation.

Next: [Budget Resolution, Display Memory, and Bandwidth Before Choosing a Screen](03-memory-and-bandwidth.md), expanding capacity and throughput into reproducible budgets.

## References and Verification Notes

### Product Entry Points

- [NXP RT1010](https://www.nxp.com/products/i.MX-RT1010)
- [NXP RT1020](https://www.nxp.com/products/i.MX-RT1020)
- [NXP RT1040](https://www.nxp.com/products/i.MX-RT1040)
- [NXP RT1050](https://www.nxp.com/products/i.MX-RT1050)
- [NXP RT1060](https://www.nxp.com/products/i.MX-RT1060)
- [NXP RT1064](https://www.nxp.com/products/i.MX-RT1064)
- [NXP RT1160](https://www.nxp.com/products/i.MX-RT1160)
- [NXP RT1170](https://www.nxp.com/products/i.MX-RT1170)
- [NXP RT1180](https://www.nxp.com/products/i.MX-RT1180)

### Public SDK Device Evidence

The following links use the same fixed public commit, avoiding drift in a rolling branch:

- [RT1011 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1010/MIMXRT1011/MIMXRT1011_features.h)
- [RT1021 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1020/MIMXRT1021/MIMXRT1021_features.h)
- [RT1052 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1050/MIMXRT1052/MIMXRT1052_features.h)
- [RT1062 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1060/MIMXRT1062/MIMXRT1062_features.h)
- [RT1064 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1064/MIMXRT1064/MIMXRT1064_features.h)
- [RT1166 Cortex-M7 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1160/MIMXRT1166/MIMXRT1166_cm7_features.h)
- [RT1176 Cortex-M7 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1170/MIMXRT1176/MIMXRT1176_cm7_features.h)
- [RT1189 Cortex-M7 features](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1180/MIMXRT1189/MIMXRT1189_cm7_features.h)
- [RT1166 device header](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1160/MIMXRT1166/MIMXRT1166_cm7.h)
- [RT1176 device header](https://github.com/nxp-mcuxpresso/mcux-devices-rt/blob/85cc37edc7b9d00a69f41b1072e8cb19ae6e5311/RT1170/MIMXRT1176/MIMXRT1176_cm7.h)

SDK macros help identify modules and driver conditions, but they are not a complete hardware catalog. A device header or product page may describe a module without a matching `FSL_FEATURE_SOC_*_COUNT` macro. Final selection must use the complete target manuals and ordering code.
