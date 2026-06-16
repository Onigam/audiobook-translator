#!/usr/bin/env python3
"""Unified CLI progress across the EN->FR audiobook pipeline stages.
Usage: python3 status.py <book_work_dir>   (dir containing full_en.json, fr_batches/, full_chunks/, master_fr_chunks.json)
"""
import json, os, re, glob, subprocess, sys

W = sys.argv[1] if len(sys.argv) > 1 else "work"


def pct_bar(p, n=24):
    p = max(0.0, min(1.0, p)); f = int(p * n)
    return "[" + "#" * f + "-" * (n - f) + f"] {p*100:5.1f}%"


def alive(pat):
    return subprocess.run(["pgrep", "-f", pat], capture_output=True).returncode == 0


def transcription():
    done = os.path.exists(f"{W}/full_en.json"); p, note = 0.0, ""
    log = f"{W}/whisper.log"
    if os.path.exists(log):
        txt = open(log, errors="ignore").read().replace("\r", "\n")
        m = re.findall(r"(\d+)/(\d+)\s*\[", txt)
        if m and not done:
            p = int(m[-1][0]) / max(1, int(m[-1][1]))
    if done:
        p = 1.0; note = f"{len(json.load(open(f'{W}/full_en.json'))['segments'])} segments"
    return p, ("done" if done else "running"), note


def translation():
    en = glob.glob(f"{W}/en_batches/batch_*.txt"); fr = glob.glob(f"{W}/fr_batches/batch_*.json")
    if not en:
        return 0.0, "pending", "not split"
    return len(fr) / len(en), ("done" if len(fr) >= len(en) else "running"), f"{len(fr)}/{len(en)} lots"


def tts():
    master = f"{W}/master_fr_chunks.json"
    if not os.path.exists(master):
        return 0.0, "pending", "chunks pas prets"
    total = len(json.load(open(master)))
    done = len([f for f in glob.glob(f"{W}/full_chunks/chunk_*.wav") if os.path.getsize(f) > 1000])
    note = f"{done}/{total} chunks"
    log = f"{W}/tts.log"
    if os.path.exists(log) and 0 < done < total:
        el = re.findall(r"\|\s*(\d+)s elapsed", open(log, errors="ignore").read())
        if el:
            eta = int((int(el[-1]) / done) * (total - done))
            note += f" | ETA ~{eta//3600}h{(eta%3600)//60:02d}"
    st = "running" if alive("tts_build.py") else ("done" if done >= total and total else "idle")
    return (done / total if total else 0), st, note


def main():
    s1, s2, s3 = transcription(), translation(), tts()
    overall = 0.12 * s1[0] + 0.06 * s2[0] + 0.82 * s3[0]
    icon = {"running": "RUN", "done": "OK ", "pending": "...", "idle": "..."}
    print("=" * 46)
    for name, (p, st, note) in [("1 Transcription EN", s1), ("2 Traduction  FR ", s2), ("3 Synthese   TTS ", s3)]:
        print(f"[{icon.get(st,'?')}] {name} {pct_bar(p)}  {note}")
    print("-" * 46)
    print(f"     GLOBAL        {pct_bar(overall)}")
    print("=" * 46)


if __name__ == "__main__":
    main()
