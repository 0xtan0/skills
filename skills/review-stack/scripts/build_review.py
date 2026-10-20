"""Turn approved PR comments into one review payload per PR, and refuse any range outside the diff.

Usage: python3 -I build_review.py <work_dir>

Reads from <work_dir>:
  comments.json  {"<pr>": {"commit_id": "<head sha>",
                           "comments": [{"path", "start_line" (optional), "line", "body"}, ...]}}
  post/pr-<N>.diff  `gh pr diff <N>` saved at the same head sha
Writes post/review-<N>.json, ready for:
  gh api -X POST repos/<owner>/<repo>/pulls/<N>/reviews --input post/review-<N>.json
No `event` field, so GitHub creates the review as PENDING.
Exits 1 and writes nothing when any line of any range is not a RIGHT-side line of its PR's diff.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflines import parse  # noqa: E402


def main(work):
    spec = json.load(open(os.path.join(work, "comments.json"), encoding="utf8"))
    bad, payloads = [], {}
    for pr, review in spec.items():
        diff = parse(os.path.join(work, "post", f"pr-{pr}.diff"))
        out = []
        for c in review["comments"]:
            start = c.get("start_line") or c["line"]
            lines = diff.get(c["path"])
            missing = [i for i in range(start, c["line"] + 1) if lines is None or i not in lines]
            if missing:
                bad.append(f"#{pr} {c['path']}:{start}-{c['line']} (not in diff: {missing[:5]})")
            item = {"path": c["path"], "line": c["line"], "side": "RIGHT", "body": c["body"]}
            if c.get("start_line") and c["start_line"] != c["line"]:
                item.update(start_line=c["start_line"], start_side="RIGHT")
            out.append(item)
        payloads[pr] = {"commit_id": review["commit_id"], "comments": out}
    if bad:
        print("REFUSED, ranges outside the diff:\n  " + "\n  ".join(bad))
        sys.exit(1)
    for pr, body in payloads.items():
        json.dump(body, open(os.path.join(work, "post", f"review-{pr}.json"), "w"), indent=1)
        print(f"#{pr}: {len(body['comments'])} comments")
    print(f"total: {sum(len(b['comments']) for b in payloads.values())}")


if __name__ == "__main__":
    main(sys.argv[1])
