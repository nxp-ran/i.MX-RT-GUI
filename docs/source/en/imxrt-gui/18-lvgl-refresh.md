# Article 18: LVGL Refresh and Rendering

> Series: [i.MX RT Graphics in Practice](README.md)
>
> Previous: [A Minimal LVGL Port](17-lvgl-minimal-port.md)
>
> Next: [Connecting LVGL to PXP / GPU](19-lvgl-acceleration.md)
>
> Goal: Explain LVGL 9.2.0 invalidation, tasks, modes, and handoff. Internals are not stable cross-version APIs.

## 1. After a Widget Changes

```text
Object change -> Invalidate -> Refresh areas -> Draw tasks
   -> Execute -> Flush -> Return ownership
```

Object changes, task count, flush count, and visible frames are different.

No LVGL work does not imply stopped scanout.

## 2. Invalidation Exceeds Object Bounds

Movement includes old/new areas. Shadows, borders, antialiasing, and transparency can expand coverage.

Regions can merge or split into buffer-sized chunks.

One changed number does not prove only a few pixels move. Record actual regions.

Full-screen invalidation removes partial benefits; undersized invalidation leaves stale pixels.

## 3. Three Modes

| Mode | Buffer requirement | Behavior |
| --- | --- | --- |
| PARTIAL | Smaller buffers permitted | Draw regions/chunks, transfer/copy |
| DIRECT | Full screen | Update dirty locations directly |
| FULL | Full screen | Redraw the whole image |

Modes control LVGL output, not panel storage.

PARTIAL scanout designs still need a complete display frame. DIRECT/FULL still need synchronization.

## 4. Double Buffering by Mode

PARTIAL overlaps chunk drawing/transfer.

DIRECT maintains dirty-area consistency between complete frames; LVGL 9.2.0's synchronization must not be bypassed.

FULL simplifies complete back-frame content at the cost of full redraws.

| Scene | Initial candidate |
| --- | --- |
| Small GRAM interface | PARTIAL |
| Sparse complete-frame updates | DIRECT with synchronization |
| Complete animation/simple consistency | FULL |

Measure actual objects, memory, and output rather than treating this as a fixed rule.

## 5. Stride, Position, Pointer

Flush area/pixel layout depends on mode.

PARTIAL typically supplies a chunk. DIRECT/FULL may supply a full-frame start with an area descriptor.

Verify actual stride, rotation, offsets, and placement. Do not always add a screen-coordinate offset.

Tail chunks use real heights, not fixed allocation sizes.

## 6. Tasks Are Not Necessarily Hardware Commands

Backends evaluate types, formats, blend, and parameters.

One frame can mix CPU/hardware work while retaining dependencies.

A GPU function return does not establish full-frame completion. Do not submit unfinished destinations.

Preserve framework contracts rather than guessing internal states.

## 7. Flush Completion

`lv_display_flush_ready()` means buffer handoff, not function return or human-visible presentation.

Wait for source release in transfers and safe old-frame reuse in swaps.

Refresh/flush events may describe submission rather than scanout. Read definitions when measuring.

Use supported wait callbacks and OS notifications consistently instead of mixing completion models.

## 8. Observe Without Distorting

Record invalidation, backends, chunks, waits, and cycles.

| Observation | Interpretation |
| --- | --- |
| Small change redraws everything | FULL/layout/invalidation |
| Many chunks | Small buffers/fragmented regions |
| Long waits | Output/synchronization |
| CPU/GPU alternation | Coverage/dependencies, not necessarily failure |
| Events without new pixels | Event boundary differs from effective update |

Logging affects performance; prefer bounded sampling and counters.

## 9. Summary

Refresh combines objects, regions, tasks, buffers, and drivers. Match mode to architecture and workload.

Next: [Connecting LVGL to PXP / GPU](19-lvgl-acceleration.md).

## References

- [LVGL 9.2 display modes](https://docs.lvgl.io/9.2/porting/display.html)
- [LVGL 9.2.0 refresh implementation](https://github.com/lvgl/lvgl/blob/v9.2.0/src/core/lv_refr.c)
- [LVGL 9.2.0 display API](https://github.com/lvgl/lvgl/blob/v9.2.0/src/display/lv_display.h)
