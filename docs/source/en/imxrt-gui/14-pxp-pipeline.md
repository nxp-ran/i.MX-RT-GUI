# Article 14: PXP in Practice: From One Operation to an Asynchronous Pipeline

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [PXP Capabilities and Limits](13-pxp-capabilities.md)
>
> Next: [GPU and VG-Lite Basics](15-gpu-vglite.md)
>
> Goal: Validate processing, completion, and display handoff. The workflow and reference model are not claimed board measurements.

## 1. Validate Processing Without the GUI

Start with fixed inputs and a separate output, not three unknown layers at once.

```text
Prepare -> Validate -> Maintain cache -> Start
   -> Wait for completion/error -> Check output -> Submit for display
```

Begin with copy and fixed blending, then transforms. Preserve inputs, settings, results, and errors.

## 2. A Synchronous Baseline Needs Cleanup

When using SDK initialization/configuration/start:

- Clear stale completion and prepare request identity.
- Check APIs that return status.
- Watch errors alongside completion.
- Bound waits with timeouts.
- On timeout, stop/reset, confirm access termination, then release.

Do not wait forever on one completion bit or treat AXI errors as success.

Examples illustrate paths; products need recovery and ownership.

## 3. Independent Pixel Acceptance

| Operation | Check |
| --- | --- |
| Copy | Active contents, padding, boundaries |
| Conversion | Channels and quantization |
| Blending | Alpha endpoints/intermediate/background |
| Rotation | Coordinates, dimensions, pitch |
| Scaling | Edges, sampling, tolerances |

Controlled guards can expose overruns, but avoid unrelated data in maintained boundary lines.

CPU checks require hardware-write completion and visibility first.

## 4. Offline Blending Reference

This blends stored eight-bit straight-Alpha channels and quantizes to RGB565. It does not emulate particular PXP rounding, premultiplication, or CSC.

```python
foreground = (255, 0, 0)
background = (0, 0, 255)

for alpha in (0, 128, 255):
    blended = tuple(
        (fg * alpha + bg * (255 - alpha) + 127) // 255
        for fg, bg in zip(foreground, background)
    )
    r, g, b = blended
    rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    print(f"alpha={alpha}: RGB={blended}, RGB565=0x{rgb565:04X}")
```

Output:

```text
alpha=0: RGB=(0, 0, 255), RGB565=0x001F
alpha=128: RGB=(128, 0, 127), RGB565=0x800F
alpha=255: RGB=(255, 0, 0), RGB565=0xF800
```

Match Alpha mode, ordering, rounding, and output before hardware comparison. Premultiplied input needs a different interpretation.

## 5. Asynchrony Is Not Deleting the Wait

Retain request state:

| State | Owner | Permitted work |
| --- | --- | --- |
| FREE | Allocator | Prepare next request |
| CONFIGURING | Submitter | Configure inputs/output |
| RUNNING | PXP | CPU leaves buffers unchanged |
| COMPLETE | Completion task | Establish visibility |
| DISPLAY_OWNED | Display | Wait for consumer release |
| FAILED | Recovery task | Abort and redraw explicitly |

PXP completion releases its ownership, not scanout.

Sources can be reused when reads stop. Outputs wait for all downstream consumers.

## 6. Interrupts Convey Actual State

Read completion/errors, acknowledge correctly, and notify the owner.

IDs, queues, and events need synchronization. `volatile bool` is not a safe multitask queue.

Tasks handle cache, state transitions, display submission, and recovery. Avoid expensive checks or unbounded ISR waits.

Stale events after reset must not complete the next request; use state/generation checks.

## 7. Double-Frame Pipelining

```text
Display: Scan A ---------------- Scan B
PXP:     Process B -> ready      Process A
Owner:                Submit B, wait for A release
```

PXP cannot write A while scanout owns it.

Regional-transfer displays have different release semantics. Use the actual contract, not a generic VSYNC label.

LVGL 9.2.0's `lv_pxp_run()` wrapper runs and waits. Its name does not prove immediate return.

## 8. Measurement Boundaries

Separate configuration, cache, processing, waiting, display handoff, and total updates.

| Metric | Question |
| --- | --- |
| PXP execution | Hardware speed |
| CPU busy time | Freed CPU resources |
| Request-to-reuse | Buffer occupancy |
| Input-to-visible | User delay |

Keep scene, format, quality, and presentation policy equivalent for comparisons.

## 9. Summary

Reliable PXP integration covers submission, execution, completion, presentation, and release, not only one successful image.

Next: [GPU and VG-Lite Basics](15-gpu-vglite.md).

## References

- [NXP PXP API/status](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/pxp/fsl_pxp.h)
- [NXP rotation/display handoff](https://github.com/nxp-mcuxpresso/mcuxsdk-examples/blob/cc8974f843f496ac0ec959c55164766fd0d489bd/driver_examples/pxp/rotate/pxp_rotate.c)
- [LVGL 9.2.0 PXP wrapper](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/pxp/lv_pxp_cfg.c)
