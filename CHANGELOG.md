# Changelog

## v1.1.0 · 2026-11-10 (later the same day)

- Added `patches/0003-fill-drain-pr51.patch`, OsakaTX's upstream PR #51 rebased onto this engine commit, and the
  three switches it needs: `TF_FILL_CHUNKS=2 TF_FILL_MANY=1 TF_FILL_DRAIN=8192`.
- **Cut-in fixed:** a short request sent 3 s into a cold prompt now answers in 1.11 s at 64K and 0.79 s at 150K,
  against 22.9 s and 33.9 s before. This was the one measured speed gap against the community reference.
- No cost measured: sustained 8 streams 163.4 (was 163.8), 16 streams 194.9 (was 194.9), TTFT p95 0.77 / 1.82 s
  (was 0.87 / 2.05), 1M needle exact in 506.0 s (was 510.9), gates 6/6, 131K needle exact.
- House bench and prefill are unchanged (98.4 / 59.1 / 143.7 from v1.0.0; prefill 2,385 / 2,576 / 2,586 tok/s).

## v1.0.0 · 2026-11-10

- Initial release: serving kit and measured record for DeepSeek-V4.1-Flash-1017 on two GB10 nodes, 2.7 bpw
  object-oriented-architects EXL3 pack plus the drowzeys Keys L10-35 abliteration graft (104 `wo_b` tensors,
  layers 10-35), TensorFold Zig `a57deb9` (recipe v0.7.3) with the RDMA idle-nap patch.
- Serving shape: 1,048,576 context, **16 streams**, 3,932,160-position shared window, 16 parallel requests,
  `TF_DS_IDX_SPLIT=8192`, `TF_DS_COPY_MIN=3`, vision and thinking on by default; model id `DeepSeek-V4.1-Flash-TF`.
- Measured on a 2x GB10 pair: house bench 143.7 / 59.1 / 98.4 tok/s (structured / prose / coding, 1 stream);
  sustained 90 s set b 163.8 tok/s at 8 streams and **194.9 at 16 (+19.0%)**; 16 x 131K burst with 17/17 replies
  equal to solo and 16/16 needles; 1M needle 1,039,833 tokens exact in 510.9 s; boot ~45 s, 109.3 GiB active,
  9/11 GiB free.
- Idle cost: the RDMA proxy's one-core-per-node busy-poll (100.3% / 100.2%) is removed by the nap patch
  (1.3-2.4%). Serving unchanged.
- Deliberately not taken: v0.7.5 (its 64-row rounds panic at a 1M prompt in the Engram read-ahead); copies-off
  and solo-overhead knobs (a wash upstream, and copies-off costs a file rewrite 7.6-11.6% on the pack author's own
  A/B); `TF_FILL_DRAIN` (open upstream PR, a separate project).
