#!/usr/bin/env python3
import os, sys, csv, argparse, math
from datetime import datetime

def esc(s): return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def render_html(title, cols, rows, coach=None):
    show = [c for c in ["company","title","location","remote","posted_at","apply_url"] if c in cols] or cols[:6]
    out = [f"<h3>{esc(title)}</h3>"]
    if coach: out.append(f"<div><b>Coach:</b> {esc(coach)}</div>")
    out.append("<table border=1 cellpadding=4>")
    out.append("<tr>" + "".join(f"<th>{esc(c)}</th>" for c in show) + "</tr>")
    for r in rows:
        cells=[]
        for c in show:
            v=r.get(c,"")
            if c=="apply_url" and v: v=f'<a href="{esc(v)}">Apply</a>'
            cells.append(f"<td>{esc(v)}</td>")
        out.append("<tr>"+"".join(cells)+"</tr>")
    out.append("</table>")
    return "\n".join(out)

def render_text(coach, cols, rows):
    show = [c for c in ["company","title","location","remote","posted_at","apply_url"] if c in cols] or cols[:6]
    out=[]
    if coach: out.append(f"Coach: {coach}")
    for r in rows: out.append(" | ".join(f"{c}: {r.get(c,'')}" for c in show))
    return "\n".join(out)

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",required=True)
    ap.add_argument("--outdir",default="outbox")
    ap.add_argument("--max-rows",type=int,default=50)
    ap.add_argument("--coach",default="Presales focus: demo/POC, APIs, auth, Linux/Python/SQL, remote US/AU.")
    args=ap.parse_args()

    with open(args.csv,newline="",encoding="utf-8") as f:
        r=csv.DictReader(f)
        cols=r.fieldnames or []
        rows=list(r)
    total=len(rows)
    if total==0: sys.exit("[i] CSV has 0 rows.")
    batches=math.ceil(total/max(1,args.max_rows))
    run_id=datetime.now().strftime("%Y%m%d-%H%M%S")
    out_root=os.path.join(args.outdir,run_id); os.makedirs(out_root,exist_ok=True)
    for i in range(batches):
        chunk=rows[i*args.max_rows:(i+1)*args.max_rows]
        subj=f"[ApplyPilot] SE/SC Digest — Batch {i+1}/{batches} ({len(chunk)} roles, total={total})"
        bdir=os.path.join(out_root,f"batch_{i+1:02d}"); os.makedirs(bdir,exist_ok=True)
        open(os.path.join(bdir,"subject.txt"),"w").write(subj)
        open(os.path.join(bdir,"body.txt"),"w").write(render_text(args.coach,cols,chunk))
        open(os.path.join(bdir,"body.html"),"w").write(render_html(subj,cols,chunk,args.coach))
        print(f"[ok] {subj}")
    print(f"[ok] Wrote {batches} batch(es) into {out_root}")
