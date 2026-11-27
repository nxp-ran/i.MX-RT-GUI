# From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice

> Series roadmap: Display interfaces → Display peripherals and memory → PXP / GPU → LVGL → Performance optimization.
>
> Start reading: [Article 1: What Makes Up an Embedded GUI System?](01-gui-system-overview.md)

## Available Articles

| Article | Title |
| --- | --- |
| 1 | [What Makes Up an Embedded GUI System?](01-gui-system-overview.md) |
| 2 | [i.MX RT Graphics Capabilities and Platform Selection](02-platform-selection.md) |
| 3 | [Budget Resolution, Display Memory, and Bandwidth Before Choosing a Screen](03-memory-and-bandwidth.md) |
| 4 | [SPI / QSPI Displays: From Commands to Partial Updates](04-spi-qspi-display.md) |

## I. What Does This Series Address?

A familiar embedded-GUI situation is that the display works and the example runs, but a different screen, higher resolution, or animation introduces problems.

- How should you choose between SPI, 8080, RGB, and MIPI DSI displays?
- What do the display controller, DMA, PXP, and GPU each do?
- Why is the interface sluggish despite a high CPU frequency?
- Why can double buffering still produce tearing?
- Why does enabling cache improve performance but occasionally leave stale pixels?
- How can you prove that LVGL hardware acceleration is actually running?

Rather than presenting disconnected tricks, the series follows a complete data path:

```text
Application logic and user interaction
                 |
                 v
LVGL: Widgets, layout, events, invalidated regions, draw tasks
                 |
                 v
CPU software rendering / PXP / GPU: Selected by task and capability
                 |
                 v
Pixel buffers: Draw buffers and display frame buffers
                 |
                 v
Display controller / transfer peripheral
                 |
                 v
Display-side controller / panel
```

This is a logical model, not a fixed hardware topology for every device. Memory, bus bandwidth, cache coherency, and synchronization affect the whole path.

The goal is not merely to run an example, but to explain where pixels originate, which modules handle them, and where the bottleneck lies.

## II. Scope and Writing Conventions

### 2.1 Intended Readers

- Embedded engineers planning an i.MX RT product with a display.
- Developers who have a working display and want to understand its operation and performance limits.
- Engineers porting LVGL or introducing PXP / GPU acceleration.

Basic C, MCU peripheral, interrupt, and RTOS knowledge is recommended. Prior graphics expertise is not required.

### 2.2 Platform Scope

The series covers i.MX RT devices with four-digit model numbers. Device-specific functions are tied to explicit models, packages, boards, and SDKs.

The following boundaries apply:

1. **Do not infer features from a family name.** Display interfaces, PXP, GPU, and external-memory support differ.
2. **Separate four support layers.** Silicon capability, board connectivity, SDK drivers, and LVGL integration are different facts.
3. **Separate output from rendering.** Display controllers output pixels; PXP / GPU execute supported processing or graphics work.
4. **Separate hardware from software.** VG-Lite is an API / driver stack, not a hardware peripheral alongside PXP and the GPU.
5. **Fix software versions.** Code identifies its SDK and LVGL versions instead of mixing APIs from different major releases.
6. **Separate theory from measurements.** Calculations state assumptions; performance results identify platform, workload, and measurement method.

Choose the main board, panel, and software versions before platform-specific exercises. This outline does not assume that one board contains every graphics capability.

### 2.3 Suggested Reading Routes

| Goal | Suggested articles |
| --- | --- |
| Understand the complete system | Articles 1–3 |
| Connect a new display | Articles 4–8, then 9–12 |
| Investigate corruption, tearing, or memory problems | Articles 9–12 |
| Use PXP / GPU | Articles 13–16 |
| Port and optimize LVGL | Articles 17–23 |
| Integrate a product-level example | Article 24 |

## III. Detailed Outline

The "Deliverable" below is the writing objective of each article, not a claim that its code or measurements already exist.

