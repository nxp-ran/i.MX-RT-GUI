# Article 13: PXP Capabilities and Limits

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Cache, MPU, and DMA Coherency](12-cache-mpu-dma.md)
>
> Next: [PXP in Practice: From One Operation to an Asynchronous Pipeline](14-pxp-pipeline.md)
>
> Goal: Understand PXP paths and separate hardware, driver, and LVGL capabilities. References use public NXP drivers and LVGL 9.2.0, not one universal i.MX RT IP.

## 1. A Pixel-Processing Pipeline

PXP operates on pixels, not widgets or pages:

```text
Source/background -> Supported conversion, blending, transform -> Destination
```

The CPU configures work; PXP accesses memory; software hands the result downstream.

It is neither scanout nor a replacement for LVGL events, layout, or invalidation.

## 2. Process, Alpha, and Output Surfaces

| Path | Meaning | Verify |
| --- | --- | --- |
| PS / Process Surface | Main image/background path | Format, size, placement, scaling, CSC |
| AS / Alpha Surface | Overlay/blending path | Pixel/global Alpha, color key |
| Output | Result writes | Address, pitch, format, size, reachability |

Path names do not establish arbitrary operation combinations.

Input and output formats differ. An enum is not proof that the target's conditional implementation supports it.

IP versions can change routes, registers, and engines. Use actual diagrams and SDKs.

## 3. Common Workloads

| Need | Potential PXP use | Verify |
| --- | --- | --- |
| Copy | Write another buffer | Pitch, overlap, format |
| Conversion | Produce display-compatible pixels | Source/destination combination, CSC |
| Alpha blending | Foreground over background | Modes and computation |
| Scaling | Resize a supported PS/path | Ratios, filters, boundaries, IP limits |
| Rotation/flip | Orientation | Angles, paths, dimensions |
| Color key/LUT | Specialized processing | Version support |

These are verification categories, not guarantees.

Rounded shapes, arbitrary vector paths, and text layout are not automatically single PXP operations.

## 4. Two Meanings of Support

Hardware can sometimes compose multiple operations, while an LVGL backend rejects the equivalent single task.

LVGL 9.2.0's PXP backend shows:

- Plain rectangle fill without radius or gradient.
- Image/layer format and alignment checks.
- Rotation in 90-degree multiples.
- Rejection of some transform/transparency/recolor combinations.
- Specific transformed-image dimension alignment checks.

These are **backend-version restrictions**, not the complete specifications of all PXP hardware.

Custom two-stage code is not automatically used by LVGL.

## 5. Describe the Whole Operation

| Item | Purpose |
| --- | --- |
| Source/background/destination addresses | Actual reads/writes |
| Formats and ordering | Pixel interpretation |
| Dimensions and pitch | Region and rows |
| Placement and clipping | Coordinates |
| Alpha and CSC | Result semantics |
| Transform parameters | Output size/bounds |
| Cache and ownership | Visibility/lifetime |

Width in pixels is not `pitchBytes`.

Rotation can exchange dimensions and change stride. The destination must fit the transformed layout.

## 6. Do Not Assume In-Place Operation

Hardware access order is not necessarily `memmove`.

Start with non-overlapping buffers unless the target explicitly permits overlap.

Background reads, source reads, and destination writes can overlap in time. Define whether partial output needs old contents.

CPU, GUI, and other DMA must not modify PXP-owned sources.

## 7. Residual Configuration

Previous jobs can leave:

- CSC.
- Alpha/color key.
- Rotation, flip, scaling.
- Routes, clips, formats.

Define a complete state for each job; updating addresses alone is insufficient.

Use SDK reset/configuration while respecting interrupts, clocks, and other owners.

Applications must not independently reset a PXP instance managed by LVGL.

## 8. Independent Platform Tests

| Operation | Pattern | Check |
| --- | --- | --- |
| Copy | Asymmetric corners/rows | Content, pitch, bounds |
| Conversion | RGB intensity steps | Channels, quantization |
| Blending | Fixed foreground/background | Alpha 0, intermediate, 255 |
| Rotation | Asymmetric markers | Direction, dimensions, clipping |
| Scaling | Grid and edges | Ratio, filter, boundaries |

Validate before timing. Define rounding/tolerances for blending and scaling; different filters are not equivalent-quality comparisons.

## 9. Summary

PXP offloads supported pixel work when paths, formats, combinations, sizes, and software agree.

Next: [PXP in Practice: From One Operation to an Asynchronous Pipeline](14-pxp-pipeline.md), focusing on completion and handoff.

## References

- [NXP PXP driver](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/pxp/fsl_pxp.h)
- [NXP PXP rotation example](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/pxp/rotate/pxp_rotate.c)
- [LVGL 9.2.0 PXP selection](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/pxp/lv_draw_pxp.c)
