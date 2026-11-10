# Patches in this folder

`0002-rdma-idle-nap.patch` is the only patch we run beyond the pack's own three. It is not ours; it is
reproduced here so the exact served binary is reproducible.

## 0002: the RDMA proxy naps when idle

- **What:** +76/−2 in `zig/src/families/dsv41/rdma.zig`. After `TF_RDMA_IDLE_S` (default 2 s) with nothing posted or
  reaped, the proxy sleeps `TF_RDMA_NAP_US` (default 100 µs) between looks instead of spinning; the next doorbell or
  completion resumes the spin immediately. `TF_RDMA_IDLE_S=0` keeps the old behaviour. Timer slack is set to 1 µs.
- **Why:** the loop polls the doorbell and `poll_cq` with no back-off, so each node held a full core at 100% with the
  server idle (measured on a 2x GB10 pair: 100.3% / 100.2%, zero connections; GPU at ~9 W).
- **Measured effect:** idle drops to under 50% of a thread on either node (ours: 1.3-2.4% of a core).
  Serving is unchanged: the ring is never quiet for 2 s while decoding, so the only cost is at most one 100 µs nap
  on the first gather after an idle spell.
- **Provenance:** original nap by [willjriley](https://github.com/willjriley) in
  [bertholomus/TensorFold PR #27](https://github.com/bertholomus/TensorFold/pull/27) (Python branch);
  Zig port by [MiaAI-Lab](https://github.com/MiaAI-Lab) (`0010-rdma-idle-nap.patch`);
  two-node port, test and the attachment this file is taken from by
  [wiseares](https://github.com/wiseares) in
  [recipe issue #32](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/issues/32).
  Apache-2.0, as TensorFold and that recipe are.
- **Applies to:** `bertholomus/TensorFold` `deepseek-v41-zig-tp2` @ `a57deb9`, after the pack's
  `zig-tp2-patches/0003`-`0005`. `git apply --check` is clean on an unmodified checkout.

## The pack's own three (not reproduced here)

`0003-request-limits`, `0004-copy-min` and `0005-upstream-picks` ship with the pack
(`object-oriented-architects/DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold`, folder `zig-tp2-patches/`).
Apply them in that order before the build; `0005` picks four upstream fixes (TCP_NODELAY on reply sockets, the draft
depth search, the admission 503, and sticky CUDA errors turning `/health` to 503). Their README has the measurements.

## What is not here

The GID index edit (four hardcoded `5`s to `3`) is a site edit, not a patch, because the right value is whatever your
fabric's RoCE v2 address is at. See the README's Build it section.
