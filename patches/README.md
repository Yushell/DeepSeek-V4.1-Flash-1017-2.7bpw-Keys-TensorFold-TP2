# Patches in this folder

`0002-rdma-idle-nap.patch`, `0004-serve-keep-logs.patch`, `0005-dsv41-1m-readahead-clamp.patch` and
`0006-ooa-copy-min-rebased.patch` are the changes this kit runs beyond the pack's own three. `0002` is not ours;
`0004` targets the recipe's launcher rather than the engine tree; `0005` is this repo's own one-line fix; `0006` is the
pack's own copy-min patch rebased for this pin. All are reproduced here so the exact served tree is reproducible.

Upstream PR #51 (`TF_FILL_DRAIN`) is merged into the pinned engine commit `c9c70953`, so the former
`0003-fill-drain-pr51.patch` is no longer needed and stays only in this repo's git history. Credit for it is unchanged
(see Credits in the README).

## 0006: the pack's copy-min patch, rebased for this pin

- **What:** the pack's `zig-tp2-patches/0004-copy-min.patch`: `copy_min` on the lane `Model`/`Config`, the env parse
  `TF_DS_COPY_MIN` in `families/dsv41/native.zig`, and the copy-window check in `core/lanes/windows.zig` that leaves a
  round to the draft head below the threshold.
- **Why not the shipped patch:** its `native.zig` hunk context moved between the pack's engine pin and `c9c70953`, so
  `git apply` fails there. `config.zig`, `windows.zig` and `lanes.zig` apply verbatim; `native.zig` needed the same two
  additions by hand (the `TF_DS_COPY_MIN` doc lines and its env parse). This file is the diff of that result.
- **Provenance:** [object-oriented-architects](https://huggingface.co/object-oriented-architects),
  `DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold` → `zig-tp2-patches/0004-copy-min.patch` (MIT). Apache-2.0 as
  applied to the TensorFold tree.
- **Applies to:** `c9c70953`, right after the pack's `0003-request-limits`; `git apply --check` is clean there and the
  pack's `0005-upstream-picks` still applies after it.

## 0005: the 1M Engram read-ahead clamp (this repo's own)

- **What:** one line in `zig/src/families/dsv41/model.zig`. The next chunk's read-ahead span is
  `nn = @min(m.next_rows, m.fill_seq.len - start - n)`, and `m.next_rows` comes from `passCap`, which at a long
  prompt is the whole remaining pass, not the next chunk. The three read-ahead buffers per Engram layer are sized
  `chunk_rows` (4,096 rows), so a 1M prompt overran them. The patch clamps `nn` to `chunk_rows`; rows beyond the span
  are read at apply time, and the apply path already falls back when `ahead_n < n`.
- **Why:** v0.7.5's 64-row rounds and 32-stream pool reached the path that earlier versions did not. A 1,048,407-token
  needle panicked rank 1 in `engramAhead1` (`index out of bounds: index 50225232, len 196608`, about 1,046,359 rows
  against 4,096 x 48), and rank 0 stopped on the reciprocal rule, so the client saw `RemoteDisconnected`.
- **Measured effect:** none on decode or prefill. 1M needle exact, **1,048,407 tokens in 518.9 s**; 16 x 131,072-token
  burst **17/17 replies equal to solo, 16/16 needles**, all 16 states kept; house bench and sustained rows level with
  the same build before the clamp.
- **Applies to:** `bertholomus/TensorFold` `deepseek-v41-zig-tp2` @ `c9c70953` (v0.7.5 + merged PR #51), after the
  pack's `zig-tp2-patches/0003`-`0005`. `git apply --check` is clean on an unmodified checkout.
- **License:** Apache-2.0, as TensorFold is.

## 0002: the RDMA proxy naps when idle

- **What:** +76/−2 in `zig/src/families/dsv41/rdma.zig`. After `TF_RDMA_IDLE_S` (default 2 s) with nothing posted or
  reaped, the proxy sleeps `TF_RDMA_NAP_US` (default 100 µs) between looks instead of spinning; the next doorbell or
  completion resumes the spin immediately. `TF_RDMA_IDLE_S=0` keeps the old behaviour. Timer slack is set to 1 µs.
- **Why:** the loop polls the doorbell and `poll_cq` with no back-off, so each node held a full core at 100% with the
  server idle (measured on a 2x GB10 pair: 100.3% / 100.2%, zero connections; GPU at ~9 W).
- **Measured effect:** idle drops to under 50% of a thread on either node (ours: 1.3-2.5% of a core on v0.7.3 and
  v0.7.5). Serving is unchanged: the ring is never quiet for 2 s while decoding, so the only cost is at most one
  100 µs nap on the first gather after an idle spell.
- **Provenance:** original nap by [willjriley](https://github.com/willjriley) in
  [bertholomus/TensorFold PR #27](https://github.com/bertholomus/TensorFold/pull/27) (Python branch);
  Zig port by [MiaAI-Lab](https://github.com/MiaAI-Lab) (`0010-rdma-idle-nap.patch`);
  two-node port, test and the attachment this file is taken from by
  [wiseares](https://github.com/wiseares) in
  [recipe issue #32](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/issues/32).
  Apache-2.0, as TensorFold and that recipe are.
- **Applies to:** `bertholomus/TensorFold` `deepseek-v41-zig-tp2` @ `c9c70953`, after the pack's
  `zig-tp2-patches/0003`-`0005`. `git apply --check` is clean on an unmodified checkout; it also applied clean on the
  older `a57deb9` pin this kit used before v1.3.0.

## 0004: the launcher keeps each run's log

- **What:** +17/−2 in the recipe's `scripts/serve.sh`. `stop()` writes the container's own log with docker's
  timestamps (`tp2-lane.<stamp>.docker.log`) and renames the file the container wrote (`tp2-lane.<stamp>.log`) on
  each node, then removes the container; `start` calls `stop` first. Diffed with one line of context, so it applies
  to the upstream launcher and to one that already carries the GID edits.
- **Why:** `node_run.sh` starts the container with `--rm` and `tee /logs/tp2-lane.log`. A rank that ends by itself
  takes its docker log with it, leaving only the tee'd file, and the next start truncates that file. Without this
  change a restart wipes the only record of the run.
- **Applies to:** the recipe checkout's `scripts/serve.sh`, not the engine tree; `git apply` is clean on the upstream
  v0.7.3 and v0.7.5 launchers.
- **Test:** `scripts/test_serve_stop.sh <serve.sh>` runs the shipped `stop()` text against a fake docker: 24 checks
  fail on the stock launcher and all pass on the patched one.

## The pack's own three (not reproduced here)

`0003-request-limits`, `0004-copy-min` and `0005-upstream-picks` ship with the pack
(`object-oriented-architects/DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold`, folder `zig-tp2-patches/`).
Apply `0003` as shipped, then `0006` here in place of the pack's `0004` (that patch's `native.zig` context does not fit
this pin), then `0005` as shipped; `0005` picks four upstream fixes (TCP_NODELAY on reply sockets, the draft
depth search, the admission 503, and sticky CUDA errors turning `/health` to 503). Their README has the measurements.

## What is not here

The GID index edit (four hardcoded `5`s to `3`) is a site edit, not a patch, because the right value is whatever your
fabric's RoCE v2 address is at. See the README's Build it section.
