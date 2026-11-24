# Changelog

## v1.5.1 · 2026-11-24

- Added the 4 x 1M capacity row: four 1,048,576-token prompts at once, **4/4 needles found, 4/4 replies equal to
  their solo runs**, drafted equals serial; burst 2,134.6 s, solo resumes 12.4 s (1,046,528 cached tokens each). The
  stock `long_check.py` appends a sampled fifth 1M case, which over-subscribes the 5.24M pool; the clean arm removes
  it.

## v1.5.0 · 2026-11-24

- Added `patches/0007-capture-join-issue31.patch`: bertholomus's `fix/tp2-31-capture-join` fix (commit `a8ff91e`).
  A decode stretch that fails before its two side streams join now joins them, ends the capture and reports the body
  error instead of leaving `CUDA_ERROR_STREAM_CAPTURE_UNJOINED (904)` poisoning every later request.
- Added `patches/0008-rdma-gid-env.patch`: `TF_RDMA_GID_INDEX` for the ring's queue pairs (unset keeps 5), a local port
  of PR #58. The RoCE v2 IPv4 GID index moves with the address assignment order, so a hardcoded index is a reboot trap.
- Added `patches/0009-serve-gid-discovery.patch`: the launcher discovers the device's RoCE v2 IPv4 GID on every boot and
  sets `NCCL_IB_GID_INDEX`, `TF_DS_NEIGHBOR_GID_INDEX` and `TF_RDMA_GID_INDEX` from it; the preflight checks that index
  on both nodes. `config.env.example` no longer carries a fixed neighbor index.
- Added `TF_FILL_ROUNDS=32` to the config: with another stream live, each prompt piece is followed by 32 of that
  stream's rounds. Measured beside a cold 99,840-token prompt: **1.2 chunks/s at the default 4, 4.2 at 16, 7.6 at 32**,
  with the prompt at 44.2 / 49.5 / 58.1 s. No cost when nothing else is decoding.
- The README now records the MTU companion: both CX7 rails need `mtu 4500` (RoCE `active_mtu` 4096) persisted across
  reboots; a reset to 1500 produces `VerbsFailed` and the 904 above.
- Measured on this build: house bench **148.0 / 61.1 / 102.5 tok/s** (structured / prose / coding; 146.8 / 60.4 / 100.8
  after a 2 h soak, within 1.5%); 2 h at 32 streams **6,259 requests, 222.0 t/s aggregate**, per-stream p50 7.15,
  TTFT p50 0.375 s / p95 0.55 s, memory flat, 87 C, no throttle reason; warm restart `loaded in 33.0 s` (37 s to the
  chat check).

## v1.4.0 · 2026-11-17

- Ran the fixed open-source quality panel against this build and added it to the README: **MMLU 50 = 0.860**,
  **AIME 2025 10 = 1.000**, **HumanEval 50 pass@1 = 0.980**, **BFCL 50 = 0.900** (stderr 0.043). Temperature 0, lane
  default thinking, each test alone, every sampler held to two connections or fewer; `simple_evals` for MMLU and
  HumanEval, Inspect for AIME and BFCL.
- The notes record the ceilings (AIME at 10 questions, HumanEval at 98%) and the omissions (IFEval, full 14k MMLU,
  MBPP+) so the row is not over-read.

## v1.3.1 · 2026-11-17

- Added a `Quality benchmarks` section to the README: the seeded MMLU (200) and GSM8K (100) panel with its method and
  95% Wilson intervals, thinking off and on (MMLU 83.5% / 90.5%, GSM8K 96.0% / 98.0%), the 44-item uncensoring
  battery (44/44), and an explicit note that no full open-source suite has been run against this recipe.

## v1.3.0 · 2026-11-17

