#!/usr/bin/env python3
"""Read whisper json, group segments into translation batches of ~target_words words.
Writes momtest_fr/work/en_batches/batch_NNN.txt (one segment per line)."""
import json, os, sys

def main():
    jpath = sys.argv[1]
    outdir = sys.argv[2]
    target_words = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
    os.makedirs(outdir, exist_ok=True)
    data = json.load(open(jpath))
    segs = [s["text"].strip() for s in data["segments"] if s["text"].strip()]
    batches, cur, cw = [], [], 0
    for t in segs:
        cur.append(t); cw += len(t.split())
        if cw >= target_words:
            batches.append(cur); cur, cw = [], 0
    if cur:
        batches.append(cur)
    for i, b in enumerate(batches):
        with open(os.path.join(outdir, f"batch_{i:03d}.txt"), "w") as f:
            f.write("\n".join(b))
    print(f"segments={len(segs)} batches={len(batches)} -> {outdir}")

if __name__ == "__main__":
    main()