## Part One: The Complete GUI System

### Article 1: What Makes Up an Embedded GUI System?

**Key question:** Which modules cooperate to turn a software button into screen pixels?

**Topics:**

- Distinguish lighting up the display, displaying an image, and smooth interaction.
- Roles of the application, framework, renderer, memory, output path, and panel.
- Displays with GRAM versus MCU-driven continuous scanout.
- Draw buffers, display frame buffers, and display GRAM.
- Panel refresh, GUI update rate, CPU utilization, and response latency.

**Deliverable:** A system diagram, pixel path, and shared terminology.

**Full article:** [Read Article 1](01-gui-system-overview.md).

### Article 2: i.MX RT Graphics Capabilities and Platform Selection

**Key question:** How do you choose the right i.MX RT platform for a GUI?

**Topics:**

- A matrix of display interfaces, PXP, GPU, on-chip RAM, and external-memory interfaces.
- Cross-check product information, manuals, errata, and SDK support.
- Separate silicon capability, package pins, board connections, and software support.
- Trade resolution, animation complexity, cost, and memory.
- Choose the main platform and explain differences on other platforms.

**Deliverable:** A traceable capability table and selection checklist.

**Full article:** [Read Article 2](02-platform-selection.md).

### Article 3: Budget Resolution, Display Memory, and Bandwidth Before Choosing a Screen

**Key question:** Can you establish basic feasibility before connecting a display?

**Topics:**

- Resolution, format, stride, and frame-buffer capacity.
- RGB565, RGB888, and ARGB8888 quality and storage trade-offs.
- Single/double buffering and total working-memory budgets.
- Active pixel payload, interface throughput, memory bandwidth, and pixel clock.
- MB / MiB and average versus instantaneous bandwidth.

**Deliverable:** Capacity, bandwidth, and timing budgets using resolutions such as 800 × 480.

**Full article:** [Read Article 3](03-memory-and-bandwidth.md).

## Part Two: Display Interfaces

### Article 4: SPI / QSPI Displays: From Commands to Partial Updates

**Key question:** How can a low-pin-count serial interface deliver a useful GUI within its bandwidth limit?

**Topics:**

- Display controller, GRAM, initialization commands, and pixel data.
- Address windows, continuous writes, chunking, and partial updates.
- DMA, asynchronous transfer, source lifetimes, and completion.
- Single-line versus multi-line theoretical throughput and overhead.
- Match QSPI display protocols to the MCU's transactions; QuadSPI Flash support alone does not prove display compatibility.

**Deliverable:** A region-update example and full-screen / partial-update throughput comparison.

**Full article:** [Read Article 4](04-spi-qspi-display.md).

### Article 5: 8080 / DBI Parallel Displays with FlexIO and Other Resources

**Key question:** How can a supported platform transfer pixels to a common MCU-style parallel display?

**Topics:**

- 8080-style DBI timing, command/data selection, and read/write cycles.
- Bus width, pin count, and pixel format.
- Evaluate dedicated interfaces or resources such as FlexIO on the actual device.
- Use DMA to reduce per-pixel CPU work.
- Compare SPI and parallel designs for pins, efficiency, and software complexity.

**Deliverable:** Timing documentation and equivalent-workload comparisons.

### Article 6: RGB Displays: Pixel Clock and Continuous Scanout

**Key question:** Why does an RGB display normally need a continuous MCU pixel stream?

**Topics:**

- PCLK, HSYNC, VSYNC, DE, and active regions.
- Front/back porches, sync widths, and frame timing.
- RGB bit mapping, formats, and signal polarities.
- Frame reads, display FIFOs, and insufficient pixel supply.
- Investigation of incorrect colors, offsets, jitter, and corrupted images.

**Deliverable:** Panel-to-controller parameter mapping and a color-bar example.

### Article 7: MIPI DSI Displays: The High-Speed Serial Link

**Key question:** Where does DSI configuration complexity come from?

**Topics:**

