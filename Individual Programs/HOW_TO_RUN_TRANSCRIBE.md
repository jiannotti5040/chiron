# How to run the transcriber

You do **not** need to build anything or touch Python. There is one file to run.

## To transcribe

1. Put your audio/video files in your `transcribe_input` folder (on the Desktop, in the
   Walter Reed Project folder).
2. Double-click **`Transcribe.command`** in this folder.
3. A Terminal window opens and does the work. When it says **Finished**, your `.docx`
   transcripts are in the `transcribe_output` folder.

That's the whole thing.

## The very first time only

The first double-click sets itself up: it installs `ffmpeg` (if needed) and builds a
Python environment with Whisper and the speaker-labeling models. That download is a few
gigabytes and takes 5–15 minutes. **It happens once.** Every run after is just step 1–3 above.

It will also ask, once, for a free **Hugging Face token** (used to label who is speaking):

- Get a token at <https://huggingface.co/settings/tokens>
- While signed in, click "Agree" on these two model pages so the token is allowed to use them:
  - <https://huggingface.co/pyannote/speaker-diarization-3.1>
  - <https://huggingface.co/pyannote/segmentation-3.0>
- Paste the token when asked. It's saved privately on your Mac; you won't be asked again.

If you skip the token, you still get a transcript — just without speaker labels.

## Why this isn't a single "app" file

This tool uses the Mac's GPU (through PyTorch/MLX) and downloads AI models as it runs, so
it can't be frozen into one portable file — the earlier `.exe`-style build was the wrong
shape for it and is safe to delete. The launcher above is the normal, reliable way tools
like this are run.

## If something errors

Copy whatever the Terminal window shows and send it over. The most common first-time
snags are: ffmpeg not installed (the launcher handles it if you have Homebrew), or the
Hugging Face model terms not yet accepted (the two links above).
