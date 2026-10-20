"""Wrap the docs fragment as a standalone explainer page (phase 1), so one source serves both pages.

Usage: python3 -I wrap_docs.py <docs.html> <out.html> "<title>"

The fragment carries its own scoped styles and scripts; this adds the page head the Artifact contract asks for
(title, viewport-fit tag), a themed background, and the Ask Claude boxes (assets/ask-claude.html). Publish the
page with capabilities {"comments": {}} so the boxes can send a question to the watching session.
"""

import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_artifact import check_docs, with_ask  # noqa: E402

HEAD = """<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root{{--page-bg:#f5f6f8;--page-ink:#17202a;color-scheme:light}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--page-bg:#0f141a;--page-ink:#e3e8ee;color-scheme:dark}}}}
:root[data-theme="dark"]{{--page-bg:#0f141a;--page-ink:#e3e8ee;color-scheme:dark}}
body{{background:var(--page-bg);color:var(--page-ink);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
</style>
"""

if __name__ == "__main__":
    src, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
    frag, n = check_docs(src)
    open(out, "w", encoding="utf8").write(HEAD.format(title=html.escape(title)) + with_ask(frag))
    print(f"ok: {n} PR sections -> {out}")