- Pixel source, DSI Host, PHY, and panel.
- Lanes, formats, link rate, and panel constraints.
- Command versus video mode.
- Panel initialization versus video timing.
- Confirm Host, PHY, driver, and mode compatibility on the selected device.

**Deliverable:** Link diagram, configuration checklist, and layered troubleshooting.

### Article 8: A Reusable Display Bring-Up and Troubleshooting Process

**Key question:** How can you investigate a dark or incorrect display without blindly changing parameters?

**Topics:**

- Check power, reset, backlight, initialization, timing, and pixels in order.
- Solid colors, color bars, checkerboards, and moving patterns.
- Evidence from oscilloscopes, logic analyzers, and software logs.
- Separate wiring, timing, format, buffering, and cache issues.
- Record symptoms, conditions, investigation, and fixes.

**Deliverable:** A reusable bring-up checklist.

> Extension topic: LVDS or HDMI through external bridges. Clearly distinguish native device interfaces from bridge capabilities.

## Part Three: i.MX RT Display Peripherals and Data Paths

### Article 9: How Do LCDIF / eLCDIF Display Controllers Work?

**Key question:** How does a stored frame become the panel's pixel timing?

**Topics:**

- Frame address, format, stride, and scan order.
- Timing, FIFO behavior, interrupts, and errors.
- When address updates take effect and old buffers become reusable.
- Display behavior under memory contention.
- Common principles and differences across controller versions.

**Deliverable:** A complete memory-read-to-pixel-output path.

### Article 10: Why Does GUI Performance Depend on Memory?

**Key question:** Why can a GUI fail or run slowly even when the nominal capacity is sufficient?

**Topics:**

- On-chip RAM, external SDRAM / PSRAM, and Flash.
- Placement of frames, draw buffers, images, fonts, and decoder caches.
- Verify memory reachability for the display controller, DMA, PXP, and GPU.
- CPU, scanout, and accelerator contention.
- Linker layout and actual access paths, not capacity alone.

**Deliverable:** A GUI memory map and module-to-memory access table.

### Article 11: Single/Double Buffering and Tearing

**Key question:** Why does another buffer not automatically eliminate tearing?

**Topics:**

- Buffer count and refresh strategy are separate choices.
- Front scanout, back rendering, swaps, and ownership.
- VSYNC / frame-boundary synchronization for continuous scanout.
- TE synchronization for GRAM-based displays.
- Capacity, throughput, latency, and image-integrity trade-offs.

**Deliverable:** Buffer timing diagrams and reproducible tearing comparisons.

### Article 12: Cache, MPU, and DMA Coherency

**Key question:** Why can a peripheral see old pixels after the CPU has changed them?

**Topics:**

- Visibility between CPU cache and peripheral memory access.
- Clean, Invalidate, barriers, and cache-line alignment.
- CPU-write/device-read versus device-write/CPU-read synchronization.
- Avoid shared cache-line damage, stale writeback, and incorrect maintenance ranges.
- Cached versus uncached buffers.

**Deliverable:** Synchronization timelines for representative data flows and a stale-image fix.

## Part Four: PXP and GPU Acceleration

### Article 13: PXP Capabilities and Limits

**Key question:** Which pixel-processing tasks should use PXP?

**Topics:**

- Inputs, outputs, layers, and destination buffers.
- Verify conversion, blending, scaling, and rotation for the actual IP.
- Format, size, alignment, and operation-combination restrictions.
- PXP versus the CPU and display controller.
- Do not treat PXP as a general GPU or GUI framework.

**Deliverable:** The selected platform's PXP capability and restriction list.

### Article 14: PXP in Practice: From One Operation to an Asynchronous Pipeline

**Key question:** How do you reliably integrate hardware processing into display updates?

**Topics:**

- Independent examples for a few representative operations.
- Inputs, outputs, completion interrupts, and errors.
- Buffer lifetimes and CPU/PXP handoffs.
- Compare output correctness before measuring end-to-end time.
- Synchronous waiting versus asynchronous pipelines.

