#!/usr/bin/env python3
"""Local web dashboard for the EN->FR audiobook pipeline.
Usage: python3 webapp.py <book_work_dir> [port]
Serves a live page with stage bars + a TTS progress chart at http://127.0.0.1:<port>."""
import json, os, re, glob, sys, http.server, socketserver, subprocess

W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath("work")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8731
OUTDIR = os.path.dirname(W)


def alive(pat):
    return subprocess.run(["pgrep", "-f", pat], capture_output=True).returncode == 0


def transcription():
    done = os.path.exists(f"{W}/full_en.json"); p = 1.0 if done else 0.0; note = ""
    log = f"{W}/whisper.log"
    if not done and os.path.exists(log):
        m = re.findall(r"(\d+)/(\d+)\s*\[", open(log, errors="ignore").read().replace("\r", "\n"))
        if m:
            p = int(m[-1][0]) / max(1, int(m[-1][1]))
    if done:
        note = f"{len(json.load(open(f'{W}/full_en.json'))['segments'])} segments"
    return {"name": "Transcription EN", "pct": p, "state": "done" if done else "running", "note": note}


def translation():
    en = glob.glob(f"{W}/en_batches/batch_*.txt"); fr = glob.glob(f"{W}/fr_batches/batch_*.json")
    if not en:
        return {"name": "Traduction FR", "pct": 0, "state": "pending", "note": ""}
    return {"name": "Traduction FR", "pct": len(fr) / len(en),
            "state": "done" if len(fr) >= len(en) else "running", "note": f"{len(fr)}/{len(en)} lots"}


