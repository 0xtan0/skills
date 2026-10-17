#!/usr/bin/env python3
"""Check an infra-flow-deck page in headless Chrome, then screenshot every slide.

Usage: python3 check.py DECK.html [--ledger LEDGER.txt] [--out DIR] [--no-shots]

Fails (exit 1) on:
  - a label (.lbl .sub .tag .chiptx, account and region titles) that overlaps another label or a tile
  - a label crossed by a line (.arr .mon .deploy .uses)
  - a .tag or .lbl/.sub on or within 6px of a box border (.acc .reg .grp .chainbox)
  - a line that runs through a tile it does not start or end at
  - diagram text smaller than 16px
  - a <marker> inside a slide (it does not paint while that slide is hidden)
  - a Play step that names an id its own svg does not have, or a solid arrow (.arr) no step uses
  - a path with a command segs() cannot measure (only absolute M, H, V, L are checked)
  - chip text (.chiptx) that runs past its chip
  - a white tile with a white glyph (github, vercel, discord, pagerduty need their brand colour)
  - a matrix (.mx-wrap) that scrolls at 1440x1000
  - a ledger line whose arrow id is not in the page

Ledger format, one line per edge from the code:
  arrowId | source -> destination :port | file:line
  -       | left out: reason            | file:line
Lines starting with # are ignored.

The page must register each Play: player() pushes {svg, steps} to window.__players.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium", "chromium-browser",
]

PROBE = r"""
<script>
addEventListener('load',()=>setTimeout(()=>{
const out=[];const err=(slide,kind,msg)=>out.push({slide,kind,msg});
const slides=[...document.querySelectorAll('.slide')];
document.querySelectorAll('.slide marker').forEach(m=>err(-1,'marker','marker #'+m.id+' is inside a slide'));
const LBL='text.lbl,text.sub,text.tag,text.chiptx,text.acct-t,text.regt';
const LINES='path.arr,path.mon,path.deploy,path.uses';
const BOX='rect.acc,rect.reg,rect.grp,rect.chainbox';
const badPath=p=>/[a-zCSQTAZ]/.test((p.getAttribute('d')||'').replace(/\de-?\d/g,''));
function segs(p){const d=p.getAttribute('d')||'';const t=d.match(/[MHVL]|-?[\d.]+/g)||[];
  let i=0,c='',x=0,y=0,r=[];while(i<t.length){if(/[MHVL]/.test(t[i]))c=t[i++];
  if(c==='M'){x=+t[i++];y=+t[i++];c='L';continue}
  let nx=x,ny=y;if(c==='H')nx=+t[i++];else if(c==='V')ny=+t[i++];else{nx=+t[i++];ny=+t[i++]}
  r.push([x,y,nx,ny]);x=nx;y=ny}return r}
const bb=e=>{const b=e.getBBox();return{x:b.x,y:b.y,w:b.width,h:b.height}};
const ov=(a,b)=>Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x))*Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));
function segHits(s,b){const[x1,y1,x2,y2]=s;
  if(y1===y2){return y1>b.y&&y1<b.y+b.h&&Math.max(x1,x2)>b.x&&Math.min(x1,x2)<b.x+b.w}
  if(x1===x2){return x1>b.x&&x1<b.x+b.w&&Math.max(y1,y2)>b.y&&Math.min(y1,y2)<b.y+b.h}
  return false}
