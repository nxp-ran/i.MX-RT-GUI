# Article 1: What Makes Up an Embedded GUI System?

> Series: [From Lighting Up a Display to a High-Performance GUI: i.MX RT Graphics in Practice](README.md)
>
> Next: [i.MX RT Graphics Capabilities and Platform Selection](02-platform-selection.md)
>
> Goal: Follow a screen update to understand the roles of the panel, display peripherals, rendering units, memory, and LVGL.
>
> Scope: General principles explained in an i.MX RT context. Not every device has the same peripherals. This article does not initialize a specific board; all capacity and bandwidth figures are theoretical calculations, not board measurements.

## 1. Is a GUI Finished Once the Display Lights Up?

An embedded GUI project often starts with a development board and a display.

Connect the cable, download an example, and a picture appears. Run a graphics demo, and buttons, text, and animations start moving. The display system seems complete.

The real questions arise when you build your own interface:

- Why does the existing driver not work with a different display?
- Why do static images look fine while animation becomes sluggish?
- Why is the interface slow despite a high CPU clock?
- Why does tearing remain after enabling double buffering?
- Why does LVGL not become faster when the chip has PXP or a GPU?

These questions have a common explanation: **a GUI is not an isolated module. It is a data path implemented by several cooperating modules.**

Before discussing registers, drivers, and acceleration, distinguish three goals:

| Goal | What it primarily verifies | What it does not establish |
| --- | --- | --- |
| Light up the display | Power, reset, backlight, and necessary initialization or scanout | Correct pixel format and all timing parameters |
| Display an image correctly | Stable delivery of pixels through the display path | Sufficient dynamic-update performance |
| Run an interactive GUI smoothly | Cooperation among rendering, transfer, synchronization, input, and application tasks | Resource headroom and long-term reliability still need validation |

In particular, **a lit backlight does not prove that the display has received a valid image.**

This series follows the progression from the first goal to the third, explaining why each step works.

## 2. The Big Picture: Seven Roles

A typical embedded GUI can be divided into the following roles.

| Role | Main responsibility | Examples |
| --- | --- | --- |
| Application logic | Decide what the interface should express | Temperature values, page changes, alarms |
| GUI framework | Manage objects, layout, styles, events, and refresh | LVGL |
| Rendering execution units | Turn drawing tasks into pixels | CPU software rendering, supported PXP / GPU operations |
| Memory and buffers | Store resources, working data, and pixels | RAM, external memory, draw buffers, frame buffers |
| Display output path | Deliver pixels to the display | SPI, parallel transfers, display controllers, DSI Host |
| Display side | Receive pixels and drive the panel | Display controller, GRAM, panel drive circuitry |
| Input devices | Deliver user actions to software | Touch, buttons, rotary encoders |

The logical relationship looks like this:

```text
Touch / buttons / rotary encoder
             |
             v
Input driver -> GUI events and application logic
                               |
                               v
                       LVGL objects and layout
                               |
                               v
                   Invalidated areas and draw tasks
                               |
                               v
                  CPU software rendering / PXP / GPU
                               |
                               v
                         Pixel buffers
                               |
                               v
                  Display controller / transfer peripheral
                               |
                               v
                    Display-side controller / panel
```

This is not an internal bus diagram. It shows responsibilities, not a requirement for pixels to pass through the CPU, PXP, and GPU in sequence.

Some tasks may run on the CPU while others use hardware. A result may also be rendered into one buffer, converted or copied, and only then submitted to the display path.

**Hardware acceleration is an execution choice, not a mandatory stage in every GUI.**

## 3. How Does a Button Become Pixels?

Suppose the interface contains a button. The application normally asks simple questions:

- Where should it appear?
- What text should it show?
- What colors should it use?
- What should happen when it is pressed?

The display does not understand a "button." It receives pixels, or commands that write pixels.

A conversion must therefore happen between the application and the display.

### 3.1 The GUI Framework Describes What to Draw

LVGL manages the button object, size, position, style, and events.

