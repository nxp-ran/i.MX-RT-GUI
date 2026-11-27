# Article 15: GPU and VG-Lite Basics [Supported Devices]

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [PXP in Practice](14-pxp-pipeline.md)
>
> Next: [Choosing CPU, PXP, or GPU](16-render-backend-selection.md)
>
> Goal: Understand 2D commands, images, paths, and synchronization using RT1170 capabilities and LVGL 9.2.0 integration. Match APIs to the actual VG-Lite driver.

## 1. Hardware Versus Software

The GPU executes graphics. VG-Lite is the API/driver stack, not another peripheral.

```text
Application/LVGL -> VG-Lite -> Driver/commands -> GPU -> Destination pixels
```

This is 2D GUI work, not desktop 3D graphics.

IP, builds, and drivers affect paths, filtering, formats, and blending.

## 2. Images and Paths

| Input | Description | Work |
| --- | --- | --- |
| Bitmap | Existing pixels/layout | Blit, scaling, rotation, blend |
| Path | Geometry/parameters | Fill, supported strokes |
| Draw target | Output storage | Results, not the panel itself |

Images need reads; paths can require tessellation and workspaces.

Vectors are not free of capacity or traffic. Budget paths, caches, workspaces, and off-screen results.

## 3. Transform, Clip, Blend

Transforms map inputs to targets, clipping limits coverage, and blending defines composition.

Check:

- Origins and transform order.
- Applying rotation twice.
- Clip versus destination coordinates.
- Straight versus premultiplied Alpha.
- Driver output versus consumer interpretation.

Dark transparent edges can be a semantic problem even when the GPU runs.

## 4. Minimal Execution Lifetime

This is a logical workflow, not a board-independent compilable initialization:

```text
Initialize platform/GPU/VG-Lite
   -> Allocate/map target
   -> Prepare image/path
   -> Submit clear/blit/draw
   -> Commit commands
   -> Wait/check execution
   -> CPU check or display submission
   -> Wait for consumers
   -> Release images, paths, workspaces
```

Interfaces such as `vg_lite_flush()` and `vg_lite_finish()` distinguish submission and waiting, subject to the actual version.

API return does not permit immediate source/path/target release.

## 5. Allocation Is Integration

CPU `malloc()` does not establish GPU access.

Verify:

- Driver allocation/mapping.
- Formats, strides, alignment.
- Reachability/capacity.
- Cache/visibility.
- Separate resource lifetimes.

Mapping success does not establish correct dimensions or format. Do not hide descriptor mismatches with unnecessary casts.

## 6. Command Batching

Batching can amortize fixed costs, but increase:

- Commands and retained resources.
- Queueing.
- Input latency.
- Recovery complexity.

Fewer flushes are not the only goal. Preserve dependencies and synchronization.

## 7. Two Similar LVGL Backend Names

LVGL 9.2.0 provides:

| Setting | Path |
| --- | --- |
| `LV_USE_DRAW_VGLITE` | `src/draw/nxp/vglite` |
| `LV_USE_DRAW_VG_LITE` | `src/draw/vg_lite` |

They are not spelling aliases.

Match SDK, IP, initialization, threading, and cache hooks to one backend. Enabling both is not automatically stronger acceleration.

A simulator or another platform's VG-Lite execution is not proof of RT1170 hardware execution.

## 8. Progressive Experiments

| Stage | Work | Acceptance |
| --- | --- | --- |
| Fill | Fixed color | Correct target/bounds |
| Copy | Asymmetric image | Format, stride, placement |
| Transform | Rotate/scale | Direction, filtering, clipping |
| Blend | Alpha endpoints/edges | Background and semantics |
| Commands | Dependent operations | Same result as individual work |
| Display | Present output | Correct lifetime/swap |

Check every status-returning API. Failure stops the success path; release only after access termination.

## 9. Summary

GPU integration encompasses commands, memory, synchronization, and semantics.

Next: [Choosing CPU, PXP, or GPU](16-render-backend-selection.md), comparing equivalent workloads.

## References

- [NXP RT1170 GPU entry point](https://www.nxp.com/products/i.MX-RT1170)
- [LVGL 9.2.0 NXP VG-Lite](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/vglite/lv_draw_vglite.c)
- [LVGL 9.2.0 generic VG-Lite](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/vg_lite/lv_draw_vg_lite.c)
- [LVGL 9.2.0 configuration](https://github.com/lvgl/lvgl/blob/v9.2.0/lv_conf_template.h)
