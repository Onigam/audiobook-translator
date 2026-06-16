#!/usr/bin/env bash
# Transcribe an audio file to English JSON+TXT with openai-whisper.
# Usage: ./transcribe.sh <input_audio> <out_dir> [model]
set -euo pipefail
IN="$1"; OUT="$2"; MODEL="${3:-small}"
mkdir -p "$OUT"
# 16kHz mono speeds up whisper
WAV="$OUT/full_en.wav"
ffmpeg -v error -y -i "$IN" -ac 1 -ar 16000 "$WAV"
whisper "$WAV" --model "$MODEL" --language en --task transcribe \
  --output_format json --output_dir "$OUT" --fp16 False --verbose False
# flatten segments to a readable txt
python3 - "$OUT/full_en.json" "$OUT/full_en.txt" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
open(sys.argv[2], "w").write("\n".join(s["text"].strip() for s in d["segments"]))
print("segments:", len(d["segments"]))
PY
echo "transcription done -> $OUT/full_en.json"