When its state changes, such as from released to pressed, the framework determines which regions are affected and schedules drawing work.

That work can include:

- Drawing the background and rounded corners.
- Drawing the border.
- Blending a shadow or translucent layer.
- Reading glyphs and drawing text.

One button does not necessarily correspond to one hardware operation or one draw task.

### 3.2 Execution Units Calculate the Pixels

CPU software can perform the work, or a supported portion can be assigned to PXP or a GPU.

Acceleration depends on all of the following:

1. The device contains the required hardware.
2. The hardware supports the operation, format, and parameters.
3. The driver exposes the required capability.
4. The GUI backend can dispatch the task.
5. Memory location, alignment, and synchronization requirements are satisfied.

There is an entire software integration path between "the chip has a GPU" and "the GPU draws this button."

Even when hardware handles pixel operations, the CPU generally still handles events, layout, submission, resource management, and synchronization.

### 3.3 The Display Path Sends the Pixels

Rendered pixels still have to reach the display.

This can mean:

- Writing a small pixel region into display GRAM over SPI.
- Updating a region through a parallel interface.
- Letting a display controller scan a complete frame buffer.
- Sending an image through a display controller and DSI link.

Only at this stage does the work become display output.

> The framework determines the interface, execution units generate pixels, and the display path delivers them to the display. These are different layers.

## 4. Two Typical Display Architectures

Display discussions often start with interface names such as SPI, RGB, and MIPI DSI.

Those names matter, but another question has a major impact on software architecture:

**Can the display side retain an image, or must the MCU continuously supply a pixel stream?**

The following are two common architectures, not an absolute classification of every interface and panel.

### 4.1 Architecture A: The Display Retains the Image

Many SPI and 8080-style displays contain a display controller and GRAM.

GRAM stores the image on the display side. After the MCU writes pixels, the display-side controller reads them and refreshes the panel.

```text
MCU side                              Display side

Draw buffer -> SPI / parallel transfer -> Controller and GRAM -> Panel
```

For a numeric-field update, the MCU can:

1. Set the destination window.
2. Send the pixels for that window.
3. Wait until the transfer path no longer uses the source buffer.
4. Reuse the buffer for the next drawing operation.

If the image does not change, the MCU usually need not resend the entire screen. The display side continues scanning its stored image.

The advantage is that the MCU need not necessarily retain a complete image.

This does not mean "no display memory is needed." The full image may live in display GRAM, while the MCU still needs rendering, decoding, and transfer buffers.

### 4.2 Architecture B: The MCU Retains a Frame for Continuous Scanout

In a common RGB-display design, the complete image resides in an MCU-accessible frame buffer. A display controller continuously reads it and generates pixel timing.

```text
MCU side

CPU / accelerator -> Frame buffer -> Display controller -> RGB -> Panel
```

Some DSI video-mode systems also contain a DSI Host and PHY:

```text
Frame buffer -> Display controller -> DSI Host / PHY -> Panel
```

The output path generally continues running at the panel's required timing even when the image is unchanged.

The GUI can stop redrawing, but the display controller still reads existing pixels.

Two consequences follow:

- Complete frame data must be accessible to the display controller.
- Scanout itself consumes memory and bus bandwidth.

DSI supports command mode, video mode, and different panel implementations. The term "DSI display" alone does not reveal its buffer architecture.

### 4.3 The Key Differences

| Question | Image retained on the display side | Image retained and scanned on the MCU side |
| --- | --- | --- |
| Where is the complete image mainly stored? | Display-controller GRAM | MCU-accessible frame buffer |
| How does the MCU update it? | Write changed regions or the whole screen | Modify frame contents or submit a new buffer |
| What happens with a static image? | MCU pixel transfers can usually stop | Continuous scanout usually remains necessary |
| Main concerns | Interface throughput, window writes, transfer synchronization | Memory bandwidth, scan timing, buffer swaps |
| Can the MCU use only a small draw buffer? | Usually, depending on the driver | Yes, but a complete scanout frame is usually still required |

