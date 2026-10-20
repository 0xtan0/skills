"""Build the review artifact page from the per-PR review files.

Usage: python3 -I build_artifact.py <work_dir> <out.html> [--feedback db|file] [--docs <docs.html>]

--docs adds the stack explanation (a fragment, see check_docs) as a left pane: the page opens in split view on
wide screens, with Docs / Split / Review switches and scroll sync by PR.

--feedback file builds a findings-only page (no feedback controls) for accounts without the artifact
`db` capability; the reviewer then edits feedback.md (see feedback_file.py). Default: db.

Reads from <work_dir>:
  stack.json         {"repo", "author", "title", "root", "prs": [{"pr", "head", "base"}, ...]} in stack order
  reviews/pr-<N>.json one per PR (schema in SKILL.md)
  ste.txt            optional STE rewrites, blocks of:
                       @@ pr-<N>          then  S: <summary>
                       @@ <finding id>    then  T: / P: / E: / F: lines (title, problem, effect, fix)
                     A finding with no block keeps the reviewer's own wording.
Fails when a review file is missing, a finding id is duplicated, or ste.txt names an unknown id.
"""

import html
import json
import os
import re
import sys

STD = {"id", "severity", "category", "file", "line", "title", "detail", "failure_scenario", "suggested_fix"}


def fmt(s):
    s = html.escape(str(s).strip(), quote=False)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def read_ste(path):
    blocks, cur = {}, None
    if not os.path.exists(path):
        return blocks
    for line in open(path, encoding="utf8"):
        line = line.rstrip("\n")
        if line.startswith("@@ "):
            cur = line[3:].strip()
            blocks[cur] = {}
        elif cur and len(line) > 3 and line[1:3] == ": " and line[0] in "TPEFS":
            blocks[cur][line[0]] = line[3:]
    return blocks


def check_docs(path):
    """The docs fragment shares one document with the review page, so it must not collide with it."""
    frag = open(path, encoding="utf8").read()
    low = frag.lower()
    for tag in ("<!doctype", "<html", "<head", "<body", "<title"):
        # match the tag name whole, so <header> and <bodyless-thing> are not taken for <head> and <body>
        assert not re.search(re.escape(tag) + r"[\s>/]", low), f"{path}: a fragment has no {tag}>; the review page owns the document"
    bad = sorted({i for i in re.findall(r'\bid="([^"]+)"', frag) if not i.startswith("doc-")})
    assert not bad, f"{path}: every id must start with doc- (found {bad[:8]})"
    secs = re.findall(r'\bid="doc-pr-(\d+)"', frag)
    assert secs, f"{path}: no section with id doc-pr-<N>, so the panes cannot sync"
    for placeholder in ("__DATA__", "__DOCS__", "__TITLE__", "__REPO__", "__AUTHOR__", "__HASDOCS__"):
        assert placeholder not in frag, f"{path}: contains {placeholder}"
    return frag, len(secs)


def with_ask(frag):
    """Append the Ask Claude boxes (assets/ask-claude.html): one per docs section, live only where the page
    declares the comments capability and a Claude session watches it."""
    here = os.path.dirname(os.path.abspath(__file__))
    ask = open(os.path.join(here, "..", "assets", "ask-claude.html"), encoding="utf8").read()
    return frag + "\n" + ask.split("-->", 1)[1].lstrip("\n")


def main(work, out, feedback="db", docs=None):
    assert feedback in ("db", "file"), feedback
    here = os.path.dirname(os.path.abspath(__file__))
    stack = json.load(open(os.path.join(work, "stack.json"), encoding="utf8"))
    ste = read_ste(os.path.join(work, "ste.txt"))
    prs, seen = [], set()
    for entry in stack["prs"]:
        n = entry["pr"]
        d = json.load(open(os.path.join(work, "reviews", f"pr-{n}.json"), encoding="utf8"))
        assert d["pr"] == n, f"pr-{n}.json says pr {d['pr']}"
        summary = ste.get(f"pr-{n}", {}).get("S", d.get("summary", ""))
        findings = []
        for f in d["findings"]:
            assert f["id"] not in seen, f"duplicate finding id {f['id']}"
            seen.add(f["id"])
            b = ste.get(f["id"], {})
            extra = {k: v for k, v in f.items() if k not in STD}
            conf = "; ".join(f"{k}: {v}" for k, v in extra.items()) or None
            findings.append({
                "id": f["id"], "severity": f["severity"], "category": f.get("category", ""),
                "file": f["file"], "line": f["line"],
                "title": fmt(b.get("T", f["title"])),
                "problem": fmt(b.get("P", f["detail"])),
                "effect": fmt(b.get("E", f["failure_scenario"])),
                "fix": fmt(b.get("F", f["suggested_fix"])),
                "orig": {k: f[k] for k in ("title", "detail", "failure_scenario", "suggested_fix")},
                "confidence": conf,
            })
        prs.append({"pr": n, "title": d["title"], "url": d["url"], "head_sha": d["head_sha"],
                    "base": entry["base"], "head": entry["head"], "summary": fmt(summary),
                    "findings": findings})
    unknown = set(ste) - seen - {f"pr-{p['pr']}" for p in prs}
    assert not unknown, f"ste.txt names unknown ids: {sorted(unknown)}"
    data = json.dumps({"root": stack["root"], "feedback": feedback, "prs": prs}, ensure_ascii=False).replace("</", "<\\/")
    tpl = open(os.path.join(here, "..", "assets", "review-template.html"), encoding="utf8").read()
    page = (tpl.replace("__DATA__", data)
               .replace("__TITLE__", html.escape(stack["title"]))
               .replace("__REPO__", html.escape(stack["repo"]))
               .replace("__AUTHOR__", html.escape(stack["author"])))
    nsec = 0
    frag = ""
    if docs:
        frag, nsec = check_docs(docs)
        frag = with_ask(frag)
    page = page.replace("__HASDOCS__", "1" if docs else "0").replace("__DOCS__", frag)
    open(out, "w", encoding="utf8").write(page)
    print(f"ok: {len(prs)} PRs, {len(seen)} findings, {len(ste)} STE blocks"
          + (f", docs pane with {nsec} PR sections" if docs else "") + f" -> {out}")


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = "db"
    if "--feedback" in args:
        i = args.index("--feedback")
        mode = args[i + 1]
        del args[i:i + 2]
    docs = None
    if "--docs" in args:
        i = args.index("--docs")
        docs = args[i + 1]
        del args[i:i + 2]
    main(args[0], args[1], mode, docs)
