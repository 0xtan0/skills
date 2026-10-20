"""Build the class diagram section of the explainer (phase 1) from a data file, and check the data first.

Usage: python3 -I class_diagram.py <class-diagram.json> <out-section.html>

Paste the output into docs.html in place of the class diagram section (it is one <section id="doc-classes">
with its own scoped style and script). The engine lays the boxes out on each package's grid, gives every
relation its own lane in a gap, and draws UML notation. This script refuses data the engine cannot draw
cleanly, so a bad grid fails here and not as a line through a box.

Data file:
{
  "prs": [101, 104],                         stack order; each needs a .d-c<N> colour helper in docs.html
  "classes": {
    "<id>": {
      "st": "interface",                     stereotype: "" for a plain class, else interface, abstract,
                                             function, functions, module, hooks, components, schemas, error ...
      "n": "PaymentProvider",                name in the box
      "pr": 101,                             PR that adds the type, 0 = in the root branch before the stack
      "about": "One sentence.",              shown in the detail panel
      "also": ["implements Port"],            relations to types the diagram does not draw (optional)
      "m": [["+ charge(order): Receipt", 101, [104]]]
                                             public members: [signature, introducing PR (0 = before the
                                             stack), [PRs that change it], optional full signature]. Write
                                             the full signature; the engine shortens long ones in the box and
                                             keeps the full text in the tooltip and the panel.
    }
  },
  "packages": [
    {"name": "@scope/pkg · folder", "band": 0, "grid": [["a", "b"], ["c", null]]}
                                             band = row of the page, top to bottom (callers above callees);
                                             grid = the package's own rows of class ids, null = empty cell
  ],
  "edges": [["from", "to", "dep", "label"]]  kind: inh (extends), real (implements), comp (owns, diamond at
                                             from), agg (holds, hollow diamond at from), dep (uses);
                                             label optional
}

Layout rules (checked below):
- Each class sits in exactly one cell.
- An edge joins two classes in the same package, or in packages on adjacent bands. Two packages on the same
  band cannot be joined: move one to another band, or name the relation in "also".
- Same package, same row: the cells between the two ends are empty.
- Vertical edges: every cell the vertical part crosses is empty. Inside a package, the lane sits in the gap
  next to the target, so the source column is crossed between the source and that gap. Across bands, the
  source column is crossed from the source to its package edge, and the target column from its package edge
  to the target. Put a callee in the row next to its caller, and keep the column under (or over) a type
  that the next band points at clear.
"""

import json
import os
import sys

KINDS = {"inh", "real", "comp", "agg", "dep"}
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "class-diagram.html")


def check(d):
    errs = []
    prs = d.get("prs") or []
    if not prs:
        errs.append("prs: list the stack's PR numbers")
    classes, packages, edges = d.get("classes", {}), d.get("packages", []), d.get("edges", [])
    known = set(prs) | {0}
    for cid, c in classes.items():
        for k in ("st", "n", "pr", "m"):
            if k not in c:
                errs.append(f"class {cid}: missing {k}")
        if c.get("pr") not in known:
            errs.append(f"class {cid}: pr {c.get('pr')} is not in prs and not 0")
        for m in c.get("m", []):
            if not (isinstance(m, list) and 3 <= len(m) <= 4 and isinstance(m[2], list)):
                errs.append(f"class {cid}: member {m!r} must be [signature, pr, [changed], full?]")
                continue
            if m[1] not in known or any(p not in known for p in m[2]):
                errs.append(f"class {cid}: member {m[0]!r} names a PR outside the stack")
    pos = {}
    bands = sorted({p.get("band") for p in packages})
    if bands != list(range(len(bands))):
        errs.append(f"packages: bands must be 0..n without holes, got {bands}")
    for pi, p in enumerate(packages):
        for r, row in enumerate(p.get("grid", [])):
            for ci, cid in enumerate(row):
                if cid is None:
                    continue
                if cid not in classes:
                    errs.append(f"package {p['name']}: unknown class {cid}")
                elif cid in pos:
                    errs.append(f"class {cid}: placed twice")
                else:
                    pos[cid] = (pi, r, ci)
    for cid in classes:
        if cid not in pos:
            errs.append(f"class {cid}: not placed in any package grid")

    def cell(pi, r, ci):
        g = packages[pi]["grid"]
        return g[r][ci] if r < len(g) and ci < len(g[r]) else None

    def crossed(pi, ci, rows, who):
        for r in rows:
            if cell(pi, r, ci):
                errs.append(f"edge {who}: its vertical line crosses {cell(pi, r, ci)} "
                            f"({packages[pi]['name']}, row {r}, column {ci})")

    for e in edges:
        who = " -> ".join(map(str, e[:2]))
        if len(e) < 3 or e[2] not in KINDS:
            errs.append(f"edge {who}: kind must be one of {sorted(KINDS)}")
            continue
        if e[0] not in pos or e[1] not in pos:
            errs.append(f"edge {who}: unknown or unplaced class")
            continue
        (pa, ra, ca), (pb, rb, cb) = pos[e[0]], pos[e[1]]
        ba, bb = packages[pa]["band"], packages[pb]["band"]
        if pa == pb and ra == rb:
            lo, hi = sorted((ca, cb))
            between = [cell(pa, ra, c) for c in range(lo + 1, hi) if cell(pa, ra, c)]
            if between:
                errs.append(f"edge {who}: the horizontal line crosses {between}")
        elif pa == pb:
            # the lane sits in the gap next to the target; the source column is crossed up to it
            rows = range(ra + 1, rb) if rb > ra else range(rb + 1, ra)
            crossed(pa, ca, rows, who)
        elif ba == bb:
            errs.append(f"edge {who}: both packages are on band {ba}; move one to another band or use 'also'")
        elif abs(ba - bb) != 1:
            errs.append(f"edge {who}: bands {ba} and {bb} are not adjacent")
        else:
            down = bb > ba
            na, nb = len(packages[pa]["grid"]), len(packages[pb]["grid"])
            crossed(pa, ca, range(ra + 1, na) if down else range(0, ra), who)
            crossed(pb, cb, range(0, rb) if down else range(rb + 1, nb), who)
    return errs


def main(src, out):
    d = json.load(open(src, encoding="utf8"))
    errs = check(d)
    if errs:
        print("class diagram data refused:\n- " + "\n- ".join(errs), file=sys.stderr)
        sys.exit(1)
    tpl = open(TEMPLATE, encoding="utf8").read()
    buttons = "\n".join(
        f'      <button type="button" aria-pressed="false" class="d-c{p}" data-pr="{p}">#{p}</button>'
        for p in d["prs"])
    data = json.dumps({k: d[k] for k in ("classes", "packages", "edges")}, ensure_ascii=False)
    data = data.replace("</", "<\\/")  # keep the JSON from closing its script tag
    page = tpl.split("-->", 1)[1].lstrip("\n")
    page = page.replace("__CD_PR_BUTTONS__", buttons).replace("__CD_DATA__", data)
    open(out, "w", encoding="utf8").write(page)
    print(f"ok: {len(d['classes'])} types, {len(d['packages'])} packages, {len(d['edges'])} relations -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
