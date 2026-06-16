#!/usr/bin/env python3
"""Generate French audio from a JSON list of text chunks via the Voicebox TTS API,
then concatenate into a single MP3. Resumable: skips chunks already rendered.

Usage:
  python3 tts_build.py <chunks.json> <out_wav_dir> <out.mp3> [profile_id]

profile_id defaults to env VOICE_PROFILE_ID, else the Laurent Baffie voice.
"""
import json, sys, os, subprocess, urllib.request, time

BASE = os.environ.get("VOICEBOX_URL", "http://127.0.0.1:17493")
DEFAULT_PROFILE = "6437fe5f-b87c-4e79-8724-27049c4c3910"  # Laurent Baffie
MODEL = os.environ.get("VOICE_MODEL", "1.7B")


def generate(profile_id, text, seed=None, retries=4):
    body = {"profile_id": profile_id, "text": text, "language": "fr", "model_size": MODEL}
    if seed is not None:
        body["seed"] = seed
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(BASE + "/generate", data=data,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise last


def main():
    chunks_file, out_dir, out_mp3 = sys.argv[1], sys.argv[2], sys.argv[3]
    profile_id = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("VOICE_PROFILE_ID", DEFAULT_PROFILE)
    chunks = json.load(open(chunks_file))
    os.makedirs(out_dir, exist_ok=True)
    wavs = []
    t0 = time.time()
    for i, text in enumerate(chunks):
        text = text.strip()
        if not text:
            continue
        wav = os.path.join(out_dir, f"chunk_{i:05d}.wav")
        if os.path.exists(wav) and os.path.getsize(wav) > 1000:
            wavs.append(wav); continue
        try:
            resp = generate(profile_id, text, seed=42 + i)
            src = resp["audio_path"]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src,
                            "-ac", "1", "-ar", "24000", wav], check=True)
        except Exception as e:
            print(f"[{i+1}/{len(chunks)}] !! FAILED after retries, skipping: {e}", flush=True)
            with open(os.path.join(out_dir, "FAILED.log"), "a") as lf:
                lf.write(f"{i}\t{text}\n")
            continue
        wavs.append(wav)
        el = time.time() - t0
        print(f"[{i+1}/{len(chunks)}] {resp['duration']:.1f}s audio | {el:.0f}s elapsed | {text[:55]}...",
              flush=True)
    # concat with small silence gaps
    listf = os.path.join(out_dir, "concat_list.txt")
    sil = os.path.join(out_dir, "_sil.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", "0.35", sil], check=True)
    with open(listf, "w") as f:
        for w in wavs:
            f.write(f"file '{os.path.abspath(w)}'\n")
            f.write(f"file '{os.path.abspath(sil)}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", listf, "-c:a", "libmp3lame", "-q:a", "2", out_mp3], check=True)
    print(f"\nDONE -> {out_mp3}")


if __name__ == "__main__":
    main()
