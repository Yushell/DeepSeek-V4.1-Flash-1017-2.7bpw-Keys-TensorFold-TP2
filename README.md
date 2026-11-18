# DeepSeek-V4.1-Flash-1017 · EXL3 2.7 bpw + Keys L10-35 · TensorFold TP2 (2x GB10)

A serving recipe and measured record for **DeepSeek-V4.1-Flash-1017** on two GB10 nodes: the 2.7 bpw object-oriented-architects EXL3 pack, grafted with the **drowzeys Keys L10-35** abliteration sidecar, served by **TensorFold Zig** at 1,048,576 context and **32 concurrent streams**.

Everything below was measured on a 2x GB10 pair (128 GB unified memory each, two RoCE rails) in November 2026. The lane answers on `:8888` as `DeepSeek-V4.1-Flash-TF`.

**The weights are not hosted here** (198.8 GB pack + 190 GB Engram). This repo is the serving kit, the engine build record (including the three patches we run beyond the pack's own), and the numbers.

## Credits and attributions

Credit where it is due, all links:

- **The model and its Engram tables**: [DeepSeek-AI](https://huggingface.co/deepseek-ai) publishes [DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) (MIT), a 763B MoE with the Engram memory tables as two ~94 GiB shards.
- **The 2.7 bpw pack**: [object-oriented-architects](https://huggingface.co/object-oriented-architects) built [DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold](https://huggingface.co/object-oriented-architects/DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold) (MIT), a sensitivity-allocated EXL3 pack, and publishes the three engine patches (`zig-tp2-patches/0003`-`0005`) this build applies.
- **The abliteration graft**: [drowzeys](https://huggingface.co/drowzeys) publishes [keys-DeepSeek-V4.1-Flash-1017-Abliterated](https://huggingface.co/drowzeys/keys-DeepSeek-V4.1-Flash-1017-Abliterated) (MIT), the `exl3_wo_b_l10_35_mia29` sidecar and `apply_mia29_wo_b_graft.py`.
- **The serving engine**: [bertholomus](https://github.com/bertholomus) maintains the [TensorFold](https://github.com/bertholomus/TensorFold) two-node branch (`deepseek-v41-zig-tp2`, pinned here at [`c9c70953`](https://github.com/bertholomus/TensorFold/tree/c9c709534d0fa64cd62bded064e929df6f8f797d), v0.7.5 with PR #51 merged) and the [two-Spark recipe](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10) (v0.7.5) this kit plugs into. Upstream: [ashhart/TensorFold](https://github.com/ashhart/TensorFold) and the TensorFold contributors.
- **The idle-nap patch**: [wiseares](https://github.com/wiseares) ported it to the two-node branch and attached it to [recipe issue #32](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/issues/32); the original nap is [willjriley](https://github.com/willjriley)'s [PR #27](https://github.com/bertholomus/TensorFold/pull/27), and the Zig port lineage is [MiaAI-Lab](https://github.com/MiaAI-Lab)'s `0010-rdma-idle-nap.patch`.
- **The fill-drain patch** (`TF_FILL_DRAIN`, the cut-in fix): [OsakaTX](https://github.com/OsakaTX)'s [PR #51](https://github.com/bertholomus/TensorFold/pull/51), now merged into the pinned engine commit (the kit carried a rebased copy on the older pin).
- **The 1M Engram read-ahead clamp** (`patches/0005`): this repo's own one-line fix for v0.7.5's panic at a 1M prompt; see `patches/README.md` for the failure and the measurement.
- **The EXL3 format**: [exllamav3](https://github.com/turboderp-org/exllamav3) by [turboderp](https://github.com/turboderp-org) (MIT).

The deeper stack keeps its own credits (the RoCE transport, the kernel kit, the drafting policy): see the recipe's [ATTRIBUTION.md](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/blob/main/ATTRIBUTION.md) and TensorFold's [NOTICE](https://github.com/bertholomus/TensorFold/blob/deepseek-v41-zig-tp2/NOTICE). The full list is at the end of this README.

## Results at a glance

| Metric | Result |
|---|---|
| House bench, 1 stream, 384 tokens, median of 3 | **structured 143.8 · prose 58.8 · coding 98.4 tok/s** (identical texts across reps) |
| Sustained aggregate, 90 s, set b | 8 streams 164.4 · 16 streams **209.5** · **32 streams 241.6 tok/s** |
| 16-stream capacity | 16 x 131,072-token prompts at once, 32-stream shape: burst **1,001.1 s**, **17/17 replies identical to their solo runs**, 16/16 needles found, all 16 states kept (129,024 cached tokens each) |
| Long context | 1M needle: **1,048,407 prompt tokens, exact in 518.9 s** |
| Load | ~34 s to ready; 110.3 GiB active; ~8 GiB still available on the head at the lowest |
| Idle cost | **~2.5% of one core per node** (100% of a core without the idle-nap patch) |
| Tool calls | gates 6/6: plain and streamed, no DSML markup leaks into `content` |
| **Cut-in latency** | a short request sent 3 s into a cold prompt answers in **1.11 s at 64K** and **0.79 s at 150K** (22.9 s / 33.9 s without the fill switches) |
| Kept conversations | 42K-53K-token conversations resume in **0.92-1.28 s** after five short side requests and two other long conversations (16.8-18.9 s cold); a new conversation on the same system prompt starts in 1.25 s with its 12,288-token block reused |
| Quality, seeded panel | 200 MMLU + 100 GSM8K: GSM8K 96.0 off / 98.0 on, MMLU 83.5 off / 90.5 on |
| Uncensoring | 44-item battery: 44/44 comply, 0 refusals (the stock 1017 pack refused 29 of 40 hostile prompts) |
| Vision | pass (native tower, 6/6 probes) |
| Disk | 198.8 GB pack + 190 GB Engram + ~93 GB rank cache per node |

## Quality benchmarks

The two quality rows above are one fixed, seeded probe, measured on this pack and graft against the v0.7.3 build; the v0.7.5 engine change is quality-neutral in the gates (drafted replies byte-identical to serial):

| Probe | n | Thinking off | Thinking on |
|---|---|---|---|
| MMLU (seeded subset, seed 20261004) | 200 | 83.5% (95% CI 77.7-88.0) | 90.5% (85.6-93.8) |
| GSM8K (seeded subset, seed 20261004) | 100 | 96.0% (90.2-98.4) | 98.0% (93.0-99.4) |

- Method: greedy, one question per request, exact-match answer parsing, Wilson intervals; the run records unparsed and length-cut counts (`local.json`: 1 unparsed / 1 cut on MMLU off, 3 / 3 on, 0 on both GSM8K arms).
- Uncensoring: 44-item refusal battery, **44/44 comply, 0 refusals**; the stock 1017 pack refused 29 of 40 hostile prompts on the same class of prompts.
- **Not covered here:** the fixed open-source panel below was run (MMLU 50, AIME 10, HumanEval 50, BFCL 50); the full 14k MMLU, MBPP+/HumanEval+ and IFEval were not.

## Open-source quality panel

Run 2026-11-17 against the v0.7.5 build, temperature 0, lane default thinking, each test alone and every sampler held to two connections or fewer:

| Test | N | Score |
|---|---|---|
| MMLU | 50 | 0.860 |
| AIME 2025 | 10 | 1.000 |
| HumanEval (pass@1) | 50 | 0.980 |
| BFCL | 50 | 0.900 (stderr 0.043) |

- Harness: `simple_evals` for MMLU and HumanEval, Inspect (`inspect_evals/aime2025`, `inspect_evals/bfcl`) at `--max-connections 1`; HumanEval runs under `spawn` because of the filelock fork audit.
- Read them with their N: AIME at 10 questions and HumanEval at 98% sit near a ceiling and separate models poorly; the MMLU and BFCL rows carry the information. IFEval is omitted (optional dependency plus a known metric stall), and no full 14k MMLU or MBPP+ run exists for this recipe.
- Raw logs: the panel workspace's `runs/dsv41-27-v075-20261117/` (one log and exit code per row, Inspect `.eval` files for AIME and BFCL).

## What is in the pack

| Part | Format |
|---|---|
| Attention, routed experts, MTP, head | EXL3 at 2.7 bpw average, per-expert sensitivity allocation (43 `model-*` shards plus `model-exl3-routed-*` expert files) |
| Keys L10-35 graft | 104 `wo_b` tensors across layers 10-35, trellis `[512, 320, 80]`, applied in place |
| Engram tables | separate 190 GB pair (shards 47 and 48), read by both ranks; not part of the pack |
| Everything else | as the pack ships it |

## Serve it

Prerequisites: two GB10 nodes on a 200 GbE / RoCE link (two rails preferred), Docker with the NVIDIA runtime, `nvcr.io/nvidia/pytorch:26.07-py3`, passwordless ssh from the head to the worker, and about 520 GB free per node for a local pack plus Engram (the worker can be fed over NFS instead).

1. **Stage the pack and the graft** on the head:

   ```bash
   hf download object-oriented-architects/DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold \
     --local-dir /mnt/models/dsv41-27-source
   hf download drowzeys/keys-DeepSeek-V4.1-Flash-1017-Abliterated \
     --local-dir /mnt/models/keys-l10-35
   cp -a /mnt/models/dsv41-27-source /mnt/models/dsv41-27-ablit
   ```

   Run the publisher's graft script in the torch container, with one bind covering source and destination, and **without** `--jay-zig` (this pack already carries the MTP/Engram tensors in the engine's dtypes):

   ```bash
   docker run --rm --gpus all \
     -v /mnt/models:/models -w /models/keys-l10-35 \
     nvcr.io/nvidia/pytorch:26.07-py3 \
     python apply_mia29_wo_b_graft.py \
       --src /models/keys-l10-35/exl3_wo_b_l10_35_mia29.safetensors \
       --dst /models/dsv41-27-ablit
   ```

   Check `ABLIT_META.json` reports `n_edited: 104`. The Keys repo is gated with automatic approval, so accept its terms once in the browser before `hf download`. Copy the recipe's chat template into the pack (`cp <recipe>/chat/chat_template.jinja /mnt/models/dsv41-27-ablit/`), and stage the Engram shards 47/48 under `/mnt/models/dsv41-27-engram/`.

2. **Build the engine** (see [Build it](#build-it)), then put `tensorfold-native`, `tf-dsv41-lanes`, `tf-dsv41-rank-cache`, `node_inputs.sh` and `make_token_map.py` in `/opt/dsv41-27-engine` on **both** nodes and compare md5s.

3. **Verify the kernel kit** against the grafted pack, then copy the kit to the worker *after* this step (the verify writes four RoPE tables and `vision/gate_bias_vl.safetensors` into it):

   ```bash
   <recipe>/kit/verify_kit.sh /mnt/models/dsv41-27-ablit /mnt/models/dsv41-27-source
   rsync -a <recipe>/kit/ spark-b:/opt/dsv41-27-recipe/kit/
   ```

4. **Write the config** in a v0.7.5 recipe checkout: copy `config/config.env.example` to `config.env` and fill in the paths and the fabric address.

5. **First run** builds each node's rank cache (~93 GB, no GPU) and the token map, then starts rank 1 and rank 0:

   ```bash
   cd /opt/dsv41-27-recipe
   scripts/serve.sh inputs      # both nodes at once, writes CACHE_DIR/rank-cache + dsv41_token_map.json
   scripts/serve.sh start       # preflight, then rank 1, then rank 0
   scripts/serve.sh check       # /v1/models + a 4-token chat
   ```

   The lane answers on `http://<head>:8888/v1`, model id `DeepSeek-V4.1-Flash-TF`. Thinking is on by default; send `"chat_template_kwargs": {"enable_thinking": false}` for a direct answer, and always set `max_tokens` (thinking shares the reply budget; the serve default is 32,768).

## Build it

The engine is [bertholomus/TensorFold](https://github.com/bertholomus/TensorFold) branch `deepseek-v41-zig-tp2` at [`c9c70953`](https://github.com/bertholomus/TensorFold/tree/c9c709534d0fa64cd62bded064e929df6f8f797d) (v0.7.5 with PR #51 merged), with Zig 0.17.0 and the NGC CUDA 13 toolchain, **ReleaseFast**:

```bash
# 1. source tree
curl -L https://codeload.github.com/bertholomus/TensorFold/tar.gz/c9c709534d0fa64cd62bded064e929df6f8f797d -o engine.tgz
mkdir engine && tar -xzf engine.tgz -C engine --strip-components=1 && cd engine && git init -q . && git add -A
git -c user.name=lab -c user.email=lab@local commit -qm base

# 2. the pack's patches: 0003 as shipped, its 0004 rebased for this pin (patches/0006), then 0005
git apply /mnt/models/dsv41-27-source/zig-tp2-patches/0003-request-limits.patch
git apply patches/0006-ooa-copy-min-rebased.patch
git apply /mnt/models/dsv41-27-source/zig-tp2-patches/0005-upstream-picks.patch

# 3. our GID index (four hardcoded 5s -> 3; check your own link first)
#    rdma.zig default, model.zig (2 sites), layer_main.zig (1 site)
grep -rn "gid_index = 5\|gid_index: u8 = 5" zig/src/families/dsv41/

# 4. the patches this kit adds: the idle nap and the 1M read-ahead clamp
git apply patches/0002-rdma-idle-nap.patch
git apply patches/0005-dsv41-1m-readahead-clamp.patch

# 5. build the server (the `install native` step is what produces tensorfold-native;
#    a bare `zig build` produces the generic `tensorfold` CLI only)
docker run --rm -v "$PWD:/src" -v /opt/zig:/zig -w /src \
  nvcr.io/nvidia/pytorch:26.07-py3 \
  /zig/zig build install native -Dtarget=aarch64-linux-gnu.2.28 -Doptimize=ReleaseFast \
    -Dnvcc=/usr/local/cuda/bin/nvcc -Dsm=121
```

Binaries land in `zig-out/native/bin/tensorfold-native` and `zig-out/bin/` (`tf-dsv41-lanes`, `tf-dsv41-rank-cache`). The recipe's `serve.sh` also wants `--rdma-kernels /engine/rdma_gather.fatbin`; the branch carries the kernels embedded, so drop that flag and its preflight check, and point its preflight at your RoCE v2 GID (3 on our link). Beyond those site edits, `patches/0004-serve-keep-logs.patch` makes `serve.sh stop` keep each run's log in `LOG_DIR` before it removes the container. The v0.7.5 kit carries the AOT cubins for 64-row rounds (rows 49-64); sync the whole `kit/` to the worker after `verify_kit.sh`.

Why the extra patches:

- **GID index.** The branch hardcodes `gid_index = 5`; on this link the RoCE v2 address is GID 3, so both ranks died `error: VerbsFailed`. Four edits, or a small env plumb if your branch has one.
- **Idle nap.** `families/dsv41/rdma.zig`'s proxy loop polls the doorbell and completion queue with no back-off, so each node held a full core at 100% while idle. The patch naps 100 us between looks after `TF_RDMA_IDLE_S` (2 s) of quiet; serving is unchanged because the ring is never quiet that long under load.
- **1M read-ahead clamp.** v0.7.5's Engram read-ahead takes its span from `passCap`, which at a long prompt is the whole remaining pass, while the three buffers per Engram layer hold `chunk_rows` (4,096 rows). A 1M prompt panicked rank 1 (`index 50225232, len 196608`). One line clamps the span to `chunk_rows`; rows beyond it are read at apply time. With it, the 1M needle is exact and every other row is unchanged.

## Verify it

`scripts/verify.sh` runs the recipe's own tools against a running server:

```bash
TOOLS=/opt/dsv41-27-recipe/tools ./scripts/verify.sh
```

or by hand:

```bash
python3 tools/gates.py --base http://127.0.0.1:8888 --model DeepSeek-V4.1-Flash-TF --out gates.json
python3 tools/needle.py --base http://127.0.0.1:8888 --model DeepSeek-V4.1-Flash-TF \
  --lengths 1040000 --depths 0.5 --out needle-1m.json
python3 tools/kit_bench.py --base http://127.0.0.1:8888 --model DeepSeek-V4.1-Flash-TF \
  decode --set b --tokens 384 --reps 3 --out decode.json
python3 tools/kit_bench.py --base http://127.0.0.1:8888 --model DeepSeek-V4.1-Flash-TF \
  sustained --streams 32 --tokens 256 --set b --seconds 90 --out sustained-32.json
```

The 1M needle is the gate that matters: it is the test that caught v0.7.5's Engram read-ahead panic, which `patches/0005` fixes (see Notes). `scripts/cutin_probe.py` checks the latency claim (`FILLER_WORDS=17000 DELAY_S=3` gives the ~64K shape above). `scripts/agent_scenario.py` measures prompt reuse under agent-shaped traffic (three long conversations, one system prompt shared by two of them, five short side requests); it exits 0 only when every returning turn resumed:

```bash
ENGINE_SRC=<engine checkout>/zig/src/families/dsv41 RECIPE_DIR=. \
  python3 scripts/agent_scenario.py run1
```

## Notes and gotchas

- **v0.7.5 needs `patches/0005` on this pack.** The v0.7.5 branch's 64-row rounds and 32-stream pool reach a read-ahead span of the whole remaining pass while the buffers hold `chunk_rows` (4,096 rows); a 1M prompt panicked rank 1 in `engramAhead1` and rank 0 stopped on the reciprocal rule. The one-line clamp is in `patches/0005`. With it: 1M needle exact at 1,048,407 tokens in 518.9 s, 16 x 131K burst 17/17 equal to solo, house bench and sustained rows level with the pre-v0.7.5 build. Without it, do not carry v0.7.5 on this pack.
- **Build ReleaseFast.** The v0.7.5 stage script used `ReleaseSafe`; that build measured about 1% slower. Tell them apart with `strings <bin> | grep -c "index out of bounds"` (0 on Fast, 1+ on Safe).
- **Copying a binary over a running rank fails `ETXTBSY`.** Write `<bin>.new` on the node and `mv` it into place, then restart.
- **`TF_DS_COPY_MIN=3` is deliberate, not a default to lower.** The pack's own A/B: at 2, a 2-token suffix copy took the round from the draft head on repetitive text and held depth at 1 (78.4 tok/s geomean over six seeds); at 3 it reads 89.8, and the file-rewrite case stays level. Turning copies off entirely (`TF_DS_NO_COPIES=1`) lifted the repetitive seeds too but cost that rewrite 7.6-11.6%. On this build the threshold at 2 / 3 / 5 measured 99.15 / 59.26 / 144.25, 98.53 / 58.95 / 144.41 and 99.03 / 59.33 / 144.35 tok/s: a wash here, so 3 stays for the repetitive-text case.
- **`TF_DS_NO_COPIES` / `TF_DS_SOLO_OVERHEAD` are a wash here.** Upstream's own A/B on this engine line reads +1.2% code and +2.2% structured for copies-off on one bench set, flat on the other, with a third pair reporting -5.9% on repetitive prompts. There is an open issue for the underlying round-count difference; nothing worth a lane change.
- **The window is the memory.** 5,242,880 positions with 32 streams leaves ~8 GiB on the head at the lowest, through a 1M prompt and through a 16 x 131K burst. That is five 1M slots, or 32 streams at ~164K average. Growing it costs about 0.87 GiB per node per 1,048,576 positions; measure `MemAvailable` at the lowest before you do, and do not run a second lane beside it.
- **Kept conversations hold rows in that window, and that is why agent traffic stays fast.** A kept prompt state's compressed rows stay in place: a new stream is placed clear of kept states plus growth room (`placeSoft`), and a state is overwritten only when the window has no other room, oldest first, with a log line (`the kept state of N tokens at B goes stale`). Resumes sit on the 2,048-row grid, so a returning turn re-reads up to about 2K tokens. A shared system block is kept as its own mark, so a new conversation on a known system prompt and tool set starts warm. Real chat text reads about 10% slower than `kit_bench prefill`'s random words here (2,320-2,430 against 2,584 tok/s at 65K) because it reads about 12% more Engram bytes; quote each figure with its shape.
- **32 streams is the proven shape.** 16 x 131K at 32 streams: 17/17 replies equal to solo, 16/16 needles, all 16 states kept. Sustained aggregate **164.4 / 209.5 / 241.6 tok/s at 8 / 16 / 32 streams**. Per-stream rate falls with concurrency (p50 24.0 / 15.0 / 7.6 tok/s), so quote the aggregate with its stream count.
- **`--prompt-cache-gib 2` is enough for agent traffic.** Four conversations at 14-52K plus five short side requests all resumed their kept state; 4 GiB measured identical (7/7 resumes, 9,361 fresh tokens, 6.71 against 6.72 s summed first token) and costs 2 GiB of window headroom.
- **`TF_DS_PASS_ROWS` cannot exceed 4,096 in this build.** `passRows` caps at `chunk_rows` and the unit test asserts `8192` is rejected, so a bigger prompt pass is a rebuild (the Engram buffers are sized by `chunk_rows`), not a knob. Prefill holds at 2,573 / 2,583 tok/s at 32K / 128K.
- **Prefill is one pass at a time per stream.** A short request sent into a long cold prompt is admitted between the pass's pieces (see the `TF_FILL_*` note below), so it no longer waits for the whole prompt.
- **Vision is a load-time template check.** `--vision` requires the media-reminder branch in `chat_template.jinja`; use the recipe's template (as above), not a fine-tune's.
- **The launcher's log is written over at every start.** `node_run.sh` runs the container with `--rm` and `tee /logs/tp2-lane.log`: a rank that ends by itself takes its docker log with it, leaving only that file, and the next start truncates it. `patches/0004-serve-keep-logs.patch` keeps the previous run's two files under a timestamp before the container is removed, and `scripts/test_serve_stop.sh <serve.sh>` checks it offline against a fake docker.
- **The 16-way cold burst is where the fill switches cost something.** At 32 streams the same 16 x 131K prompts, from a fresh boot, complete in **1,001.1 s**, every correctness gate green (17/17 replies equal to solo, 16/16 needles, all 16 states kept). The switches' own A/B, measured at 16 streams: **992.4 s** with `TF_FILL_*` on and **868.8 s** with them off, every correctness gate green in both (17/17 replies equal to solo, 16/16 needles in both phases). Wall time for the same 17-prompt set is 14.2% longer with the switches, but that is not a like-for-like rate: the switches-off arm's duplicate prompt resumed its twin's 129,024 cached tokens (2,099,200 prompt tokens read against 2,228,224). Per prompt token the prefill runs 2,245 tok/s with the switches and 2,416 without, 7.1% slower. The pre-fill build's 850.1 s matches the switches-off arm within 2.2%, and solo, single-prompt and sustained rows are level, so the cost is specific to many concurrent cold long prompts. The switches buy the 1.1 s cut-in that every agent turn uses; a workload dominated by simultaneous long starts is the case to boot without them.
- **The three `TF_FILL_*` switches are the latency fix, not a throughput one.** `TF_FILL_CHUNKS=2` runs a prompt pass two chunks at a time, `TF_FILL_MANY=1` admits a new request between pieces, and `TF_FILL_DRAIN=8192` starts a burst's whole one-step passes back to back. Without them a short request behind a 64K cold prompt waits the whole prompt (22.9 s here); with them it answers in 1.11 s. Burst rates and prefill are unchanged in our measurements; `TF_FILL_MANY` without `DRAIN` is the bad combination (-36-38% on a burst of eight short requests), so never set one without the other.
- **Not affiliated** with any upstream authors; see Credits for the full attribution and licenses.

## Credits

Every piece this work builds on, with links:

- **DeepSeek-V4.1-Flash-1017** (model, Engram, design, training, MIT): [deepseek-ai](https://huggingface.co/deepseek-ai) ([model page](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)).
- **The 2.7 bpw EXL3 pack and its engine patches**: [object-oriented-architects](https://huggingface.co/object-oriented-architects) ([pack](https://huggingface.co/object-oriented-architects/DeepSeek-V4.1-Flash-1017-EXL3-2.7bpw-TensorFold), MIT).
- **Keys L10-35 abliteration sidecar and apply script**: [drowzeys](https://huggingface.co/drowzeys) ([repo](https://huggingface.co/drowzeys/keys-DeepSeek-V4.1-Flash-1017-Abliterated), MIT).
- **TensorFold** (the serving engine, Apache-2.0): [bertholomus](https://github.com/bertholomus) maintains the two-node branch ([TensorFold](https://github.com/bertholomus/TensorFold) `deepseek-v41-zig-tp2` @ `c9c70953`, v0.7.5 with PR #51 merged), upstream is [ashhart/TensorFold](https://github.com/ashhart/TensorFold) and the TensorFold contributors.
- **The two-Spark serving recipe** this kit plugs into (v0.7.5, Apache-2.0): [bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10).
- **The idle-nap patch**: original by [willjriley](https://github.com/willjriley) ([PR #27](https://github.com/bertholomus/TensorFold/pull/27)); Zig port by [MiaAI-Lab](https://github.com/MiaAI-Lab) (`0010-rdma-idle-nap.patch`); two-node port and test by [wiseares](https://github.com/wiseares) ([issue #32](https://github.com/bertholomus/deepseek-v4.1-tensorfold-tp2-2xgb10/issues/32)).
- **The fill-drain patch** (`TF_FILL_DRAIN`, which makes a short request cut in between prompt pieces): [OsakaTX](https://github.com/OsakaTX) ([PR #51](https://github.com/bertholomus/TensorFold/pull/51)), merged into the pinned engine commit.
- **The 1M Engram read-ahead clamp** (`patches/0005`): this repo's own fix; the failure mode and measurement are in `patches/README.md`.
- **exllamav3** (the EXL3 format and converter, MIT): [turboderp-org/exllamav3](https://github.com/turboderp-org/exllamav3) by [turboderp](https://github.com/turboderp-org).
- **The kernel kit** (Triton AOT variants): shipped in the recipe repo above, derived from TensorFold's kernel work.

**Licenses:** this repo's scripts, config and notes are Apache-2.0 (see `LICENSE`). The model weights and the pack are MIT at their sources; the graft sidecar is MIT at its source; TensorFold is Apache-2.0 (with third-party notices in its own tree). No weights are redistributed here.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
