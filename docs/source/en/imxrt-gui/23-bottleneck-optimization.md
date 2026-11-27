# Article 23: Optimize the Bottleneck, Not the Acceleration Checkbox

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Trustworthy GUI Performance Testing](22-performance-testing.md)
>
> Next: [A Deliverable i.MX RT GUI](24-complete-gui-case.md)
>
> Goal: Optimize from evidence without sacrificing quality, latency, or reliability. Cases are hypothetical, not board results.

## 1. Draw the Timeline

Connect events, rendering, transfer, waits, and scanout:

```text
CPU work       ------
Accelerator         --------
Transfer                     ------------
Display wait                              ----
```

Use measured durations. Frequency, GPU names, and theoretical bandwidth do not identify the present bottleneck.

Observe overlap, queues, loading, and errors.

## 2. Four Bottlenecks

| Type | Evidence | Options |
| --- | --- | --- |
| Rendering | Execution dominates | Less work, compatible hardware, assets |
| Interface | Near effective link capacity | Areas, chunking, suitable interface |
| Memory | Load-dependent stalls/underrun | Layout, copies, layers, contention |
| Scheduling | Short execution, long queues | Notifications, locks, frame policy |

Bottlenecks coexist and change after optimization.

## 3. Case One: SPI Full-Screen Traffic

**Symptom:** Faster CPU fills do not significantly improve updates.

**Evidence:** Transfer dominates and matches measured payload throughput.

**Change:**

- Avoid unnecessary full-screen updates.
- Remove per-pixel gaps using validated DMA.
- Tune chunks/setup.
- Reconsider the interface for genuinely full-screen animation.

**Retest:** Equivalent scene/quality, bytes, total time, CPU, tearing, tails.

Theoretical 320 × 240 RGB565 at single-line 40 MHz already needs 30.72 ms. CPU optimization cannot remove that payload.

## 4. Case Two: Transparent Memory Pressure

**Symptom:** More CPU headroom with GPU, but multilayer animation underruns.

**Evidence:** Errors correlate with layers and shared-bus load.

**Change:**

- Limit Alpha to necessary regions.
- Remove redundant full-frame copies.
- Compare precomposition versus scan-time traffic.
- Place resources/output according to viable access paths.

**Retest:** Same Alpha/filter semantics, errors, latency, edges, and application load.

Making transparent content opaque is not equivalent acceleration.

## 5. Case Three: Scheduling Dominates Response

**Symptom:** Fast rendering/output but poor touch response.

**Evidence:** Input queues, lock waits, or delayed GUI processing.

**Change:**

- One GUI owner.
- Latest snapshots for mergeable values.
- Avoid needless I/O/decode under locks.
- Completion notifications instead of long fixed delays.
- Preserve non-droppable discrete events.

**Retest:** Latency distribution, event loss, lifetimes, application deadlines.

Priority changes can move the problem into networking/control.

## 6. Optimization Order

1. Remove unnecessary work.
2. Remove duplicate copies/invalidations.
3. Improve scheduling/buffers.
4. Use compatible hardware.
5. Optimize remaining hot instructions.

Repeatedly loading one image is often a resource-lifetime issue, not a pixel-instruction issue.

Caches need bounds and invalidation; leaking memory is not optimization.

## 7. Avoid Shortcuts

| Shortcut | Risk |
| --- | --- |
| Premature flush completion | Active-source races |
| Disable errors/assertions | Hidden faults |
| Unverified overclocking | Unsupported operating conditions |

Do not omit cache handoffs or overwrite scanning frames to reduce waits.

## 8. Before/After Records

| Item | Record on both sides |
| --- | --- |
| Conditions | Versions, clocks, quality, load |
| Correctness | Pixels, bounds, Alpha, errors |
| Throughput | Intervals/distribution |
| Response | Input-to-visible |
| Resources | CPU, heap/stack, buffers |
| Reliability | Queues, timeouts, recovery |

Change one relevant factor, repeat, and retain regressing scenes.

## 9. Summary

Optimize real critical-path cost while preserving behavior and reliability.

Next: [A Deliverable i.MX RT GUI](24-complete-gui-case.md).

## References

- [LVGL 9.2 refresh/waiting](https://docs.lvgl.io/9.2/porting/display.html)
- [NXP LCDIFv2 reads/errors](https://github.com/nxp-mcuxpresso/mcuxsdk-core/blob/19b4cd9c4151edd6165306c82e750b06a9a4c54b/drivers/lcdifv2/fsl_lcdifv2.h)
- [LVGL 9.2.0 draw backend](https://github.com/lvgl/lvgl/blob/v9.2.0/src/draw/vg_lite/lv_draw_vg_lite.c)
