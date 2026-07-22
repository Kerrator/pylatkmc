#!/usr/bin/env python3
"""Reconstruct the deep-research verified-claim sets from durable workflow agent transcripts.

Regenerates DEEP_RESEARCH_CLAIMS_2026-07-18.json. Needed because the workflow task outputs
live in /tmp and are cleaned, while the agent transcripts under ~/.claude/projects/... survive.

Only counts votes from the SECOND (Opus-verify) run: those agents carry {"model":"opus"} in
their .meta.json. Pooling both runs mixes fable+opus votes and inflates the tallies.

Verified reproduction (2026-07-21): 14/9/19/16/14 = 72 confirmed, matching the original runs.
"""
import json, os, re, glob

BASE = ("/home/kerr/.claude/projects/-home-kerr-pykmc/"
        "df9c7729-e59e-42f4-83c6-697beba5e681/subagents/workflows")
RUNS = {
    "1-barrier-surrogate": "wf_132cb1e8-2d0",
    "2-projection":        "wf_dd420569-49b",
    "3-bookkeeping":       "wf_5434bff2-efc",
    "4-stop-criteria":     "wf_59e6f5a1-501",
    "5-identity-porous":   "wf_211ee392-3c3",
}
EXPECT = {"1-barrier-surrogate": 14, "2-projection": 9, "3-bookkeeping": 19,
          "4-stop-criteria": 16, "5-identity-porous": 14}
VOTES_PER_CLAIM, REFUTATIONS_REQUIRED = 3, 2


def agent_prompt_and_result(path):
    """(first user prompt, final StructuredOutput payload) from an agent transcript."""
    prompt = result = None
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message") or {}
            if prompt is None and (obj.get("type") in ("user", "human") or msg.get("role") == "user"):
                c = msg.get("content", obj.get("content"))
                if isinstance(c, list):
                    c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
                if isinstance(c, str) and c.strip():
                    prompt = c
            c = msg.get("content")
            if isinstance(c, list):
                for p in c:
                    if isinstance(p, dict) and p.get("type") == "tool_use" \
                            and p.get("name") == "StructuredOutput":
                        result = p.get("input")
    return prompt, result


def is_opus(path):
    try:
        return json.load(open(path.replace(".jsonl", ".meta.json"))).get("model") == "opus"
    except Exception:
        return False


def extract(runid):
    claims, args = {}, None
    for path in glob.glob(os.path.join(BASE, runid, "agent-*.jsonl")):
        prompt, result = agent_prompt_and_result(path)
        if not prompt:
            continue
        if args is None and "Decompose this research question" in prompt:
            m = re.search(r"## Question\n(.*?)\n\n## Task\n", prompt, re.S)
            if m:
                args = m.group(1)          # verbatim Workflow args for this run
        if "Adversarial Claim Verifier" in prompt and is_opus(path):
            mc = re.search(r'## Claim under review\n"(.*?)"\n\n\*\*Source:\*\* (\S+)', prompt, re.S)
            if not mc:
                continue
            mq = re.search(r'\*\*Supporting quote:\*\* "(.*?)"\n\n## Checklist', prompt, re.S)
            e = claims.setdefault(mc.group(1), {"source": mc.group(2),
                                                "quote": mq.group(1) if mq else None, "votes": []})
            if result is not None and "refuted" in result:
                e["votes"].append(bool(result["refuted"]))

    out = {"runId": runid, "args": args, "confirmed": [], "refuted": [], "unverified": []}
    for ctext, e in claims.items():
        valid, ref = len(e["votes"]), sum(e["votes"])
        rec = {"claim": ctext, "source": e["source"], "quote": e["quote"],
               "vote": f"{valid - ref}-{ref}", "validVotes": valid,
               "erroredVotes": VOTES_PER_CLAIM - valid}
        bucket = ("confirmed" if valid >= REFUTATIONS_REQUIRED and ref < REFUTATIONS_REQUIRED
                  else "refuted" if ref >= REFUTATIONS_REQUIRED else "unverified")
        out[bucket].append(rec)
    return out


if __name__ == "__main__":
    allout = {}
    for name, rid in RUNS.items():
        r = allout[name] = extract(rid)
        flag = "MATCH" if len(r["confirmed"]) == EXPECT[name] else f"!! expected {EXPECT[name]}"
        print(f"{name:22s} confirmed={len(r['confirmed']):3d} refuted={len(r['refuted'])} "
              f"unverified={len(r['unverified']):3d}  {flag}")
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "DEEP_RESEARCH_CLAIMS_2026-07-18.json")
    json.dump(allout, open(dest, "w"), indent=1)
    print(f"\ntotal confirmed: {sum(len(v['confirmed']) for v in allout.values())} -> {dest}")
