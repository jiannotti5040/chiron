#!/bin/bash
# Transcribe.command — double-click this to transcribe.
# Whisper transcription + speaker labels -> .docx (Walter Reed batch).
# The first run sets everything up; every run after just transcribes.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/transcribe_final.py"
ENV_DIR="$HOME/.local/transcribe_env"
TOKEN_FILE="$HOME/.local/transcribe_hf_token"
PY="$ENV_DIR/bin/python"
PIP="$ENV_DIR/bin/pip"

echo "=================================================="
echo "  Transcribe — Walter Reed batch"
echo "=================================================="

# --- ffmpeg: reads the audio/video files ---
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo
  echo "ffmpeg is required and isn't installed yet."
  if command -v brew >/dev/null 2>&1; then
    echo "Installing it with Homebrew (one time)..."
    brew install ffmpeg || { echo "ffmpeg install failed. Run:  brew install ffmpeg"; echo "Press Return to close."; read -r _; exit 1; }
  else
    echo "Homebrew isn't installed. Get it at https://brew.sh, then run this again."
    echo "Press Return to close."; read -r _; exit 1
  fi
fi

# --- one-time Python environment (PyTorch + Whisper + diarization) ---
if [ ! -x "$PY" ]; then
  echo
  echo "First-time setup: building the Python environment."
  echo "This downloads several GB and can take 5-15 minutes."
  echo "You only do this once."
  echo
  mkdir -p "$HOME/.local"
  python3 -m venv "$ENV_DIR" || { echo "Could not create the environment."; echo "Press Return to close."; read -r _; exit 1; }
  "$PIP" install --upgrade pip
  if ! "$PIP" install mlx-whisper torch torchaudio soundfile "pyannote.audio" python-docx; then
    echo
    echo "A dependency failed to install. Copy the error above and send it to me."
    echo "Press Return to close."; read -r _; exit 1
  fi
  echo "Environment ready."
fi

# --- Hugging Face token (free; needed for the speaker labels) ---
if [ -z "${HF_TOKEN:-}" ] && [ -f "$TOKEN_FILE" ]; then
  HF_TOKEN="$(cat "$TOKEN_FILE")"
fi
if [ -z "${HF_TOKEN:-}" ]; then
  echo
  echo "A free Hugging Face token is needed for speaker labels."
  echo "  1. Get a token:  https://huggingface.co/settings/tokens"
  echo "  2. Accept the model terms (one click, while signed in):"
  echo "       https://huggingface.co/pyannote/speaker-diarization-3.1"
  echo "       https://huggingface.co/pyannote/segmentation-3.0"
  echo
  printf "Paste your token (or press Return to skip speaker labels): "
  read -r HF_TOKEN
  if [ -n "$HF_TOKEN" ]; then
    echo "$HF_TOKEN" > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
    echo "Saved to $TOKEN_FILE — you won't be asked again."
  fi
fi
export HF_TOKEN

# --- run ---
echo
echo "Starting transcription..."
echo
"$PY" "$SCRIPT"
STATUS=$?
echo
if [ "$STATUS" -eq 0 ]; then
  echo "Finished."
else
  echo "Stopped with an error (shown above)."
fi
echo "Press Return to close."
read -r _
