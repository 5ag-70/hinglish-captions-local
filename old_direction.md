CAPTIONING PROJECT — OLD EXPERIMENTS / USEFUL NOTES

Current direction:
- Use Sarvam for Hindi/Hinglish transcription.
- Sarvam results are substantially better for my Hinglish videos.
- Do NOT use the old Whisper experiments as the main workflow.

Desired architecture:
1. transcription.py
   - Makes the Sarvam API call ONLY.
   - Saves the complete response as JSON.
   - Do not repeatedly call the API while adjusting subtitles.

2. Subtitle/post-processing script
   - Reads the existing JSON.
   - Creates:
     - .srt
     - .vtt
     - .txt
   - All subtitle optimisation happens here without another API call.

3. Subtitle layout option
   - Ask:
       1 = One line
       2 = Two lines

   - One line → normally vertical Instagram Reels / YouTube Shorts.
   - Two lines → normally horizontal YouTube videos.

General subtitle goals:
- Natural phrase boundaries.
- Avoid cutting a sentence in awkward places.
- Keep captions readable rather than blindly following ASR segments.
- Preserve accurate timestamps from the transcription response.
- Hinglish should stay Romanized.
- English technical terms should remain English.

Useful FFmpeg command to extract WAV directly from video:

ffmpeg -i "video.MP4" \
  -map 0:a:0 \
  -vn \
  -ac 1 \
  -ar 16000 \
  -c:a pcm_s16le \
  "audio.wav"

Previous experiments:
- openai-whisper large-v3 on CPU:
  Good/relatively better transcription, but extremely slow.
  Roughly 7–28 minutes for ~50 sec Hinglish video.

- MLX Whisper large-v3 on M1 Pro GPU:
  Very fast (~30–40 sec), but Hinglish accuracy was poor.

- whisper.cpp large-v3 + Metal:
  Faster than CPU.
  Best tested settings included:
    --language hi
    --beam-size 5
    --best-of 5
    --temperature 0
    --no-flash-attn
    --no-fallback

  One test completed in ~43 sec.
  Accuracy improved but was still not reliable enough.
  Also saw malformed/zero-duration subtitle cues.

- Old romanize_hinglish.py:
  Only transliterated Devanagari → Roman Hindi.
  It could NOT fix ASR/transcription mistakes.
  This approach is no longer necessary if Sarvam directly gives good Hinglish.

Conclusion:
Sarvam transcription + JSON-first workflow is the direction going forward.
Do not spend more time optimising Whisper unless Sarvam becomes unsuitable.