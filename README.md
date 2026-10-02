# Whisper Hinglish Captions

Generate Roman-script Hinglish captions from a video using FFmpeg, local Whisper transcription, and an editable Hindi spelling glossary.

> **Before you start:** This workflow runs on your computer. Install Python and FFmpeg, then create and activate the virtual environment using the steps below. Internet access is needed to install the tools and download the Whisper model on first use. The script uses the large-v3 model on CPU, which can take substantial time and memory.

These instructions are for **macOS Terminal**. Linux users can adapt installation steps; Windows users need a compatible Bash environment and different setup instructions.

## What this project does

```text
Video → extracted MP3 → Whisper captions → Roman-script Hinglish captions
```

1. `caption.sh` extracts the first audio track using FFmpeg.
2. Whisper transcribes it locally and saves the original caption files.
3. `romanize_hinglish.py` converts Devanagari text into Roman letters using a glossary and approximate phonetic rules.
4. You review spelling and timing, then import the SRT into your video editor.

Romanization changes the writing system, not the meaning. It does not translate Hindi into English or repair words Whisper misheard. Existing English text stays unchanged. This project preserves subtitle timing rather than splitting captions into a new layout.

## Basic terms

| Term | Meaning |
| --- | --- |
| Terminal | The app where you type commands and press Return to run them. |
| Python | The software that runs the conversion script and Whisper. |
| Virtual environment | A folder containing this project's Python tools and packages. |
| FFmpeg | A tool for extracting audio from video. |
| Whisper | A speech recognition model that turns audio into text. |
| SRT / VTT | Subtitle formats containing text and timestamps. |
| TSV | A text table; here it contains start/end times in milliseconds and caption text. |
| JSON | Structured data; here it stores transcripts, spelling rules, or review reports. |
| Glossary | A list of Hindi words and their preferred Roman spellings. |

## Files in the project

| File or folder | Purpose |
| --- | --- |
| `caption.sh` | Runs extraction, transcription, and Hinglish conversion. |
| `romanize_hinglish.py` | Converts existing SRT, and optionally VTT/TSV, without rerunning Whisper. |
| `hinglish_glossary.json` | Editable Hindi spellings and technical terms. |
| `requirement.txt` | Python packages with pinned versions. The filename is singular. |
| `Apple_Pay_In_India - 1080p.mp4` | Included sample video. |
| `Apple_Pay_In_India - 1080p_audio.mp3` | Included extracted audio. |
| `original_captions/` | Original Whisper captions and transcript files. |
| `hinglish_captions/` | Romanized captions, transcript, and spelling review report. |

The included caption examples still use `4K` in their names. New runs on the `1080p.mp4` sample create files with `1080p` names.

## First-time setup

### 1. Open Terminal and get the project

Press **Command + Space**, type **Terminal**, and press **Return**.

On the GitHub repository page, click **Code**, choose **HTTPS**, and copy the URL. In Terminal, type `git clone ` (including the space), paste the URL, and press Return. If macOS asks to install command-line developer tools, complete that installation and retry.

If you have already cloned the project, skip cloning again. Enter your downloaded project folder: type `cd `, drag the folder from Finder into Terminal, and press Return. This uses your own path, regardless of the repository's name or where you saved it.

Check that you are in the right folder:

```bash
pwd
ls
```

You should see `caption.sh`, `romanize_hinglish.py`, `hinglish_glossary.json`, and `requirement.txt`.

Copy only commands from the boxes below, not the triple backticks. Run one step at a time. Keep filenames containing spaces in double quotes.

### 2. Install Python

Check whether Python is available:

```bash
python3 --version
```