Architecture comes from the combination of display-side controller, interface mode, MCU display controller, and buffer strategy, not the interface name alone.

## 5. Three Different Meanings of Display Memory

"Buffer," "display memory," and "frame buffer" are often used interchangeably.

This series uses the following distinctions to avoid confusion when integrating LVGL.

### 5.1 Draw Buffer: Where Are Pixels Rendered?

A draw buffer is the destination written by a rendering execution unit.

It may hold the whole screen, a few dozen lines, or a region awaiting processing.

For a tightly packed, 800-pixel-wide RGB565 buffer containing 40 lines:

```text
800 × 40 × 2 = 64,000 B = 62.5 KiB
```

The buffer can be reused for different regions once its previous consumer has stopped accessing it.

### 5.2 Display Frame Buffer: Where Does Scanout Get a Frame?

In a typical continuous-scanout design, a display frame buffer retains an entire image for display.

It must meet the controller's requirements for format, address, stride, alignment, and access permissions.

Draw and display frame buffers can be the same allocation or separate allocations:

```text
Option 1: Direct rendering

Renderer -> Complete frame buffer -> Display controller

Option 2: Partial rendering followed by frame updates

Renderer -> Small draw buffer -> Copy / convert -> Complete frame buffer
                                                        |
                                                        v
                                                 Display controller
```

The second option reduces drawing-workspace capacity. It does not eliminate the complete frame data needed for continuous scanout.

### 5.3 Display GRAM: What Does the Display Retain?

GRAM is on the display side and is normally accessed through command or pixel-write transactions.

It may not support ordinary CPU random access. Do not assume it can be a direct PXP / GPU destination.

Check the data path and addressing model before deciding whether intermediate buffers or copies are necessary.

In short:

> Draw buffers generate pixels, display frame buffers supply scanout, and GRAM retains the image on the display side. They can cooperate, but they are not the same concept.

## 6. A Worked Budget: 800 × 480

Consider why memory often limits GUI performance.

Assume an 800 × 480 image with tightly packed pixels, excluding row alignment, extra layers, and working buffers.

### 6.1 How Large Is One Frame?

```text
Frame size = Width × Height × Bytes per pixel
```

| Format | Bytes per pixel | Bytes per frame | One-frame capacity | Two-frame capacity |
| --- | --- | --- | --- | --- |
| RGB565 | 2 | 768,000 B | 750 KiB | 1,500 KiB |
| RGB888 | 3 | 1,152,000 B | 1,125 KiB | 2,250 KiB |
| ARGB8888 | 4 | 1,536,000 B | 1,500 KiB | 3,000 KiB |

Units used here:

```text
1 KiB = 1,024 B
1 MiB = 1,048,576 B
1 MB  = 1,000,000 B
```

Two complete RGB565 frame buffers already require 1,536,000 B, approximately 1.465 MiB.

That excludes:

- Application data, task stacks, and the heap.
- Images, fonts, and decoding caches.
- Off-screen layers and accelerator workspaces.
- Actual stride, alignment, and format-specific overhead.

In a real project, prefer:

```text
Frame-buffer size = Actual stride in bytes × Height
```

A pixel-format name does not prove that all hardware supports tightly packed storage.

### 6.2 How Much Pixel Data Is Required Per Second?

Assume complete RGB565 scanout 60 times per second:

```text
Active pixel rate = 800 × 480 × 60
                  = 23,040,000 pixel/s

Active pixel data = 800 × 480 × 2 × 60
                  = 46,080,000 B/s
                  = 46.08 MB/s
```

This is an active-image payload estimate, not a complete interface budget or total system memory bandwidth.

In a simplified model where every frame is fully written to external RAM and then fully read by the display controller:

```text
Rendering writes: 46.08 MB/s
Scanout reads:    46.08 MB/s
Combined:         92.16 MB/s
```

Reading image assets, reading the previous background, blending transparency, and copying intermediate buffers increase traffic further.

Budget the interface separately. RGB pixel timing includes blanking, so its clock cannot be calculated from active pixels alone. Blanking time should not automatically be counted as extra active-pixel memory reads either.