**Deliverable:** Verifiable examples and measurement records.

### Article 15: GPU and VG-Lite Basics [Supported Devices]

**Key question:** How does a 2D GPU change graphics execution?

**Topics:**

- Pixel processing, image operations, and path drawing.
- Supported transforms, blending, and drawing.
- VG-Lite software layers.
- Submission, execution, waiting, and cache maintenance.
- Do not generalize one GPU or driver version to the entire family.

**Deliverable:** Minimal rendering flow and a CPU/driver/GPU/memory diagram.

### Article 16: Choosing CPU, PXP, or GPU

**Key question:** When does acceleration help, and when does its overhead dominate?

**Topics:**

- Equivalent inputs, outputs, and quality on supported platforms.
- Small-region versus large-area workloads.
- Submission, cache maintenance, movement, and synchronization costs.
- Individual-operation time, CPU availability, and full-update time.
- Mark unsupported operations as not applicable rather than comparing inequivalent results.

**Deliverable:** A workload-based execution-backend decision table.

## Part Five: Porting and Understanding LVGL

### Article 17: A Minimal LVGL Port with Software Rendering

**Key question:** How do you establish a correct baseline without hardware acceleration?

**Topics:**

- Fix board, display, SDK, and LVGL major version.
- Timebase, task handling, and display integration.
- Draw buffers and target format.
- Correct synchronous or asynchronous flush completion.
- Solid colors, text, images, and basic animation.

**Deliverable:** A minimal working port and interface-responsibility table.

### Article 18: LVGL Refresh and Rendering

**Key question:** Why does LVGL redraw only some regions, and how does it submit the result?

**Topics:**

- Object changes, invalidation, and draw tasks.
- Sharing draw buffers with display frame buffers.
- Partial, direct, and full modes in the selected LVGL version.
- Two small draw buffers versus two complete display frames.
- Conditions for rendering/transfer overlap.

**Deliverable:** Buffer strategies and refresh timelines for different architectures.

### Article 19: Connecting LVGL to PXP / GPU

**Key question:** How do you prove that compiled-in acceleration actually executes?

**Topics:**

- LVGL, SDK, and backend compatibility.
- Dispatch, capability checks, and software fallback.
- Format, location, alignment, and transparency constraints.
- Completion events, threading, and buffer reuse.
- Logs, timing, or execution-path evidence.

**Deliverable:** Integration checklist and software/hardware execution comparisons.

### Article 20: Touch, RTOS, and Thread Safety

**Key question:** How can input, application tasks, and GUI updates cooperate reliably?

**Topics:**

- Sampling, calibration, and rotation mapping.
- LVGL tasks, input devices, and updates from other tasks.
- Version-appropriate serialized access and synchronization.
- Interrupt notifications, flush completion, and task waits.
- Input-to-visible-update measurements.

**Deliverable:** Task/interrupt interaction diagram and latency analysis.

### Article 21: Engineering Images, Fonts, and Chinese Interfaces

**Key question:** How can resource-rich interfaces control capacity, loading time, and runtime memory?

**Topics:**

- Image formats, transparency, decoding, and caching.
- Chinese font subsetting, organization, and character coverage.
- External Flash, filesystems, and runtime buffers.
- Resource lifetimes, widget reuse, and dynamic objects.
- Quality, package size, memory, and startup trade-offs.

**Deliverable:** Resource organization and capacity/runtime-memory budgets.

## Part Six: Measurement and a Complete Project

### Article 22: Trustworthy GUI Performance Testing

**Key question:** How do you produce explainable, reproducible, comparable results?

**Topics:**

- Rendering, transfer, waiting, swapping, and whole-frame boundaries.
- GUI update rate, visible updates, panel refresh, and throughput.
- CPU utilization, peak memory, and input latency.
- Fixed resolution, format, clocks, buffers, and scenes.
- GPU submission versus actual execution completion.

