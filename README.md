# audiobook-translator

Pipeline 100 % local pour traduire des livres audio anglais en **MP3 français**, avec archivage des résultats.

Chaîne : **transcription** (Whisper) → **traduction EN→FR** → **synthèse vocale** (Qwen TTS via Voicebox) → **MP3 + transcripts**.

## Prérequis (macOS)

- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) + `ffmpeg` (`brew install yt-dlp ffmpeg`)
- [`openai-whisper`](https://github.com/openai/whisper) en CLI (`brew install openai-whisper`) — modèle `small` suffit
- [Voicebox](https://voicebox.sh) lancé : expose une API locale sur `http://127.0.0.1:17493` avec **Qwen TTS 1.7B** chargé et au moins une voix FR
  - ⚠️ L'endpoint `/transcribe` de Voicebox est cassé (bug d'empaquetage librosa) → on utilise le CLI `whisper` à la place.

### Voix FR disponibles (profile_id Voicebox)

| Voix | profile_id |
|---|---|
| Laurent Baffie | `6437fe5f-b87c-4e79-8724-27049c4c3910` |
| Philippe Lucas | `ef15978b-d1a0-4b63-a0a9-2492c1ff74b5` |

## Étapes

Soit `W=work/<book>` le dossier de travail (ignoré par git).

```bash
# 0. (option) télécharger la source
yt-dlp -x --audio-format mp3 --audio-quality 0 -o "%(title)s.%(ext)s" "<youtube-url>"

# 1. Transcription EN  → W/full_en.json + W/full_en.txt
pipeline/transcribe.sh "<input.mp3>" "$W" small 2>&1 | tee "$W/whisper.log"

# 2. Découpage en lots de traduction → W/en_batches/batch_NNN.txt
python3 pipeline/split_for_translation.py "$W/full_en.json" "$W/en_batches" 1400

# 3. Traduction EN→FR (faite par des agents LLM, 1 par lot) → W/fr_batches/batch_NNN.json
#    Chaque lot = un tableau JSON de chunks FR (1–2 phrases, ~250 car. max), prêts pour le TTS.

# 4. Réassemblage des chunks dans l'ordre → W/master_fr_chunks.json
python3 pipeline/combine_chunks.py "$W/fr_batches" "$W/master_fr_chunks.json"

# 5. Synthèse vocale + assemblage MP3 (reprenable, retries réseau)
python3 pipeline/tts_build.py "$W/master_fr_chunks.json" "$W/full_chunks" "books/<book>/<Name>_FR.mp3" \
  6437fe5f-b87c-4e79-8724-27049c4c3910   # profile_id (ou env VOICE_PROFILE_ID)
```

### Suivi

```bash
python3 pipeline/status.py "$W"          # tableau CLI
python3 pipeline/webapp.py "$W" 8731     # dashboard web live → http://127.0.0.1:8731
```

## Repères de performance (Apple Silicon, Whisper small + Qwen 1.7B)

- Transcription : ~2,3× temps réel
- Synthèse TTS : ~3,5× temps réel (un livre de 3 h ≈ ~10 h de génération)

## Archivage

`books/<slug>/` contient les livrables versionnés : MP3 FR final (< 100 Mo), texte FR, transcription EN, et `meta.json` (source, voix, stats). Les sources lourdes et les fichiers intermédiaires (`work/`, `*.wav`) sont **exclus** (cf. `.gitignore`).
