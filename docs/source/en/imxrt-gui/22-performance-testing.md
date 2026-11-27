# Article 22: Trustworthy GUI Performance Testing

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Engineering Images, Fonts, and Chinese Interfaces](21-images-fonts.md)
>
> Next: [Optimize the Bottleneck, Not the Acceleration Checkbox](23-bottleneck-optimization.md)
>
> Goal: Define reproducible boundaries/statistics. Script data are synthetic, not board measurements.

## 1. Define a Frame

Requests, draw tasks, flush chunks, and scans differ.

| Metric | Definition |
| --- | --- |
| Panel refresh | Scan period |
| GUI throughput | Completed effective updates |
| Visible new frames | Distinct presented images |
| Input latency | Event-to-visible target region |
| CPU utilization | Window and method |

Chunks are not full frames; repeating old content is not new presentation.

## 2. Fix the Workload

Record dimensions, formats, stride, modes, scene, assets, versions, clocks, cache, placement, application load, filtering, and Alpha.

Different shadow/filter quality is not an equivalent acceleration comparison.

## 3. Time the Critical Path

```text
Input -> Event -> Draw submission -> Execution complete
   -> Display submission -> Activation -> Scanout/panel response
```

GPU API returns may only indicate queueing.

Do not sum overlapped durations as latency. Correlate events by request identity.

## 4. Clocks and Measurement Cost

Use suitable timers, cycle counters, or GPIO.

Check wraparound, frequency changes, sleep behavior, atomic reads, units, and instrumentation cost.

CPU cycles divided by frequency are not automatically wall time including sleep/device waits.

## 5. Report Distributions

Include samples, duration, mean, median, quantiles, maximum, missed deadlines, drops/repeats, errors, and recovery.

Specify the quantile method. Small-sample p95 near the maximum does not fully characterize long tails.

## 6. Synthetic Statistics

Nearest-rank percentiles are applied to completed-update intervals:

```python
from math import ceil
from statistics import mean, median

intervals_ms = [16, 17, 16, 20, 18, 16, 17, 25, 16, 19]
if not intervals_ms or any(value <= 0 for value in intervals_ms):
    raise ValueError("Completed-update intervals must be positive.")

ordered = sorted(intervals_ms)
p95 = ordered[ceil(0.95 * len(ordered)) - 1]
deadline = 1000 / 60
misses = sum(value > deadline for value in intervals_ms)
rate = len(intervals_ms) * 1000 / sum(intervals_ms)

print(f"Samples: {len(intervals_ms)}")
print(f"Mean/median: {mean(intervals_ms):.2f}/{median(intervals_ms):.2f} ms")
print(f"p95/max: {p95:.2f}/{max(intervals_ms):.2f} ms")
print(f"Completed-update rate: {rate:.2f}/s")
print(f"Intervals above 60 Hz budget: {misses}/{len(intervals_ms)}")
```

Output:

```text
Samples: 10
Mean/median: 18.00/17.00 ms
p95/max: 25.00/25.00 ms
Completed-update rate: 55.56/s
Intervals above 60 Hz budget: 6/10
```

Individual draw durations are not completed intervals and cannot establish visible FPS using this formula.

## 7. CPU, Memory, Bandwidth

| Metric | Method |
| --- | --- |
| CPU busy time | RTOS statistics/explainable sampling |
| Heap/stack peak | Worst scene and allocator statistics |
| Link throughput | Effective bytes/defined time |
| Memory pressure | Counters, errors, controlled loads |
| Waiting | Submission/completion timeline |

LVGL monitors have their own scope, not necessarily total CPU or visible frames.

CPU wait time does not prove accelerator idleness.

## 8. Result Table

| Scene | Software | Hardware | Record |
| --- | --- | --- | --- |
| Small region | Unmeasured | Unmeasured/not applicable | Area/format |
| Full animation | Unmeasured | Unmeasured/not applicable | Distribution/errors |
| Blending | Unmeasured | Unmeasured/not applicable | Quality/bandwidth |
| Application load | Unmeasured | Unmeasured/not applicable | CPU/latency/RAM |

Test cold/warm caches, startup, transitions, and steady state, not only favorable cases.

## 9. Summary

Define metrics, fix workloads, measure boundaries, and report distributions. Throughput, response, and resources differ.

Next: [Optimize the Bottleneck, Not the Acceleration Checkbox](23-bottleneck-optimization.md).

## References

- [LVGL 9.2 display/events](https://docs.lvgl.io/9.2/porting/display.html)
- [LVGL 9.2.0 refresh](https://github.com/lvgl/lvgl/blob/v9.2.0/src/core/lv_refr.c)
- [LVGL 9.2.0 monitor settings](https://github.com/lvgl/lvgl/blob/v9.2.0/lv_conf_template.h)
