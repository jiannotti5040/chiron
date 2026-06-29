# transcribe_final.py — batch transcription with speaker labels

Turns the audio/video files in a folder into speaker-labeled `.docx` transcripts
(Whisper for the words, pyannote for who-said-what).

## The portable part (what lives in the repo)

- `transcribe_final.py` — the program itself
- `requirements.txt` — the exact list of what it needs

**That is the portable form of this tool.** Source + a requirements list is how a Python
program travels in a repo: it's tiny, it diffs cleanly in git, and it runs on any
Apple-Silicon Mac. It does not get "compiled" into one file — see the last section for why.

## To run it

In Terminal, one time, set up its environment:

```
cd "Individual Programs"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Also make sure ffmpeg is present (reads the audio): `brew install ffmpeg`.

Then, to transcribe (this is all you repeat each time):

```
cd "Individual Programs"
source .venv/bin/activate
export HF_TOKEN=paste_your_huggingface_token_here
python transcribe_final.py
```

Output `.docx` files land in the `transcribe_output` folder.

### The Hugging Face token (free, needed for speaker labels)

1. Get a token: <https://huggingface.co/settings/tokens>
2. While signed in, click "Agree" on both model pages so the token may use them:
   - <https://huggingface.co/pyannote/speaker-diarization-3.1>
   - <https://huggingface.co/pyannote/segmentation-3.0>

Without a token you still get a transcript — just no speaker labels.

## Why it isn't a single compiled file

Each run it downloads multi-gigabyte AI models from Hugging Face, uses the Mac's GPU
through Metal, and shells out to `ffmpeg`. None of that can be frozen into a portable
binary — a "successful" compile would still need the internet, ffmpeg, and the token at
run time, and would only work on one exact machine. The source above is the honest,
durable, portable version. The earlier `.exe`-style build was the wrong shape and is safe
to delete.