- Moved the pin to the v0.7.5 branch, `c9c70953` (v0.7.5 with PR #51 merged), and added
  `patches/0005-dsv41-1m-readahead-clamp.patch`: a one-line clamp that fixes the Engram read-ahead panic at a 1M
  prompt (`index 50225232, len 196608`). `0003-fill-drain-pr51.patch` is retired because PR #51 is in the pin.
- Serving shape: **32 streams, 64-row rounds, 5,242,880-position window** (was 16 / 32 / 3,932,160), with
  `TF_DS_ROUND_MS` and the v0.7.5 kit's cubins for rows 49-64.
- Measured on the 2x GB10 pair: house bench **143.8 / 58.8 / 98.4 tok/s** (structured / prose / coding); sustained
  90 s set b **164.4 / 209.5 / 241.6 tok/s at 8 / 16 / 32 streams** (+6.9% at 16 over the v0.7.3 build's 194.9;
  32 streams is a new tier); 1M needle **1,048,407 tokens exact in 518.9 s**; 16 x 131,072-token burst **17/17
  replies equal to solo, 16/16 needles, all 16 states kept**, 1,001.1 s; boot ~34 s, 110.3 GiB active, ~8 GiB free
  on the head at the lowest; idle ~2.5% of a core per node.
- Config A/B round: `TF_DS_COPY_MIN` at 2 / 3 / 5 is a wash (99.15 / 59.26 / 144.25, 98.53 / 58.95 / 144.41,
  99.03 / 59.33 / 144.35), so 3 stays; `--prompt-cache-gib 4` measured identical to 2 (7/7 resumes, 9,361 fresh
  tokens, 6.71 against 6.72 s), so 2 stays; the 5,242,880 window is kept (+33% capacity, +1.7% at 32 streams, 1M
  needle and the 16-way burst green); `TF_DS_PASS_ROWS` above 4,096 is refused by the binary's `passRows` check.
- README: results table, build steps (`zig build install native` is the step that produces `tensorfold-native`),
  patch set and notes updated to the new pin and shape.

## v1.2.2 · 2026-11-12

- Ran the fill-switch A/B on the 16 x 131K capacity burst, from a fresh boot with an empty prompt cache each arm:
  **992.4 s with `TF_FILL_*`, 868.8 s without**, every gate green in both (17/17 replies equal to solo, 16/16
  needles in both phases, the drafted reply equals the serial one). Wall time for the same 17-prompt set is 14.2%
  longer with the switches; per prompt token the prefill runs 2,245 against 2,416 tok/s (7.1% slower), because the
  switches-off arm's duplicate prompt resumed its twin's 129,024 tokens (2,099,200 against 2,228,224 prompt tokens).
  The pre-fill build's 850.1 s matches the switches-off arm within 2.2%; solo, single-prompt and sustained rows are
  level. README's burst row and Notes now carry both arms.

## v1.2.1 · 2026-11-12

- Measured the 16 x 131K capacity burst on the fill build: every gate passes (17/17 replies equal to solo, 16/16
  needles in both phases, drafted reply equals the serial one), burst **992.4 s** against 850.1 s on the pre-fill
  build. The README row now quotes this build's number, and Notes explains the comparison: part of the gap is one
  fewer full prefill in the older run (a duplicate prompt resumed its twin's 129,024 tokens there), the rest is the
  interleaving of 16 cold prompts' pieces. Single-prompt and sustained rows are unchanged.

## v1.2.0 · 2026-11-12

- Added `patches/0004-serve-keep-logs.patch`: `serve.sh stop` keeps each node's run log (the container's own log with
  docker's timestamps, and the file the container wrote) before it removes the container, so a restart no longer
  wipes the only record of the previous run. `scripts/test_serve_stop.sh` checks it offline against a fake docker.
- Added `scripts/agent_scenario.py`: prompt reuse under agent-shaped traffic (three long conversations, one system
  prompt shared by two, five short side requests). Measured here: **7 of 7 returning turns resumed** their kept
  state, first token **0.45-1.52 s** against 18.7-28.0 s cold at 44K-71K tokens; a new conversation on the same
  system prompt starts in 1.25 s with its 12,288-token block reused.
- README: the kept-conversation row in Results, a note on how the window holds kept states and why real chat text
  reads about 10% slower than the random-word prefill bench, and the launcher's log behaviour.

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
