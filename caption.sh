#!/bin/bash
set -e

# Usage: ./caption.sh <video-file> [--force-audio]
filename="${1:-}"
force_audio="${2:-}"

if [[ -z "$filename" || $# -gt 2 ]]; then
    echo "Usage: $0 <video-file> [--force-audio]" >&2
    exit 1
fi
if [[ -n "$force_audio" && "$force_audio" != "--force-audio" ]]; then
    echo "Unknown option: $force_audio" >&2
    exit 1
fi
if [[ ! -f "$filename" ]]; then
    echo "Error: File '$filename' not found." >&2
    exit 1
fi

source "${VENV_DIR:-$HOME/.pyenv/versions/openai}/bin/activate"
set -uo pipefail

for tool in ffmpeg whisper python; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Error: '$tool' is not available in this environment." >&2
        exit 1
    fi
done

# Check conversion files before extracting or running Whisper.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for file in romanize_hinglish.py hinglish_glossary.json; do
    if [[ ! -f "$script_dir/$file" ]]; then
        echo "Error: Missing $script_dir/$file" >&2
        exit 1
    fi
done

[[ "$filename" == /* ]] || filename="$PWD/$filename"
output_dir="${filename%/*}"
original_caption_dir="$output_dir/original_captions"
hinglish_caption_dir="$output_dir/hinglish_captions"
name="${filename##*/}"
stem="${name%.*}"
[[ -n "$stem" ]] || stem="$name"
audio="$output_dir/${stem}_audio.mp3"
source_prefix="$original_caption_dir/${stem}_audio"
output_prefix="$hinglish_caption_dir/${stem}_hinglish"

mkdir -p -- "$original_caption_dir" "$hinglish_caption_dir"

if [[ -e "$audio" && ! -f "$audio" ]]; then
    echo "Error: '$audio' exists but is not a regular file." >&2
    exit 1
fi

# Remove only an unfinished extraction, never the completed audio cache.
temp_audio=""
cleanup() {
    if [[ -n "$temp_audio" ]]; then
        rm -f -- "$temp_audio"
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ -z "$force_audio" && -s "$audio" && ! "$filename" -nt "$audio" ]]; then
    echo "Reusing existing audio: $audio"
else
    echo "Extracting audio..."
    temp_audio="$(mktemp "${audio}.tmp.XXXXXX")"

    if ! ffmpeg -nostdin -hide_banner -loglevel error -y \
        -i "$filename" \
        -map 0:a:0 -vn \
        -c:a libmp3lame -f mp3 \
        "$temp_audio"; then
        echo "Error: Audio extraction failed." >&2
        exit 1
    fi
    if [[ ! -s "$temp_audio" ]]; then
        echo "Error: Audio extraction returned an empty file." >&2
        exit 1
    fi

    mv -f -- "$temp_audio" "$audio"
    temp_audio=""
fi

echo "Transcribing..."
if ! whisper "$audio" \
    --model large-v3 \
    --fp16 False \
    --threads 8 \
    --output_dir "$original_caption_dir" \
    --output_format all; then
    echo "Error: Transcription failed. Cached audio has been kept." >&2
    exit 1
fi

echo "Converting to Hinglish..."
conversion_status=0
python "$script_dir/romanize_hinglish.py" \
    "${source_prefix}.srt" \
    --vtt "${source_prefix}.vtt" \
    --tsv "${source_prefix}.tsv" \
    --output-prefix "$output_prefix" || conversion_status=$?

if [[ "$conversion_status" -eq 2 ]]; then
    echo "Hinglish files created; some spellings need review."
elif [[ "$conversion_status" -ne 0 ]]; then
    echo "Error: Hinglish conversion failed." >&2
    exit "$conversion_status"
fi

echo "Done!"
echo "Audio kept: $audio"
echo "Original captions: $original_caption_dir"
echo "Hinglish subtitles: ${output_prefix}.srt"
echo "Hinglish transcript: ${output_prefix}.txt"
echo "Hinglish WebVTT: ${output_prefix}.vtt"
echo "Hinglish TSV: ${output_prefix}.tsv"
