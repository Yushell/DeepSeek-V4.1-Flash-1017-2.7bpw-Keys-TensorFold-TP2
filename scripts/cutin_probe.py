#!/usr/bin/env python3
"""Does the lane admit a short request while a long cold prompt is prefilling?

Sends a long cold prompt, waits DELAY_S, then sends a short request, and prints
both walls. With the fill switches (patches/0003) the short request answers in
about a second; without them it waits for the whole prompt.

    API_URL=http://127.0.0.1:8888/v1/chat/completions \\
    MODEL=DeepSeek-V4.1-Flash-TF FILLER_WORDS=17000 DELAY_S=3 \\
    python3 -u scripts/cutin_probe.py

Env: API_URL, MODEL, DELAY_S (8), FILLER_WORDS (40000), MAX_TOKENS_LONG (8),
MAX_TOKENS_SHORT (24). Pseudo-words tokenize at about 3.8 tokens a word on this
family, so FILLER_WORDS=17000 is a ~64K-token prompt; read prompt_tokens from
the output instead of trusting the estimate. Keep the lane at two concurrent
requests.

Apache-2.0, part of this recipe repo.
"""

import json
import os
import random
import string
import threading
import time
import urllib.request

URL = os.environ.get("API_URL", "http://127.0.0.1:8888/v1/chat/completions")
MODEL = os.environ.get("MODEL", "DeepSeek-V4.1-Flash-TF")
DELAY = float(os.environ.get("DELAY_S", "8"))
WORDS = int(os.environ.get("FILLER_WORDS", "40000"))
LONG_MAX = int(os.environ.get("MAX_TOKENS_LONG", "8"))
SHORT_MAX = int(os.environ.get("MAX_TOKENS_SHORT", "24"))


def ask(prompt, max_tokens):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning_effort": "none",
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        data = json.loads(r.read())
    return time.time() - t0, data.get("usage", {})


def words(n, seed=7):
    rng = random.Random(seed)
    return " ".join(
        "".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(5, 8)))
        for _ in range(n)
    )


out = {}


def long_req():
    prompt = "Read this and reply with the single word DONE.\n\n" + words(WORDS)
    try:
        out["A"] = ask(prompt, LONG_MAX)
    except Exception as e:  # noqa: BLE001
        out["A"] = (0.0, {"error": str(e)})


t = threading.Thread(target=long_req, daemon=True)
t.start()
time.sleep(DELAY)
try:
    out["B"] = ask("In one short sentence, what is 17 * 23?", SHORT_MAX)
except Exception as e:  # noqa: BLE001
    out["B"] = (0.0, {"error": str(e)})
t.join()

for key, label in (("A", "long cold prompt"), ("B", "short request")):
    wall, usage = out.get(key, (0.0, {}))
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    print(
        f"{key} ({label}): wall={wall:.2f}s prompt_tokens={usage.get('prompt_tokens')} "
        f"cached={cached} error={usage.get('error')}"
    )

a_wall = out.get("A", (0.0, {}))[0]
b_wall = out.get("B", (0.0, {}))[0]
if a_wall and b_wall:
    queued = max(a_wall - DELAY, 0.0)
    verdict = "cuts in" if b_wall < max(queued / 3.0, 2.0) else "waited for the pass"
    print(
        f"short request sent {DELAY:.0f}s in; queued-behind-pass estimate {queued:.1f}s, "
        f"measured {b_wall:.1f}s -> {verdict}"
    )
