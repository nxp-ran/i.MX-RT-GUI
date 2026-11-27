# Article 16: Choosing CPU, PXP, or GPU

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [GPU and VG-Lite Basics](15-gpu-vglite.md)
>
> Next: [A Minimal LVGL Port with Software Rendering](17-lvgl-minimal-port.md)
>
> Goal: Compare equivalent semantics, total time, and resources. Timing parameters are mathematical assumptions, not chip results.

## 1. Capability Before Speed

Use:

```text
Operation/quality
  -> Hardware/driver/backend support
  -> Memory/lifetime feasibility
  -> Correct output
  -> End-to-end comparison
```

Mark unsupported work as not applicable. Approximate output is not automatically equivalent.

Software remains a baseline and a path for unsupported tasks.

## 2. Compare Complete Costs

| Cost | CPU | Hardware |
| --- | --- | --- |
| Pixels | Software | Engine |
| Setup | Often lower | Driver/descriptors/registers |
| Cache | Direction-dependent | More handoffs possible |
| Movement | May exist | Added for incompatible formats/addresses |
| Waiting | Software execution | Tasks/events/synchronization |
| Display | Still required | Downstream limits remain |

Start-to-IRQ timing omits preparation and handoff.

## 3. A Simplified Crossover

Assume CPU 40 ns/pixel, hardware 8 ns/pixel, and setup 80 us:

```text
T_cpu(N) = 40 × N ns
T_hw(N) = 80,000 + 8 × N ns
Break-even N = 80,000 / (40 - 8) = 2,500 pixels
```

Small work can favor the CPU; larger work can favor hardware.

This is not a measurement:

```python
cpu_ns = 40
hardware_ns = 8
setup_us = 80
crossing = setup_us * 1000 / (cpu_ns - hardware_ns)

print(f"Break-even: {crossing:.0f} pixels")
for side in (20, 100):
    pixels = side * side
    cpu_us = pixels * cpu_ns / 1000
    hardware_us = setup_us + pixels * hardware_ns / 1000
    print(f"{side}x{side}: CPU {cpu_us:.1f} us, hardware {hardware_us:.1f} us")
```

Output:

```text
Break-even: 2500 pixels
20x20: CPU 16.0 us, hardware 83.2 us
100x100: CPU 400.0 us, hardware 160.0 us
```

Real caches, contention, batching, and waits are not necessarily linear. Do not use 2,500 as an unmeasured production threshold.

## 4. Initial Backend Decisions

| Work | Candidate | Verify |
| --- | --- | --- |
| Small fill | CPU/integrated engine | Fixed cost |
| Large conversion | PXP/pixel engine | Formats, bandwidth |
| Rotate/scale | Supported PXP/GPU | Angle, size, filtering |
| Paths/complex shapes | GPU/software | Geometry and quality |
| Incompatible tasks | Software | Correct fallback and cost |

Normal capability-based fallback is different from silently ignoring hardware failure.

A failed engine may have partially modified the destination. Software cannot blindly continue from that state.

## 5. Equal Pixels, Different Traffic

Fill writes; copy reads and writes; blending also reads background.

Fix:

- Formats, placement, strides.
- Alpha and color semantics.
- Transform/filter.
- Memory, cache, clocks.
- Included decoding/copies/display synchronization.

Faster GPU computation can still worsen memory contention with scanout.

## 6. Throughput Versus CPU Availability

Hardware may free CPU time without increasing FPS. Busy-waiting may retain high CPU utilization.

Report:

| Metric | Purpose |
| --- | --- |
| Engine/total time | Throughput |
| CPU busy time | System headroom |
| Peak RAM | Capacity cost |
| Input latency | Interaction |
| Correctness/errors | Reliability |

One metric cannot prove universal superiority.

## 7. Experiments and Decisions

Establish independent-operation baselines, then compare identical GUI scenes.

Use small/medium/large regions, Alpha variations, cold/warm resources, and application load. Report distributions and errors, not only the fastest sample.

Unsupported backends are not applicable. Board results remain unmeasured until tested.

## 8. Summary

Correctness, setup, pixel cost, memory contention, and product goals determine the backend.

Next: [A Minimal LVGL Port with Software Rendering](17-lvgl-minimal-port.md).

## References

- [LVGL 9.2.0 PXP evaluation](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/nxp/pxp/lv_draw_pxp.c)
- [LVGL 9.2.0 VG-Lite execution](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/vg_lite/lv_draw_vg_lite.c)