**Deliverable:** Standard testing procedure and reusable result records.

### Article 23: Optimize the Bottleneck, Not the Acceleration Checkbox

**Key question:** Which part of the chain is worth optimizing?

**Topics:**

- Interface, rendering, memory, and synchronization bottlenecks.
- Invalidated regions, translucent layers, animation, and resources.
- Buffer layouts and pipelines.
- Cases where acceleration adds bandwidth pressure or waiting.
- Before/after evidence, costs, and applicable conditions.

**Deliverable:** Complete symptom → evidence → change → retest cases.

### Article 24: A Deliverable i.MX RT GUI

**Key question:** How do the layers combine into a stable, maintainable application?

**Topics:**

- A dashboard, industrial panel, or appliance interface.
- Touch, animation, Chinese fonts, and application data.
- Software baseline versus applicable acceleration.
- Memory boundaries, errors, long-running behavior, and recovery.
- Review display, chip, memory, and architecture choices.

**Deliverable:** A complete project with platform details, measurements, and known limitations.

## IV. A Shared Experimental Progression

### 4.1 Fixed Scenes, Increasing Complexity

| Stage | Scene | Main observations |
| --- | --- | --- |
| 1 | Solid colors and color bars | Wiring, timing, format |
| 2 | Image display and copies | Placement, transfer efficiency, DMA |
| 3 | Partial updates | Invalidation, address windows, benefits |
| 4 | Transparent blending | Pixel traffic, PXP / GPU applicability |
| 5 | Scaling and rotation | Backend capability, quality, alignment, throughput |
| 6 | Animated dashboard | Overall frame rate, latency, CPU and memory pressure |

Not every platform must execute every hardware path. Mark missing capabilities explicitly instead of substituting incomparable workloads.

### 4.2 Fixed Measurement Records

| Category | Minimum information |
| --- | --- |
| Hardware | Complete device model, board revision, panel, interface, resolution |
| Software | SDK, LVGL, compiler, optimization settings |
| Clocks | CPU, memory, display, relevant accelerators |
| Memory | Resource/buffer locations, cache/MPU attributes, alignment |
| Display | Format, stride, mode, buffer count, synchronization |
| Workload | Scene, update area, animation parameters, backend |
| Results | Rendering, transfer, total time, CPU, peak memory, latency |
| Method | Timing boundaries, duration, repetitions, statistics, errors |

Mark unmeasured values as "Not measured." Do not replace them with theoretical values or measurements from another platform.

### 4.3 Fixed Troubleshooting Method

```text
Confirm the symptom
         |
         v
Reduce to a minimal reproducible scene
         |
         v
Collect evidence along the data path
         |
         v
Change only settings related to the hypothesis
         |
         v
Validate correctness, then compare performance
         |
         v
Record the conclusion and applicable conditions
```

## V. Suggested Article Structure

Not every article needs code. Conceptual articles emphasize system relationships; practical articles identify platform and reproduction conditions.

```markdown
# Article N: Title

## Problem and goal
## Platforms, versions, and prerequisites
## Principles and data path
## Configuration and implementation (practical articles)
## Validation and results
## Common problems and investigation
## Summary and next article
## References
```

Three writing principles:

- **Explain responsibilities before registers or APIs.**
- **Establish correctness before optimizing.**
- **Present evidence before performance conclusions.**

## VI. Reference Policy

Use the target device's datasheet, reference manual, and errata for hardware capabilities. Use documentation matching the actual SDK and LVGL versions for APIs.

Starting points:

- [NXP i.MX RT1060 product page](https://www.nxp.com/products/i.MX-RT1060)
- [NXP i.MX RT1170 product page](https://www.nxp.com/products/i.MX-RT1170)
- [LVGL 9.2 display interface](https://docs.lvgl.io/9.2/porting/display.html)

The LVGL link is an explicitly versioned reference, not a commitment that all later series code will use that version.