For partial updates into display GRAM, the MCU may not need to send 60 complete images per second. Recalculate using the actual updated area.

**Resolution, pixel format, and update strategy determine the baseline workload. CPU frequency is only one condition.**

## 7. Rendering Complete Does Not Mean Visible on the Panel

An asynchronous system has several distinct milestones:

1. Software submits a task.
2. Rendering or pixel processing actually finishes.
3. A downstream consumer releases a source buffer.
4. The new image enters scanout and progressively becomes visible.

These milestones can be separated by substantial time.

### 7.1 Displays with GRAM

A typical sequence is:

```text
Render region -> Start transfer -> Release source buffer -> Scan new GRAM data
```

Starting DMA does not mean the data has been sent. A reusable source buffer does not mean the panel has already scanned the entire new image.

Check the definitions of DMA completion, peripheral FIFO states, and bus completion to determine when source reads stop and when the transaction really ends.

### 7.2 Continuous-Scanout Displays

With two complete display frame buffers, a typical sequence is:

```text
Display controller scans A
        |
        +-> CPU / accelerator generates the next frame in B
                                   |
                                   v
                          Request a switch to B
                                   |
                                   v
                     Switch takes effect at the specified time
                                   |
                                   v
                         Confirm scanout no longer reads A
                                   |
                                   v
                                Reuse A
```

Writing B's address into a register does not necessarily release A immediately.

The swap timing, event definitions, and safe-reuse conditions must come from the target display controller.

### 7.3 Why Does LVGL Need Flush-Completion Notification?

LVGL needs to know when the display driver has completed a buffer handoff so it can proceed according to the selected render mode.

In the LVGL 9.2 display interface, `flush_cb` and `lv_display_flush_ready()` illustrate this division of responsibility. Interpret their semantics together with the chosen mode and port implementation.

Do not report completion immediately after starting an asynchronous transfer. During a frame-buffer swap, do not ignore ongoing scanout reads of the old buffer.

**Completion notification hands over buffer ownership. It does not merely mean "the function returned" or "the whole image is now visible."**

Another important distinction:

> Two small draw buffers can overlap rendering with transfer. Two complete display frame buffers can support front/back buffer swapping. Both are called double buffering, but they serve different purposes and both require correct synchronization.

## 8. One FPS Number Is Not Enough

"How many frames per second does this GUI achieve?" is a common question.

First define which rate is being measured.

### 8.1 Panel Refresh Rate

Panel refresh rate describes the scanout cadence.

A panel scanning at 60 Hz does not imply that the application generates 60 different images per second. It can display the same frame repeatedly.

### 8.2 GUI Update Rate

GUI update rate describes software updates, but the measurement boundary matters:

- Completion of rendering?
- Completion of a set of region submissions?
- Completion of a frame-buffer swap?
- Production of an actually visible new image?

These figures are not interchangeable. Do not count each chunk of a partial refresh as a complete frame.

Likewise, GUI task frequency and timer frequency are not effective update rates.

### 8.3 CPU Utilization

Identical update rates can have very different CPU costs.

CPU pixel processing and hardware-assisted processing may produce similar FPS, while the latter frees CPU time for communication, control, or other tasks.

Conversely, a driver that busy-waits for hardware can retain high CPU utilization even though hardware performs the pixel work.

FPS alone therefore cannot establish the value of acceleration.

### 8.4 Input-to-Display Latency

A touch action passes through input sampling, scheduling, event handling, rendering, transfer or swapping, scanout, and panel response.

The critical path can be summarized as:

```text
Input sampling
   -> GUI scheduling and event handling
   -> Rendering
   -> Transfer / swap and required waits
   -> Scanout reaches the target region
   -> Panel response
```

An interface with a good average frame rate can still feel unresponsive because of queueing, scheduling, or swap policy.

### 8.5 Why Does Pipelining Help?

With serial rendering and transfer, a processing cycle is approximately:

```text
T = T_draw + T_transfer
```