def tts():
    master = f"{W}/master_fr_chunks.json"
    out = {"name": "Synthese TTS", "pct": 0, "state": "pending", "note": "", "done": 0,
           "total": 0, "eta_min": None, "rate_per_min": None, "series": []}
    if not os.path.exists(master):
        return out
    total = len(json.load(open(master)))
    done = len([f for f in glob.glob(f"{W}/full_chunks/chunk_*.wav") if os.path.getsize(f) > 1000])
    out.update(total=total, done=done, pct=(done / total if total else 0),
               state="running" if alive("tts_build.py") else ("done" if done >= total and total else "idle"))
    log = f"{W}/tts.log"
    if os.path.exists(log):
        series = [{"t": round(int(m.group(2)) / 60, 2), "done": int(m.group(1))}
                  for m in re.finditer(r"\[(\d+)/\d+\][^\n]*?\|\s*(\d+)s elapsed", open(log, errors="ignore").read())]
        if len(series) > 300:
            series = series[::len(series) // 300] + [series[-1]]
        out["series"] = series
        if len(series) >= 2 and done < total and series[-1]["t"]:
            rate = series[-1]["done"] / series[-1]["t"]
            out["rate_per_min"] = round(rate, 2)
            out["eta_min"] = round((total - done) / rate, 1) if rate else None
    return out


def final():
    mp3 = glob.glob(f"{OUTDIR}/*_FR_*.mp3") or glob.glob(f"{OUTDIR}/*FR*.mp3")
    if mp3 and os.path.getsize(mp3[0]) > 10000:
        return {"name": "MP3 final", "pct": 1.0, "state": "done", "note": os.path.basename(mp3[0])}
    return {"name": "MP3 final", "pct": 0, "state": "pending", "note": ""}


def build_status():
    s1, s2, s3, s4 = transcription(), translation(), tts(), final()
    overall = 0.10 * s1["pct"] + 0.05 * s2["pct"] + 0.82 * s3["pct"] + 0.03 * s4["pct"]
    return {"stages": [s1, s2, s4], "tts": s3, "overall": overall}


HTML = r"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audiobook → FR · Avancement</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>:root{--bg:#0b0f17;--card:#121826;--ink:#e6edf3;--mut:#8b97a8;--accent:#5b8cff;--ok:#34d399;--run:#fbbf24}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
.wrap{max-width:920px;margin:0 auto;padding:28px 20px 60px}h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 24px;font-size:14px}
.card{background:var(--card);border:1px solid #1f2937;border-radius:14px;padding:20px;margin-bottom:18px}
.big{display:flex;align-items:baseline;gap:12px;margin-bottom:14px}.big .n{font-size:46px;font-weight:700;letter-spacing:-1px}.big .lbl{color:var(--mut)}
.bar{height:12px;border-radius:8px;background:#1f2937;overflow:hidden}.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),#8b5cff);transition:width .6s}
.stage{margin:14px 0}.stage .row{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;vertical-align:middle}
.done .dot{background:var(--ok)}.running .dot{background:var(--run);animation:pulse 1.6s infinite}.pending .dot{background:#475569}.idle .dot{background:#475569}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(251,191,36,.5)}70%{box-shadow:0 0 0 8px rgba(251,191,36,0)}100%{box-shadow:0 0 0 0 rgba(251,191,36,0)}}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:6px}.kpi{background:#0e1420;border:1px solid #1f2937;border-radius:10px;padding:12px}
.kpi .v{font-size:24px;font-weight:600}.kpi .k{color:var(--mut);font-size:12px}.mut{color:var(--mut);font-size:12px}canvas{margin-top:8px}</style></head>
<body><div class="wrap"><h1>🎧 Audiobook → Français</h1><p class="sub">pipeline 100 % local (Whisper + Qwen TTS)</p>
<div class="card"><div class="big"><span class="n" id="overall">–</span><span class="lbl">avancement global</span></div>
<div class="bar"><i id="overallBar" style="width:0%"></i></div><div class="grid" id="kpis"></div></div>
<div class="card"><strong>Synthèse vocale — chunks générés dans le temps</strong><canvas id="chart" height="120"></canvas><div class="mut" id="chartNote"></div></div>
<div class="card" id="stages"></div><p class="mut">Rafraîchissement auto 5 s · <span id="ts"></span></p></div>
<script>let chart;const ICON={done:'done',running:'running',pending:'pending',idle:'idle'};
function fmtEta(m){if(m==null)return '–';const h=Math.floor(m/60),mm=Math.round(m%60);return h+'h'+String(mm).padStart(2,'0');}
async function tick(){let d;try{d=await (await fetch('/api/status',{cache:'no-store'})).json();}catch(e){return;}
document.getElementById('overall').textContent=(d.overall*100).toFixed(1)+'%';document.getElementById('overallBar').style.width=(d.overall*100)+'%';
const t=d.tts;document.getElementById('kpis').innerHTML=`<div class="kpi"><div class="v">${t.done}/${t.total}</div><div class="k">chunks audio</div></div><div class="kpi"><div class="v">${t.rate_per_min??'–'}</div><div class="k">chunks / min</div></div><div class="kpi"><div class="v">${fmtEta(t.eta_min)}</div><div class="k">temps restant estimé</div></div>`;
const all=[d.stages[0],d.stages[1],{name:t.name,pct:t.pct,state:t.state,note:t.done+'/'+t.total+' chunks'},d.stages[2]];
document.getElementById('stages').innerHTML=all.map(s=>{const cl=ICON[s.state]||'pending';return `<div class="stage ${cl}"><div class="row"><span><span class="dot"></span>${s.name} <span class="mut">${s.note||''}</span></span><span>${(s.pct*100).toFixed(1)}%</span></div><div class="bar"><i style="width:${s.pct*100}%"></i></div></div>`;}).join('');
const xs=t.series.map(p=>p.t),ys=t.series.map(p=>p.done);
if(!chart){chart=new Chart(document.getElementById('chart'),{type:'line',data:{labels:xs,datasets:[{label:'chunks',data:ys,borderColor:'#5b8cff',backgroundColor:'rgba(91,140,255,.15)',fill:true,tension:.25,pointRadius:0,borderWidth:2}]},options:{animation:false,scales:{x:{title:{display:true,text:'minutes écoulées',color:'#8b97a8'},ticks:{color:'#8b97a8',maxTicksLimit:8},grid:{color:'#1f2937'}},y:{title:{display:true,text:'chunks',color:'#8b97a8'},suggestedMax:t.total,ticks:{color:'#8b97a8'},grid:{color:'#1f2937'}}},plugins:{legend:{display:false}}}});}else{chart.data.labels=xs;chart.data.datasets[0].data=ys;chart.options.scales.y.suggestedMax=t.total;chart.update('none');}
document.getElementById('chartNote').textContent=`Objectif : ${t.total} chunks · état : ${t.state}`;document.getElementById('ts').textContent='maj '+new Date().toLocaleTimeString();}
tick();setInterval(tick,5000);</script></body></html>"""


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/status"):
            body = json.dumps(build_status()).encode(); ct = "application/json"
        else:
            body = HTML.encode(); ct = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as httpd:
        print(f"serving on http://127.0.0.1:{PORT}  (work dir: {W})")
        httpd.serve_forever()
