# Article 20: Touch, RTOS, and Thread Safety

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [Connecting LVGL to PXP / GPU](19-lvgl-acceleration.md)
>
> Next: [Engineering Images, Fonts, and Chinese Interfaces](21-images-fonts.md)
>
> Goal: Coordinate input, application tasks, and LVGL 9.2.0. Coordinates are an illustrative model, not measured calibration.

## 1. Two Update Paths

```text
Touch sampling -> Input state -> LVGL read -> Events -> UI
Business data -> Model -> GUI messages -> UI
```

Both influence objects, but neither permits arbitrary concurrent task/ISR updates.

LVGL is not thread-safe by default. Updates, screens, and resource lifetimes need one owner or consistent locking.

## 2. Input Is State, Not Only Coordinates

Report pressed/released, valid coordinates, update time, and failures separately.

Always report release to avoid stuck controls.

Bus errors are not silently equivalent to no touch. Log and apply defined release/retry/disable policy.

Callbacks need bounded execution, not blocking bus waits or page reconstruction.

## 3. Calibration and Orientation

```text
Raw -> Calibration/range -> Rotation -> Physical/logical mapping -> LVGL
```

Avoid double rotation or missing offsets. Already calibrated pixel coordinates do not need raw-range scaling again.

## 4. Offline Mapping

Assume x=200..3800, y=100..3900, mapped to 800 × 480 then rotated clockwise 90 degrees to 480 × 800.

Integer floor mapping is not a real filter:

```python
def map_touch(raw_x, raw_y):
    if not (200 <= raw_x <= 3800 and 100 <= raw_y <= 3900):
        raise ValueError("Touch sample is outside the assumed calibration range.")
    x = (raw_x - 200) * 799 // 3600
    y = (raw_y - 100) * 479 // 3800
    return 479 - y, x

for point in ((200, 100), (2000, 2000), (3800, 3900)):
    print(f"{point} -> {map_touch(*point)}")
```

Output:

```text
(200, 100) -> (479, 0)
(2000, 2000) -> (240, 399)
(3800, 3900) -> (0, 799)
```

Validate corners, center, edges, and drags. Define noisy-range clipping/rejection rather than hiding calibration faults.

## 5. One GUI Owner

| Context | Work |
| --- | --- |
| Touch ISR | Sampling notification/light records |
| Input task | Read/calibrate/publish state |
| Application | Domain data/messages |
| GUI task | Consume/update/run handler |
| Display ISR | Port-approved completion/notification |

Message payloads need stable lifetimes; do not queue expired stack-string pointers.

Latest snapshots suit continuous values, not necessarily discrete controls. Full queues need backpressure, counters, or explicit rejection.

## 6. Multiple Callers with Locks

Use one consistent mutex policy.

LVGL 9.2 OSAL supplies `lv_lock()` / `lv_unlock()`; configured handlers also lock internally. Avoid different locks and nonrecursive double locking.

Events/timers already execute in the processing context. Do not hold a lock while waiting for work only the blocked GUI task can complete.

Locks do not establish DMA/cache coherency.

## 7. Interrupts and Time

9.2 documentation permits specific calls such as `lv_tick_inc()` and `lv_display_flush_ready()` under the proper ISR contract, not arbitrary GUI operations.

Completion must still mean real handoff and agree with waiting mechanisms.

Verify RTOS tick rate/width/conversion. Non-1,000 Hz ticks are not milliseconds.

Interrupt priorities must permit the RTOS notification APIs being used.

## 8. Measure Input Latency

Timestamp sampling, event, rendering, submission, and visibility.

| Stage | Delay sources |
| --- | --- |
| Input | Polling, bus, filters |
| GUI | Scheduling, locks, queues |
| Rendering | CPU/hardware |
| Display | Transfer, boundary waits, scanout |

Faster sampling does not fix rendering queues; higher GUI priority can harm real-time work.

## 9. Validation and Summary

Test click, hold, rapid input, drag/release, edges, page changes, and read errors.

Add communication, animation, and loading; inspect queues, waits, and recovery.

Next: [Engineering Images, Fonts, and Chinese Interfaces](21-images-fonts.md).

## References

- [LVGL 9.2 input](https://docs.lvgl.io/9.2/porting/indev.html)
- [LVGL 9.2 OS/interrupts](https://docs.lvgl.io/9.2/porting/os.html)
- [LVGL 9.2 tick](https://docs.lvgl.io/9.2/porting/tick.html)