With independent buffers and hardware that supports overlap, ideal steady-state throughput can approach:

```text
T ≈ max(T_draw, T_transfer)
```

This models ideal processing throughput, not visible frame rate.

Memory contention, synchronization, panel refresh, and transfer throughput can impose new limits. Pipelining does not necessarily reduce the latency of a single input event.

A useful performance result should therefore report:

**Update rate, CPU utilization, memory use, and input-to-display latency.**

## 9. How Do PXP, the GPU, and LVGL Relate?

These names frequently appear together in i.MX RT graphics development, but they are not replacements for one another.

### 9.1 PXP: Supported Pixel-Processing Tasks

PXP stands for Pixel Processing Pipeline.

It addresses particular pixel-processing operations. A device or IP version may support some combination of format conversion, blending, scaling, and rotation, subject to format, size, alignment, and operation-combination limits.

Start with the target capability list instead of assuming that PXP performs every 2D drawing operation.

PXP does not manage buttons, pages, events, or layout.

### 9.2 GPU: Graphics Work Supported by Hardware and Drivers

This series focuses on 2D GUI acceleration, not desktop-class graphics.

Some 2D GPUs perform image operations, path drawing, transforms, and blending. Their actual capabilities depend on hardware, drivers, and API versions.

VG-Lite is part of the software API / driver stack, not a hardware peripheral named "VG-Lite."

### 9.3 LVGL: Interface and Drawing Organization

LVGL provides objects, layout, styles, events, and refresh management, then executes work through rendering backends.

It can use software rendering and, with compatible platforms and versions, hardware backends.

A common arrangement assigns supported tasks to hardware and leaves others to software. Evaluate real workloads rather than only checking whether an acceleration macro is enabled.

Remember the relationship this way:

| Component | Main question it answers |
| --- | --- |
| LVGL | What is the interface, and what needs updating? |
| CPU / PXP / GPU | Who executes drawing or pixel-processing tasks? |
| Display controller / transfer interface | How do the resulting pixels reach the display? |

### 9.4 i.MX RT Models Are Not Interchangeable

As public examples, NXP's RT1060 product page lists an LCD controller and 2D acceleration, while the RT1170 page lists a 2D GPU and MIPI CSI / DSI.

These are starting points for understanding platform differences. They do not prove that accelerators in different products are the same IP, or that every other model has the same capability.

Selection still requires the reference manual, package, board connectivity, SDK, and LVGL integration.

The next article builds this capability matrix.

## 10. Following a Touch All the Way to the Screen

Suppose touching a temperature button changes its displayed state.

A typical interaction follows these steps:

1. **Capture input.** The touch controller or driver reports a contact and state.
2. **Handle the event.** The GUI task processes input, and the application changes the object or data.
3. **Identify invalidated areas.** The framework determines where pixels must be regenerated.
4. **Organize draw tasks.** Backgrounds, text, images, and blending operations are scheduled.
5. **Render.** The CPU or a supported hardware backend writes the destination buffer.
6. **Hand over data.** Wait for relevant operations and maintain memory visibility for the actual path.
7. **Submit for display.** Write a region to the display or submit a frame buffer.
8. **Release buffers safely.** Use downstream-consumer state to determine what can be reused.
9. **Scan and respond.** The panel progressively presents the new pixels.

Problems anywhere in this chain can look like an incorrect GUI:

| Symptom | Initial investigation |
| --- | --- |
| Long delay after touch | Sampling, scheduling, queueing, rendering, swap waits |
| Old content remains in some regions | Invalidation, cache visibility, update area, buffer handoff |
| A horizontal split appears during animation | Scan/write conflict, swap timing, GRAM synchronization |
| Large updates stutter | Rendering volume, interface throughput, memory bandwidth, synchronization |
| Intermittent failure after enabling acceleration | Address reachability, format, alignment, cache, asynchronous lifetime |

These are investigation directions, not diagnoses. Trace the data path and collect evidence before concluding.

## 11. First Observation Exercise: Find Where the Pixels Go

