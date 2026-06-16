#!/usr/bin/env python3
"""Combine fr_batches/batch_NNN.json (each a JSON array of French text chunks)
into one ordered master JSON array for TTS."""
import json, os, sys, glob

def main():
    indir, outfile = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(indir, "batch_*.json")))
    master = []
    for fp in files:
        arr = json.load(open(fp))
        if not isinstance(arr, list):
            raise SystemExit(f"{fp} is not a JSON array")
        master.extend(x.strip() for x in arr if x and x.strip())
    json.dump(master, open(outfile, "w"), ensure_ascii=False, indent=1)
    words = sum(len(c.split()) for c in master)
    print(f"files={len(files)} chunks={len(master)} words~={words} -> {outfile}")

if __name__ == "__main__":
    main()
