#!/usr/bin/env python3
"""Agent-traffic scenario: does a conversation's kept prompt state survive short side requests and other long
conversations, and is a shared system block reused across conversations?

It sends three long conversations (two share one system prompt and tool set, one has its own), five short side
requests (a title, a command approval, a tool-result summary) and one short conversation on the shared system prompt,
in the order agent traffic produces them. One request at a time, temperature 0, thinking off, 24-token replies: the
load is the prompt reading. Every figure is the server's own usage block (prompt_tokens, cached_tokens) plus the
client's time to the first streamed token.

  ENGINE_SRC=/path/to/engine/zig/src/families/dsv41 RECIPE_DIR=/path/to/recipe python3 scripts/agent_scenario.py run1

ENGINE_SRC  the engine checkout's dsv41 family folder (the long texts: lanes.zig, prompt.zig, round.zig,
            sampling_cases.zig, layer_main.zig, model.zig, text.zig). Any folder with seven long text files of those
            names works; the contents only set the prompt lengths.
RECIPE_DIR  the recipe checkout (README.md and RUNNING.md become the two system prompts).
BASE        the server (http://127.0.0.1:8888). OUT_DIR: where scenario-<label>.json goes (the current folder).
CACHE_SALT  optional: one salt for every request of the run, so the run starts from a cold prompt cache even on a
            server that has seen these conversations before (each conversation's own turns still resume).

Run it on a server nobody else is using: it is a measurement of prompt reuse, and other traffic changes what is kept.
Afterwards the engine's log says the same thing per request: `prompt cache: N tokens, resumed at R, ...`.
"""
import json
import os
import pathlib
import sys
import time
import urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1:8888")
SRC = pathlib.Path(os.environ.get("ENGINE_SRC", "./engine/zig/src/families/dsv41"))
RECIPE = pathlib.Path(os.environ.get("RECIPE_DIR", "."))
OUT = pathlib.Path(os.environ.get("OUT_DIR", "."))
SALT = os.environ.get("CACHE_SALT", "")
LONG = ["lanes.zig", "prompt.zig", "round.zig", "sampling_cases.zig", "layer_main.zig", "model.zig", "text.zig"]

TOOLS = [{"type": "function", "function": {"name": n, "description": d, "parameters": {"type": "object", "properties": p, "required": list(p)[:1]}}}
         for n, d, p in [
    ("read_file", "Read a text file with line numbers.", {"path": {"type": "string"}, "offset": {"type": "integer"}, "limit": {"type": "integer"}}),
    ("write_file", "Write a file, replacing its content.", {"path": {"type": "string"}, "content": {"type": "string"}}),
    ("patch", "Replace one unique string in a file.", {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}),
    ("search_files", "Search file contents with a regex.", {"pattern": {"type": "string"}, "path": {"type": "string"}, "file_glob": {"type": "string"}}),
    ("terminal", "Run a shell command and return its output.", {"command": {"type": "string"}, "timeout": {"type": "integer"}}),
    ("web_search", "Search the web.", {"query": {"type": "string"}, "limit": {"type": "integer"}}),
    ("memory", "Save a durable fact.", {"content": {"type": "string"}, "target": {"type": "string"}}),
    ("skill_view", "Load a skill by name.", {"name": {"type": "string"}, "file_path": {"type": "string"}}),
]]


def text(*names, root=None, cap=None):
    root = root or SRC
    out = "\n\n".join(f"===== {n} =====\n" + (root / n).read_text(errors="replace") for n in names)
    return out[:cap] if cap else out


