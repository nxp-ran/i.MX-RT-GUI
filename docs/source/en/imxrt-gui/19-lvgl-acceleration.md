# Article 19: Connecting LVGL to PXP / GPU

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [LVGL Refresh and Rendering](18-lvgl-refresh.md)
>
> Next: [Touch, RTOS, and Thread Safety](20-touch-rtos.md)
>
> Goal: Validate LVGL 9.2.0 integration and dispatch. Enabled macros or simulation do not prove hardware acceleration.

## 1. Six Conditions

```text
Hardware -> SDK initialization -> Backend compatibility
   -> Memory/format/alignment -> Accepted tasks -> Correct synchronization
```

Keep a software baseline and comparable scenes.

## 2. Exact Configuration Names

LVGL 9.2.0 has:

| Setting | Path |
| --- | --- |
| `LV_USE_DRAW_PXP` | `src/draw/nxp/pxp` |
| `LV_USE_DRAW_VGLITE` | `src/draw/nxp/vglite` |
| `LV_USE_DRAW_VG_LITE` | `src/draw/vg_lite` |

The GPU settings are not aliases. Match initialization, threads, driver, and features to the SDK integration.

Select the appropriate GPU path rather than blindly enabling both. Keep a compatible software path.

## 3. Platform Resources

Check clocks, power, resets, memory, drivers, interrupts, OSAL, allocators, cache, and completion.

PXP interrupt priorities must respect RTOS restrictions. GPUs can require dedicated workspaces/platform setup.

Linking draw source files alone does not satisfy these conditions.

## 4. Evaluation and Fallback

PXP 9.2.0 accepts selected fills/images/layers; radius, gradients, and some transform/Alpha combinations may remain software.

VG-Lite also checks formats, chip features, and task types.

| Situation | Handling |
| --- | --- |
| Unsupported task | Another capable backend |
| Invalid memory/driver setup | Explicit error and correction |
| Runtime hardware failure | Recovery of state/result |

Capability fallback is not silent failure handling. Runtime failure can leave partial output.

## 5. More Than Base Alignment

Verify image addresses/strides, temporary layers, clips, transformed dimensions, formats, and cache boundaries.

Some PXP 9.2.0 transforms require dimensions divisible by 16. This is a particular backend restriction, not every task or PXP IP.

Padding resources must preserve logical size, coordinates, and Alpha edges.

## 6. Prove Dispatch

Collect:

1. Initialization/accepted-task counters.
2. Accepted/rejected types and reasons.
3. Hardware starts/completions.
4. Software fallback counts.
5. Complete time and CPU utilization.

Internal IDs/scores are version-specific, not product constants.

Start with confirmed plain fills or compatible images before complex styling.

## 7. Dependencies and Completion

CPU and GPU tasks can share layers. Framework/adapters must preserve dependencies and visibility.

Do not independently queue application GPU work on LVGL-owned resources without coordination.

Backend completion, flush, and scanout are separate. Submission-call timing is not execution timing.

## 8. Acceptance

| Item | Evidence |
| --- | --- |
| Versions | SDK, LVGL, driver, chip |
| Setup | Clocks, workspace, interrupts |
| Coverage | Types/fallback ratio |
| Correctness | Images, Alpha, bounds, transforms |
| Lifetime | CPU/backend/display handoff |
| Performance | Frame time, CPU, RAM, latency |
| Faults | Timeout/partial-output recovery |

Retain unmeasured items and disclose quality differences.

## 9. Summary

Acceleration needs compatible versions, resources, task coverage, and synchronization.

Next: [Touch, RTOS, and Thread Safety](20-touch-rtos.md).

## References

- [LVGL 9.2.0 settings](https://github.com/lvgl/lvgl/blob/v9.2.0/lv_conf_template.h)
- [PXP evaluation/execution](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/pxp/lv_draw_pxp.c)
- [NXP VG-Lite](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/vglite/lv_draw_vglite.c)
- [Generic VG-Lite](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/vg_lite/lv_draw_vg_lite.c)
