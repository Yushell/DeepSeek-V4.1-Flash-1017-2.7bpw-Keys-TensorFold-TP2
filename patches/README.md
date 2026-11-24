# Patches in this folder

`0002-rdma-idle-nap.patch`, `0004-serve-keep-logs.patch`, `0005-dsv41-1m-readahead-clamp.patch`,
`0006-ooa-copy-min-rebased.patch`, `0007-capture-join-issue31.patch`, `0008-rdma-gid-env.patch` and
`0009-serve-gid-discovery.patch` are the changes this kit runs beyond the pack's own three. `0002` is not ours;
`0004`, `0009` target the recipe's launcher rather than the engine tree; `0005` is this repo's own one-line fix; `0006`
is the pack's own copy-min patch rebased for this pin; `0007` is the maintainer's capture-join fix; `0008` is our local
port of the GID env. All are reproduced here so the exact served tree is reproducible.

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

## 0007: the capture-join fix for a failed decode stretch (upstream)

- **What:** +67/−8 in `zig/src/families/dsv41/round.zig`. A decode stretch starts two side streams inside the CUDA graph
  capture; if the stretch fails before those streams join, the error path now joins them and ends the capture, reporting
  the body error instead of `CUDA_ERROR_STREAM_CAPTURE_UNJOINED (904)`.
- **Why:** without it one failed capture leaves the capture open and every later request fails. On the 2x GB10 pair the first
  decode after a bad boot read `904`, then every later request read `Failed`. It does not fix whatever fails first, only
  stops one bad round from poisoning the pair.
- **Provenance:** [bertholomus](https://github.com/bertholomus), branch
  [`fix/tp2-31-capture-join`](https://github.com/bertholomus/TensorFold/tree/fix/tp2-31-capture-join), commit
  [`a8ff91e`](https://github.com/bertholomus/TensorFold/commit/a8ff91e), filed under
  [recipe issue #31](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/issues/31). Apache-2.0.
- **Applies to:** `c9c70953`; `git apply --check` is clean.

## 0008: `TF_RDMA_GID_INDEX` for the ring's queue pairs (this repo's local port)

- **What:** a `servedGidIndex()` helper in `rdma.zig` and three call sites (`model.zig` two, `layer_main.zig` one).
  `TF_RDMA_GID_INDEX` picks the GID index the ring's queue pairs use; unset keeps upstream's 5.
- **Why:** the RoCE v2 IPv4 GID index is a function of the address assignment order. The reference pair's rails read index 3 before a
  reboot and index 4 after a `netplan apply`; a hardcoded index is a reboot trap (the boot dies
  `error: VerbsFailed`).
- **Provenance:** local port of [bertholomus PR #58](https://github.com/bertholomus/TensorFold/pull/58) (`rdma_env.zig`,
  default 5). This version adds no file and matches the `dsv41` family. Apache-2.0.
- **Applies to:** `c9c70953`; `git apply --check` is clean.

## 0009: the launcher discovers the GID index (this repo's own)

- **What:** about +60 lines in the recipe's `scripts/serve.sh`. `gid_index()` scans the HCA's sysfs GID table for the
  `RoCE v2` entry with an IPv4-mapped GID (`:ffff:`), then exports `NCCL_IB_GID_INDEX`, `TF_DS_NEIGHBOR_GID_INDEX` and
  `TF_RDMA_GID_INDEX` from it; the preflight checks that index on both nodes instead of a fixed 3.
- **Why:** with the index at 4, the stock preflight refused to start (`GID index 3 is not there`) and a hardcoded ring
  failed `VerbsFailed`. Discovery makes a reboot or a netplan apply harmless.
- **Applies to:** the recipe's `scripts/serve.sh`, after `0004` and the site GID edit; diffed against that state with one
  line of context. `serve.sh print` shows the same index in `LINK` and the engine env.
- **MTU companion:** the GID is only half the link. Both CX7 rails need `mtu 4500` (RoCE `active_mtu` 4096) persisted in
  netplan; a reboot that resets them to 1500 is what produced `VerbsFailed` and the 904 in the first place.

## The pack's own three (not reproduced here)

`0003-request-limits`, `0004-copy-min` and `0005-upstream-picks` ship with the pack
(`object-oriented-architects/DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold`, folder `zig-tp2-patches/`).
Apply `0003` as shipped, then `0006` here in place of the pack's `0004` (that patch's `native.zig` context does not fit
this pin), then `0005` as shipped; `0005` picks four upstream fixes (TCP_NODELAY on reply sockets, the draft
depth search, the admission 503, and sticky CUDA errors turning `/health` to 503). Their README has the measurements.

## What is not here

The GID index is discovered at boot by `0009`, so there is no site edit to make. The **jumbo MTU** is still a host
setting, not a patch: both CX7 rails must carry `mtu 4500` (RoCE `active_mtu` 4096) and survive reboots, or the ring
fails on data. On the reference pair that is `mtu: 4500` in netplan; a reboot that resets the rails to 1500 is what produced
`VerbsFailed` and the 904 in the first place.