const name=e=>(e.id?'#'+e.id:'')+' "'+(e.textContent||'').trim().slice(0,30)+'"';
slides.forEach((sl,si)=>{
  if(typeof go==='function')go(si);
  sl.querySelectorAll('svg').forEach(svg=>{
    const texts=[...svg.querySelectorAll(LBL)].filter(t=>t.textContent.trim());
    const tb=texts.map(t=>{const b=bb(t);return{x:b.x+1,y:b.y+3,w:b.w-2,h:b.h-6}});
    const tiles=[...svg.querySelectorAll('rect.tile')].map(r=>({r,b:bb(r),node:r.closest('.node')}));
    const lines=[...svg.querySelectorAll(LINES)];
    const boxes=[...svg.querySelectorAll(BOX)].map(bb);
    texts.forEach((t,i)=>{
      const fs=parseFloat(getComputedStyle(t).fontSize);if(fs<16)err(si,'size',name(t)+' is '+fs+'px');
      for(let j=i+1;j<texts.length;j++)if(ov(tb[i],tb[j])>4)err(si,'text-text',name(t)+' overlaps '+name(texts[j]));
      tiles.forEach(T=>{if(ov(tb[i],T.b)>4)err(si,'text-tile',name(t)+' overlaps tile '+(T.node?T.node.id:''))});
      lines.forEach(l=>segs(l).forEach(s=>{if(segHits(s,tb[i]))err(si,'line-text',(l.id||l.getAttribute('class'))+' crosses '+name(t))}));
      if(!t.matches('.chiptx,.acct-t,.regt'))boxes.forEach(b=>{const edges=[[b.x,b.y,b.x+b.w,b.y],[b.x,b.y+b.h,b.x+b.w,b.y+b.h],[b.x,b.y,b.x,b.y+b.h],[b.x+b.w,b.y,b.x+b.w,b.y+b.h]];
        const g={x:tb[i].x-6,y:tb[i].y-4,w:tb[i].w+12,h:tb[i].h+8};if(edges.some(e=>segHits(e,g)))err(si,'text-border',name(t)+' sits on a box border')});
    });
    lines.forEach(l=>{if(badPath(l))err(si,'path',(l.id||l.getAttribute('class'))+' uses a path command the check cannot measure: use absolute M H V L');
      const ss=segs(l);if(!ss.length)return;
      tiles.forEach(T=>{const b={x:T.b.x+4,y:T.b.y+4,w:T.b.w-8,h:T.b.h-8};
        ss.forEach(s=>{if(segHits(s,b))err(si,'line-tile',(l.id||l.getAttribute('class'))+' runs through tile '+(T.node?T.node.id:''))})})});
    svg.querySelectorAll('rect.tile').forEach(r=>{const g=r.nextElementSibling;if(!g||getComputedStyle(r).fill!=='rgb(255, 255, 255)')return;
      const sh=[...g.querySelectorAll('path,circle,rect,ellipse,polygon,text')];
      const vis=sh.some(s=>{const cs=getComputedStyle(s);return[cs.fill,cs.stroke].some(c=>c&&c!=='none'&&c!=='rgb(255, 255, 255)')});
      if(sh.length&&!vis)err(si,'glyph','tile #'+(r.parentElement.id||'?')+' is white and so is its glyph: give the tile the brand colour')});
    svg.querySelectorAll('text.chiptx').forEach(t=>{let c=t.previousElementSibling;
      while(c&&!c.matches('rect.chip'))c=c.previousElementSibling;if(!c)return;
      const tbx=bb(t),cb=bb(c);if(tbx.x+tbx.w>cb.x+cb.w-8)err(si,'chip-fit',name(t)+' runs past its chip by '+Math.round(tbx.x+tbx.w-(cb.x+cb.w-8))+'px')});
  });
  sl.querySelectorAll('.mx-wrap').forEach(w=>{
    if(w.scrollWidth>w.clientWidth+1)err(si,'matrix-overflow','matrix is '+(w.scrollWidth-w.clientWidth)+'px wider than the slide');
    if(w.scrollHeight>w.clientHeight+1)err(si,'matrix-overflow','matrix is '+(w.scrollHeight-w.clientHeight)+'px taller than the slide')});
});
(window.__players||[]).forEach(p=>{
  const svg=document.getElementById(p.svg);const used=new Set();
  if(!svg){err(-1,'step','player svg #'+p.svg+' is not in the page');return}
  p.steps.forEach((s,k)=>[].concat(s.n||[],s.a||[]).forEach(id=>{used.add(id);
    if(!svg.querySelector('[id="'+id+'"]'))err(-1,'step','#'+p.svg+' step '+(k+1)+' names #'+id+', which is not in that svg')}));
  svg.querySelectorAll('path.arr').forEach(a=>{if(!used.has(a.id))err(-1,'unused-arrow','#'+p.svg+' arrow #'+(a.id||'?')+' is in no step')});
});
if(!(window.__players||[]).length)err(-1,'step','no window.__players: player() must register itself');
const pre=document.createElement('pre');pre.id='__check';
pre.textContent=JSON.stringify({slides:slides.length,errors:out,ids:[...document.querySelectorAll('[id]')].map(e=>e.id)});
document.body.appendChild(pre);
},600));
</script>
"""


def chrome():
    for c in CHROME_CANDIDATES:
        p = c if os.path.isabs(c) else shutil.which(c)
        if p and os.path.exists(p):
            return p
    sys.exit("check.py: no Chrome or Chromium found")


def run(c, args):
    return subprocess.run([c, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                           "--virtual-time-budget=6000"] + args,
                          capture_output=True, text=True, timeout=120).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--ledger")
    ap.add_argument("--out")
    ap.add_argument("--no-shots", action="store_true")
    a = ap.parse_args()
    src = open(a.deck, encoding="utf-8").read()
    out = a.out or tempfile.mkdtemp(prefix="deck-check-")
    os.makedirs(out, exist_ok=True)
    c = chrome()

    probe = os.path.join(out, "_probe.html")
    open(probe, "w", encoding="utf-8").write(src + PROBE)
    dom = run(c, ["--window-size=1440,1000", "--dump-dom", "file://" + os.path.abspath(probe)])
    m = re.search(r'<pre id="__check">(.*?)</pre>', dom, re.S)
    if not m:
        sys.exit("check.py: the probe did not run (script error in the page?)")
    import html
    res = json.loads(html.unescape(m.group(1)))
    errors = res["errors"]

    if a.ledger:
        ids = set(res["ids"])
        for n, line in enumerate(open(a.ledger, encoding="utf-8"), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                errors.append({"slide": -1, "kind": "ledger", "msg": f"line {n}: needs 3 fields"})
            elif parts[0] == "-":
                if not parts[1].lower().startswith("left out"):
                    errors.append({"slide": -1, "kind": "ledger", "msg": f"line {n}: '-' needs 'left out: reason'"})
            elif parts[0] not in ids:
                errors.append({"slide": -1, "kind": "ledger", "msg": f"line {n}: #{parts[0]} ({parts[1]}) is not drawn"})

    if not a.no_shots:
        for i in range(res["slides"]):
            for theme in ("light", "dark"):
                f = os.path.join(out, f"_s{i + 1}-{theme}.html")
                inj = f"<script>addEventListener('load',()=>{{document.documentElement.dataset.theme='{theme}';go({i});}});</script>"
                open(f, "w", encoding="utf-8").write(src + inj)
                run(c, ["--window-size=1440,1000",
                        "--screenshot=" + os.path.join(out, f"slide{i + 1}-{theme}.png"),
                        "file://" + os.path.abspath(f)])
                os.remove(f)
    os.remove(probe)

    for e in errors:
        where = f"slide {e['slide'] + 1}" if e["slide"] >= 0 else "page"
        print(f"FAIL {where} [{e['kind']}] {e['msg']}")
    print(f"{len(errors)} problem(s). Screenshots: {out}" if not a.no_shots else f"{len(errors)} problem(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