Instead of board-specific initialization code, this article offers an observation exercise for an existing display example.

It defines validation methods, not predetermined measurements.

### 11.1 Prepare Three Scenes

| Scene | Action | Main observations |
| --- | --- | --- |
| A | Fixed solid color or color bars | Basic output path, pixel format, stability |
| B | Static GUI page | Whether rendering stops and whether scanout continues |
| C | Change only a small region | Actual render area, transfer area, synchronization |

### 11.2 Answer Six Questions

1. Does the display side have GRAM retaining the image?
2. Where is the draw destination, and is it a full frame or a partial buffer?
3. If a display frame buffer exists, does it share memory with the draw buffer?
4. Who reads and writes the buffers, and can every relevant device access them?
5. Which event tells software that the handoff has completed?
6. What do the CPU, interface, and display controller do when the image is unchanged?

Use the driver, linker layout, chip manual, and panel documentation to answer them.

### 11.3 Collecting Evidence

- Timestamp rendering, transfer start, and completion separately.
- Where practical, mark key intervals with GPIO and observe them with an oscilloscope or logic analyzer.
- Check whether interface output continues with a static image.
- Inspect the backend that actually executes, not merely what was compiled.
- Record render and transfer regions to confirm that partial updates reduce work.

A typical RGB system can keep its pixel clock and scanout running on a static page. A GRAM-based on-demand system can usually stop MCU pixel transfers.

Both behaviors can be correct. Continuous bus activity alone does not prove redundant GUI refresh.

After this exercise, you should be able to draw the real path:

```text
Where are the resources?
         |
         v
Who turns them into pixels?
         |
         v
Which memory receives the pixels?
         |
         v
Who reads that memory next?
         |
         v
Which link delivers them to the display?
         |
         v
Which event permits buffer reuse?
```

## 12. Misconceptions That Distort the Design

| Misconception | More accurate interpretation |
| --- | --- |
| High frequency guarantees a fast GUI | Interface, memory, synchronization, and workload can limit it |
| The display controller draws widgets | It primarily outputs pixels, rather than replacing rendering |
| A GPU accelerates every task | Hardware, driver, backend, and parameters must all match |
| Double buffering guarantees no tearing | Synchronization, swap timing, and ownership must be correct |
| GRAM displays need no memory | The image is retained on the display side, but MCU workspaces remain |
| A returned flush callback permits buffer overwrite | Asynchronous consumers may still be reading |
| A 60 Hz display means GUI output at 60 FPS | It may scan the same frame repeatedly; measurement boundaries differ |
| Cache only affects speed | On non-coherent paths, it changes what the CPU and devices can see |

These are not minor terminology issues. They directly affect capacity, drivers, and performance conclusions.

## 13. Summary: Model the System Before Accelerating It

An embedded GUI can be summarized in three statements:

1. **The application and framework decide what to draw.**
2. **The CPU or hardware backends generate and process pixels.**
3. **The output path delivers pixels and displays them at the correct timing.**

Capacity, bandwidth, data coherency, and buffer ownership connect all three.

Once you know where pixels reside, who accesses them, and when they can be reused, interfaces, controllers, PXP, GPUs, and LVGL become a system that can be understood, validated, and optimized layer by layer.

Next: [i.MX RT Graphics Capabilities and Platform Selection](02-platform-selection.md). We distinguish chip capabilities from what a particular project can actually use.

## References

1. [NXP i.MX RT1060 product page](https://www.nxp.com/products/i.MX-RT1060): Product-level entry point for LCD and 2D acceleration information.
2. [NXP i.MX RT1170 product page](https://www.nxp.com/products/i.MX-RT1170): Product-level entry point for the 2D GPU and MIPI interfaces.
3. [LVGL 9.2: Display interface](https://docs.lvgl.io/9.2/porting/display.html): Draw buffers, render modes, flush callbacks, and completion notification.

The explicitly versioned LVGL reference illustrates responsibilities and lifetimes, not universal API compatibility. Hardware capabilities and synchronization must be verified against the target device, panel, and actual software versions.
