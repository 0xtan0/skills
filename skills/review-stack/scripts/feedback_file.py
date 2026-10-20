"""Fallback feedback store: a Markdown file the reviewer edits, for when the artifact `db` is not available.

Usage:
  python3 -I feedback_file.py init <work_dir>   write <work_dir>/feedback.md from stack.json and reviews/*.json
                                                (refuses to overwrite an existing file)
  python3 -I feedback_file.py read <work_dir>   print the feedback as JSON, in the same shape as the db's
                                                `feedback` docs: [{target, pr, kind, status, comment, rereview}]

File format (one block per PR and per finding; the reviewer edits only the `status:` value and the text
under `comment:`):

  ## PR #147 · <title>
  rereview: no
  comment:
  <free text, any number of lines>

  ### 147-1 · medium · src/steps/openCycle.ts:387
  Cycle id keyed on wall clock, not SCHEDULED_AT
  status: open
  rereview: no
  comment:
  <free text>

status is one of: open | post | ignore | validate | question. Anything else is reported as an error.
"""

import json
import os
import re
import sys

STATUSES = {"open", "post", "ignore", "validate", "question"}
HEADER = """# Review feedback: {title}

Edit this file, then tell Claude in the session that it is ready.

- Set `status:` on each finding to one of: `post` (post the suggestion as it is), `ignore`,
  `validate` (Claude checks it against the code first), `question`, or leave `open`.
- Write a comment or a question under `comment:`. It can have several lines.
- Set `rereview: yes` to ask Claude to check the finding or the PR again.
- Do not change the `##` and `###` heading lines: Claude finds each item by them.
"""


def init(work):
    out = os.path.join(work, "feedback.md")
    if os.path.exists(out):
        sys.exit(f"{out} exists: not overwritten")
    stack = json.load(open(os.path.join(work, "stack.json"), encoding="utf8"))
    parts = [HEADER.format(title=stack["title"])]
    n = 0
    for entry in stack["prs"]:
        d = json.load(open(os.path.join(work, "reviews", f"pr-{entry['pr']}.json"), encoding="utf8"))
        parts.append(f"\n## PR #{d['pr']} · {d['title']}\nrereview: no\ncomment:\n\n")
        for f in d["findings"]:
            parts.append(f"### {f['id']} · {f['severity']} · {f['file']}:{f['line']}\n"
                         f"{f['title']}\nstatus: open\nrereview: no\ncomment:\n\n")
            n += 1
    open(out, "w", encoding="utf8").write("".join(parts))
    print(f"ok: {out}, {len(stack['prs'])} PRs, {n} findings")


def read(work):
    text = open(os.path.join(work, "feedback.md"), encoding="utf8").read()
    items, errors, cur, in_comment = [], [], None, False
    for line in text.splitlines():
        m_pr = re.match(r"^## PR #(\d+)\b", line)
        m_f = re.match(r"^### (\S+) · ", line)
        if m_pr or m_f:
            cur = ({"target": f"pr-{m_pr.group(1)}", "pr": int(m_pr.group(1)), "kind": "pr", "status": None}
                   if m_pr else
                   {"target": m_f.group(1), "pr": int(m_f.group(1).split("-")[0]), "kind": "finding",
                    "status": "open"})
            cur.update(rereview=False, comment=[])
            items.append(cur)
            in_comment = False
            continue
        if cur is None:
            continue
        if in_comment:
            cur["comment"].append(line)
            continue
        m = re.match(r"^(status|rereview|comment):\s*(.*)$", line.strip())
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "status" and cur["kind"] == "finding":
            if val.lower() not in STATUSES:
                errors.append(f"{cur['target']}: unknown status {val!r}")
            cur["status"] = val.lower()
        elif key == "rereview":
            cur["rereview"] = val.lower() in {"yes", "y", "true", "1"}
        elif key == "comment":
            in_comment = True
            if val:
                cur["comment"].append(val)
    for it in items:
        it["comment"] = "\n".join(it["comment"]).strip()
    print(json.dumps({"items": items, "errors": errors}, ensure_ascii=False, indent=1))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    {"init": init, "read": read}[sys.argv[1]](sys.argv[2])