If it is missing, install Python 3 using the macOS installer from [Python's official website](https://www.python.org/downloads/macos/). Reopen Terminal, return to the project folder, and check again. Package compatibility also depends on the pinned versions in `requirement.txt`; stop and check any installation errors.

### 3. Install FFmpeg

```bash
ffmpeg -version
```

If it is missing, install Homebrew by following [its official instructions](https://brew.sh/), including the final “Next steps” instructions. Then run:

```bash
brew install ffmpeg
ffmpeg -version
```

FFmpeg is a separate tool; installing Python packages alone does not install it. See [Whisper's official setup guide](https://github.com/openai/whisper#setup) for its dependency requirements.

### 4. Create and activate a Python environment

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirement.txt
```

`.venv` is the environment name. If your installation uses `python` instead of `python3`, create it with `python -m venv .venv`. Once activated, use `python` as shown in the rest of this guide.

Create the environment once. Activate it each time you open a new Terminal session. The script uses the tools in your active environment and does not activate one for you.

Check the tools:

```bash
python -c "import whisper; print('Whisper is ready')"
whisper --help
```

Whisper downloads the selected model when first needed. Allow time, internet access, and disk space for that download. See [the official Whisper repository](https://github.com/openai/whisper) for model details.

## Practice first: convert existing captions

This quick exercise does not run Whisper or download a model. With your environment active, run:

```bash
python romanize_hinglish.py "original_captions/Apple_Pay_In_India - 4K_audio.srt" \
  --vtt "original_captions/Apple_Pay_In_India - 4K_audio.vtt" \
  --tsv "original_captions/Apple_Pay_In_India - 4K_audio.tsv" \
  --output-prefix "practice_captions/apple_pay_hinglish"
```

Copy the complete command, including the backslashes: they continue the command onto the next line.

Expected files in `practice_captions/`:

- `apple_pay_hinglish.srt`
- `apple_pay_hinglish.vtt`
- `apple_pay_hinglish.tsv`
- `apple_pay_hinglish.txt`
- `apple_pay_hinglish.romanization.json`

Open the folder:

```bash
open practice_captions
```

You may see **REVIEW REQUIRED**. This means files were created but some words used approximate spellings or contained replacement characters. Read the `.romanization.json` report and review those words. A direct conversion returns exit code `2` in this case; it is different from a failed conversion.

## Runbook: create captions for a video

### Step 1. Prepare your session

Open Terminal, enter your cloned project folder using `cd` or the Finder drag method above, then activate the environment:

```bash
source .venv/bin/activate
```

Put your video in the project folder. For the following example, use a copy named `My Video.mp4`, or replace that name with your actual filename.

### Step 2. Run the complete workflow

```bash
bash caption.sh "My Video.mp4"
```

To use the included sample instead:

```bash
bash caption.sh "Apple_Pay_In_India - 1080p.mp4"
```

The script prints extraction or audio-reuse messages, then `Transcribing...`, then `Converting to Hinglish...`. Wait for it to finish. The current configuration uses **large-v3, CPU, eight threads, and FP16 disabled**. Processing can be slow; no fixed completion time is guaranteed.

### Step 3. Find the outputs

For `My Video.mp4`, output is saved **beside the input video**:

```text
My Video_audio.mp3
original_captions/
  My Video_audio.srt
  My Video_audio.vtt
  My Video_audio.tsv
  My Video_audio.txt
  My Video_audio.json
hinglish_captions/
  My Video_hinglish.srt
  My Video_hinglish.vtt
  My Video_hinglish.tsv
  My Video_hinglish.txt
  My Video_hinglish.romanization.json
```

If your video is in another folder, these folders are created there, not necessarily inside the repository. For the sample video, replace `My Video` with `Apple_Pay_In_India - 1080p`.

### Step 4. Review the result

Open `hinglish_captions/` in Finder and import the SRT into your video editor. Check the whole recording for correct words, names, technical terms, timing, line length, and reading speed.

There is no interactive one-line/two-line selector in this project. The converter preserves the source subtitle structure and timestamps; adjust layout and styling in your editor. Very long cues may need manual splitting.

The review JSON lists fallback words and glossary technical spellings applied. Glossary matches are spelling choices, not proof that Whisper heard the correct word. Correct recognition mistakes in the original captions or in your final editor track.

### Step 5. Improve spellings without transcribing again

Open `hinglish_glossary.json` in a plain-text/code editor. Add exact Devanagari-to-Roman mappings under `hindi_spellings` or `technical_terms`. For example:

```json
"एप्पल": "Apple"
```

Keep valid JSON: double quotes around keys and values, commas between entries, and no comma after the last entry. Save the file, then rerun only conversion:

```bash
python romanize_hinglish.py "original_captions/My Video_audio.srt" \
  --vtt "original_captions/My Video_audio.vtt" \
  --tsv "original_captions/My Video_audio.tsv" \
  --output-prefix "hinglish_captions/My Video_hinglish"
```

You can omit `--vtt` and `--tsv` if you only need SRT and text. SRT is required; the output prefix determines the destination names. If correcting original text in multiple formats, update each format you pass in: changing the SRT does not change the VTT or TSV.

### Step 6. Save your final captions

Keep edited final copies under separate names. Repeated runs overwrite generated outputs with the same names. When finished:

```bash
deactivate
```

## Running again and audio caching

The script reuses the extracted MP3 when it is nonempty and at least as new as the video. It still reruns Whisper on every full workflow run.

To extract audio again regardless of the cache:

```bash
bash caption.sh "My Video.mp4" --force-audio
```

Use conversion alone when only changing spelling. Use unique video basenames to keep different projects' outputs separate. The script selects the first audio track; check that this contains the speech you want.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| Folder or file not found | Check `pwd` and `ls`; use the real filename and quote paths with spaces. |
| `python3` is missing | Install Python, reopen Terminal, and check again. |
| `ffmpeg` is missing | Install FFmpeg and follow Homebrew's PATH instructions. |
| `whisper` or `python` is unavailable | Activate `.venv` and confirm dependency installation succeeded. |
| A pinned package version cannot be installed | Read the full error and check Python/platform compatibility. Ask the maintainer to review `requirement.txt`; do not assume installation completed. |
| First run is downloading or slow | Allow the model download and CPU transcription to finish. Keep Terminal open. |
| Memory error / process killed | The configured model may exceed available resources. A smaller model requires changing `--model large-v3` in `caption.sh`; speed and accuracy will differ. |
| No audio stream | Try a video with audio; the script uses its first audio track. |
| Extraction or transcription failed | Read the error. Successfully cached audio is kept; unfinished extraction is removed. |
| `REVIEW REQUIRED` / conversion exit code 2 | Inspect the spelling report and generated captions. The wrapper treats this as completed with review needed. |
| Glossary JSON error | Check quotes, commas, and the reported invalid entry. |
| Wrong Roman spelling | Add a glossary mapping, then rerun conversion only. |
| Words are wrong or missing | Correct the transcription; romanization cannot reconstruct speech or check transcript completeness. |
| Caption layout is too long | Adjust or split cues in your subtitle editor. There is no layout menu in this workflow. |
| Edited captions disappeared after rerun | Generated files are overwritten. Save final edits under separate names. |

When asking for help, include the command and error text, but remove private transcript content.

## Verification

The documented converter was checked on the included SRT, VTT, and TSV, producing all five outputs in a temporary folder. It returned the expected review-needed status. The Bash script passed a syntax check. Fresh dependency installation, complete Whisper transcription, model download, and editor import were not tested for this README.