def chat(model, messages, max_tokens=24, tools=None):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0, "stream": True,
            "stream_options": {"include_usage": True}, "chat_template_kwargs": {"enable_thinking": False}}
    if tools:
        body["tools"] = tools
    if SALT:
        body["cache_salt"] = SALT
    req = urllib.request.Request(BASE + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    ttft = None
    usage = {}
    parts = []
    with urllib.request.urlopen(req, timeout=3600) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            d = json.loads(data)
            if d.get("usage"):
                usage = d["usage"]
            for ch in d.get("choices") or []:
                delta = ch.get("delta") or {}
                piece = delta.get("content") or delta.get("reasoning_content") or ""
                if (piece or delta.get("tool_calls")) and ttft is None:
                    ttft = time.time() - t0
                if delta.get("content"):
                    parts.append(delta["content"])
    total = time.time() - t0
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    return {"prompt": usage.get("prompt_tokens"), "cached": cached, "fresh": (usage.get("prompt_tokens") or 0) - cached,
            "out": usage.get("completion_tokens"), "ttft_s": round(ttft if ttft is not None else total, 2),
            "total_s": round(total, 2), "reply": "".join(parts)[:80]}


class Conv:
    def __init__(self, model, system, first, tools=TOOLS):
        self.model, self.tools = model, tools
        self.messages = [{"role": "system", "content": system}, {"role": "user", "content": first}]

    def step(self, follow=None):
        if follow is not None:
            self.messages.append({"role": "user", "content": follow})
        r = chat(self.model, self.messages, tools=self.tools)
        self.messages.append({"role": "assistant", "content": r["reply"] or "ok"})
        return r


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: agent_scenario.py <label>   (see the header for ENGINE_SRC, RECIPE_DIR, BASE, OUT_DIR)")
    label = sys.argv[1]
    missing = [str(SRC / n) for n in LONG if not (SRC / n).is_file()] + [str(RECIPE / n) for n in ("README.md", "RUNNING.md") if not (RECIPE / n).is_file()]
    if missing:
        sys.exit("missing input text (set ENGINE_SRC and RECIPE_DIR):\n  " + "\n  ".join(missing))
    model = os.environ.get("MODEL") or json.load(urllib.request.urlopen(BASE + "/v1/models", timeout=10))["data"][0]["id"]

    agent_system = "You are a coding agent working in a repository. Follow the project notes below.\n\n" + text("README.md", root=RECIPE)
    other_system = "You are a reviewer of systems code. Be terse.\n\n" + text("RUNNING.md", root=RECIPE)
    A = Conv(model, agent_system, text("lanes.zig", "prompt.zig") + "\n\nQuestion 1: name the function that places a stream's extent in the pool. One line.")
    B = Conv(model, agent_system, text("round.zig", "sampling_cases.zig") + "\n\nQuestion 1: what does a round's rows limit bound? One line.")
    C = Conv(model, other_system, text("layer_main.zig", "model.zig") + "\n\nQuestion 1: which file opens the RDMA ring? One line.")
    D = Conv(model, agent_system, "List three files you would read first to understand this project. One line.")

    def side(kind, n):
        sysmsg = {"title": "You write a short title for a conversation. Reply with the title only.",
                  "approval": "You decide whether a shell command is safe to run. Reply SAFE or UNSAFE and one reason.",
                  "summary": "You summarise a tool result in two sentences."}[kind]
        return chat(model, [{"role": "system", "content": sysmsg},
                            {"role": "user", "content": f"({kind} {n})\n" + text("text.zig", cap=900 + 300 * n)}])

    rows = []

    def run(tag, fn, expect):
        r = fn()
        r.update(tag=tag, expect=expect)
        rows.append(r)
        print(f"{tag:26s} prompt {r['prompt']:>7} cached {r['cached']:>7} fresh {r['fresh']:>7}  first token {r['ttft_s']:>6.2f} s  total {r['total_s']:>6.2f} s   [{expect}]", flush=True)

    run("A turn 1", lambda: A.step(), "cold")
    run("A turn 2", lambda: A.step("Question 2: and which one moves a kept state? One line."), "resume")
    run("side title", lambda: side("title", 1), "short")
    run("side approval", lambda: side("approval", 2), "short")
    run("A turn 3 (after 2 sides)", lambda: A.step("Question 3: what is growth_rows for? One line."), "resume")
    run("B turn 1 (same system)", lambda: B.step(), "shared system block")
    run("C turn 1 (other system)", lambda: C.step(), "cold")
    run("A turn 4 (after B, C)", lambda: A.step("Question 4: what makes a kept state stale? One line."), "resume")
    run("side summary", lambda: side("summary", 3), "short")
    run("B turn 2", lambda: B.step("Question 2: what is a round's cost table? One line."), "resume")
    run("C turn 2", lambda: C.step("Question 2: where is the GID index read? One line."), "resume")
    run("D turn 1 (same system)", lambda: D.step(), "shared system block")
    run("D turn 2", lambda: D.step("And a fourth? One line."), "resume")
    run("A turn 5", lambda: A.step("Question 5: one more detail about placeSoft. One line."), "resume")

    returning = [r for r in rows if r["expect"] == "resume"]
    resumed = [r for r in returning if r["cached"] > 0]
    out = {"label": label, "model": model, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "rows": rows,
           "returning_turns": len(returning), "returning_turns_resumed": len(resumed),
           "returning_fresh_tokens": sum(r["fresh"] for r in returning),
           "returning_first_token_s": round(sum(r["ttft_s"] for r in returning), 2)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"scenario-{label}.json").write_text(json.dumps(out, indent=1))
    print(f"\nreturning turns resumed: {len(resumed)} of {len(returning)}; fresh tokens read on them {out['returning_fresh_tokens']:,}; "
          f"first token summed {out['returning_first_token_s']} s (worst {max(r['ttft_s'] for r in returning)} s)")
    sys.exit(0 if len(resumed) == len(returning) else 1)


if __name__ == "__main__":
    main()
