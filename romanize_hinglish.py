#!/usr/bin/env python3
"""Local, deterministic Devanagari -> readable Roman Hindi, never translation.

Known Hindi spellings and loanwords use an explicit, editable glossary. Unlisted
words use a conservative phonetic fallback and are listed in the audit. This is
not a general Hindi pronunciation model and cannot repair recognition errors.
Existing non-Devanagari spans (including English, URLs and casing) are untouched.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

DEV = r"\u0900-\u097f\ua8e0-\ua8ff"
# Punctuation and digits are handled separately, not as parts of words.
WORD = re.compile(r"[\u0900-\u0963\u0971-\u097f\ua8e0-\ua8ff\u200c\u200d]+")
VOWELS = dict(zip("अआइईउऊऋॠऌॡऍऎएऐऑऒओऔ", [
    "a", "aa", "i", "ee", "u", "oo", "ri", "ri", "li", "li",
    "e", "e", "e", "ai", "o", "o", "o", "au"]))
MATRAS = dict(zip("ािीुूृॄॅॆेैॉॊोौॢॣ", [
    "aa", "i", "ee", "u", "oo", "ri", "ri", "e", "e", "e", "ai",
    "o", "o", "o", "au", "li", "li"]))
CONS = dict(zip("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळऴऱऩ", [
    "k", "kh", "g", "gh", "ng", "ch", "chh", "j", "jh", "ny",
    "t", "th", "d", "dh", "n", "t", "th", "d", "dh", "n",
    "p", "ph", "b", "bh", "m", "y", "r", "l", "v", "sh", "sh", "s", "h",
    "l", "l", "r", "n"]))
NUKTA = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "r", "ढ": "rh",
         "फ": "f", "य": "y", "र": "r", "न": "n", "ल": "l"}
SRT_STAMP = r"[0-9]{2,}:[0-9]{2}:[0-9]{2}[,.][0-9]{3}"
VTT_STAMP = r"(?:[0-9]{2,}:)?[0-9]{2}:[0-9]{2}\.[0-9]{3}"
SRT_TIME = re.compile(rf"^(?P<start>{SRT_STAMP})[ \t]+-->[ \t]+(?P<end>{SRT_STAMP})(?:[ \t]+.*)?$")
VTT_TIME = re.compile(rf"^(?P<start>{VTT_STAMP})[ \t]+-->[ \t]+(?P<end>{VTT_STAMP})(?:[ \t]+.*)?$")
# Treat tags, voice annotations, inline timestamps and entities as opaque markup.
CAPTION_MARKUP = re.compile(r"<[^>\r\n]*>|&(?:#[0-9]+|#[xX][0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);")
DEFAULT_GLOSSARY = Path(__file__).with_name("hinglish_glossary.json")


def normal(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\u200c", "").replace("\u200d", ""))


def phonetic_word(word: str) -> str:
    """Approximate Hindi phonetics. Exceptions belong in the glossary, not guesses.

    Inherent schwas are represented separately from explicit vowel marks. Delete
    a final inherent schwa, then conservative medial V-C-schwa-C-V cases from
    right to left. Do not remove explicit final vowels (e.g. kiya -> kiyaa).
    """
    text = unicodedata.normalize("NFD", word).replace("\u200c", "").replace("\u200d", "")
    units: list[dict[str, Any]] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in CONS:
            consonant = CONS[c]
            if i + 1 < len(text) and text[i + 1] == "़":
                consonant = NUKTA.get(c, consonant)
                i += 1
            units.append({"c": consonant, "v": "a", "implicit": True})
        elif c in VOWELS:
            units.append({"c": "", "v": VOWELS[c], "implicit": False})
        elif c in MATRAS:
            if not units or not units[-1]["c"]:
                raise ValueError(f"Detached vowel sign in {word!r}; correct the source text.")
            units[-1]["v"] = MATRAS[c]
            units[-1]["implicit"] = False
        elif c == "्":
            if not units or not units[-1]["c"]:
                raise ValueError(f"Detached virama in {word!r}")
            units[-1]["v"] = ""
            units[-1]["implicit"] = False
        elif c in "ँं":
            # Nasalization is conventionally written n; glossary handles main/mein.
            units.append({"c": "", "v": "n", "implicit": False, "mark": True})
        elif c == "ः":
            units.append({"c": "", "v": "h", "implicit": False, "mark": True})
        elif c == "ऽ":
            units.append({"c": "", "v": "'", "implicit": False, "mark": True})
        elif c in "॒॑॓॔":
            # Vedic pitch accents do not add a spoken consonant or vowel.
            pass
        elif c == "ॐ":
            units.append({"c": "", "v": "om", "implicit": False})
        elif c == "़":
            raise ValueError(f"Detached nukta in {word!r}")
        else:
            raise ValueError(f"Unsupported character U+{ord(c):04X} in {word!r}; add a glossary entry.")
        i += 1
    if len(units) > 1 and units[-1].get("implicit"):
        units[-1]["v"] = ""
        units[-1]["implicit"] = False
    for i in range(len(units) - 2, 0, -1):
        previous, current, following = units[i-1:i+2]
        if (current.get("implicit") and previous["v"]
                and not previous.get("mark") and following["c"]
                and following["v"] and not following.get("mark")):
            current["v"] = ""
            current["implicit"] = False
    return "".join(u["c"] + u["v"] for u in units)


class Romanizer:
    def __init__(self, glossary: Path = DEFAULT_GLOSSARY):
        data = json.loads(glossary.read_text(encoding="utf-8"))
        self.entries: dict[str, str] = {}
        self.kinds: dict[str, str] = {}
        for kind in ("hindi_spellings", "technical_terms"):
            for source, target in data.get(kind, {}).items():
                key = normal(source)
                if not key or not re.fullmatch(r"[\u0900-\u097f\ua8e0-\ua8ff\s]+", key):
                    raise ValueError(f"Glossary keys must contain only Devanagari and spaces: {source!r}")
                if not isinstance(target, str) or not target or re.search(f"[{DEV}]", target) or any(c in target for c in "\n\r\t"):
                    raise ValueError(f"Invalid Roman glossary value for {source!r}")
                self.entries[key] = target
                self.kinds[key] = kind
        keys = sorted(self.entries, key=len, reverse=True)
        # Match only Devanagari keys, never already-Roman words such as main, is, or US.
        alternatives = [re.escape(k).replace(r"\ ", r"[ \t]+") for k in keys]
        self.phrases = re.compile(
            rf"(?<![\u0900-\u0963\u0971-\u097f\ua8e0-\ua8ff])(?:{'|'.join(alternatives)})(?![\u0900-\u0963\u0971-\u097f\ua8e0-\ua8ff])") if keys else None
        self.fallback_words: dict[str, str] = {}
        self.applied_terms: dict[str, str] = {}
        self.replacement_characters_seen = 0

    def text(self, text: str) -> str:
        self.replacement_characters_seen += text.count("\ufffd")
        # Normalize only the Devanagari runs; do not normalize accented Latin names.
        text = WORD.sub(lambda m: normal(m.group()), text)
        # Segment at glossary matches to avoid feeding their English values back in.
        parts: list[str] = []
        cursor = 0
        if self.phrases:
            for match in self.phrases.finditer(text):
                parts.append(self._fallback(text[cursor:match.start()]))
                key = re.sub(r"[ \t]+", " ", match.group())
                parts.append(self.entries[key])
                if self.kinds[key] == "technical_terms":
                    self.applied_terms[key] = self.entries[key]
                cursor = match.end()
        parts.append(self._fallback(text[cursor:]))
        result = "".join(parts)
        if re.search(f"[{DEV}]", result):
            raise ValueError("Unconverted Devanagari remains; inspect the glossary/source.")
        return result

    def _fallback(self, text: str) -> str:
        def convert(match: re.Match) -> str:
            source = match.group()
            value = phonetic_word(source)
            self.fallback_words[source] = value
            return value
        result = WORD.sub(convert, text)
        result = result.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
        return result.replace("॥", ".").replace("।", ".")

    def audit(self) -> dict:
        return {"method": "explicit glossary plus approximate Hindi phonetic fallback; no translation model",
                "fallback_spellings_to_review": self.fallback_words,
                "technical_spellings_applied": self.applied_terms,
                "requires_review": bool(self.fallback_words or self.replacement_characters_seen),
                "unicode_replacement_character_count": self.replacement_characters_seen,
                "limits": "Does not correct ASR errors, infer missing words, or guarantee every name/pronunciation."}


def line_parts(line: str) -> tuple[str, str]:
    text = line.rstrip("\r\n")
    return text, line[len(text):]


def timestamp_ms(stamp: str) -> int:
    parts = stamp.replace(",", ".").split(":")
    if len(parts) == 2:
        hours, minutes, seconds = 0, int(parts[0]), parts[1]
    else:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), parts[2]
    seconds, milliseconds = map(int, seconds.split("."))
    if minutes > 59 or seconds > 59:
        raise ValueError(f"Invalid timestamp: {stamp!r}")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def validate_times(start: int, end: int, previous_start: int, label: str) -> None:
    # Overlapping cues are valid; only starts must be in chronological order.
    if end < start:
        raise ValueError(f"{label}: end precedes start.")
    if start < previous_start:
        raise ValueError(f"{label}: start precedes the previous cue/row start.")


def caption_text(text: str, romanizer: Romanizer) -> str:
    output: list[str] = []
    cursor = 0
    for match in CAPTION_MARKUP.finditer(text):
        output.append(romanizer.text(text[cursor:match.start()]))
        output.append(match.group())
        cursor = match.end()
    output.append(romanizer.text(text[cursor:]))
    return "".join(output)


def romanize_srt(source: str, romanizer: Romanizer) -> tuple[str, str]:
    """Change text lines only. Preserve every index, timing line and line ending."""
    lines = source.splitlines(keepends=True)
    output: list[str] = []
    transcript: list[str] = []
    state = "index"
    text_lines: list[str] = []
    cue_count = 0
    previous_start = -1
    for line in lines:
        stripped, newline = line_parts(line)
        if not stripped.strip():
            if state == "time":
                raise ValueError("SRT cue has an index but no timing line.")
            if state == "text" and not text_lines:
                raise ValueError("SRT cue has no subtitle text.")
            if text_lines:
                transcript.append(" ".join(text_lines))
                text_lines = []
            state = "index"
            output.append(line)
        elif state == "index":
            if not stripped.lstrip("\ufeff").strip().isdigit():
                raise ValueError(f"Invalid SRT index: {stripped!r}")
            output.append(line)
            state = "time"
        elif state == "time":
            match = SRT_TIME.fullmatch(stripped)
            if not match:
                raise ValueError(f"Invalid SRT timestamp line: {stripped!r}")
            start, end = timestamp_ms(match["start"]), timestamp_ms(match["end"])
            validate_times(start, end, previous_start, "SRT cue")
            previous_start = start
            output.append(line)
            cue_count += 1
            state = "text"
        else:
            if SRT_TIME.fullmatch(stripped):
                raise ValueError("SRT cues must be separated by a blank line.")
            value = caption_text(stripped, romanizer)
            output.append(value + newline)
            text_lines.append(value.strip())
    if state == "time" or (state == "text" and not text_lines):
        raise ValueError("Incomplete final SRT cue.")
    if text_lines:
        transcript.append(" ".join(text_lines))
    if not cue_count:
        raise ValueError("No SRT cues found.")
    return "".join(output), "\n".join(transcript) + "\n"


def romanize_vtt(source: str, romanizer: Romanizer) -> str:
    """Preserve structure and metadata; convert only cue payload text."""
    lines = source.splitlines(keepends=True)
    if not lines or not re.fullmatch(r"WEBVTT(?:[ \t].*)?", line_parts(lines[0])[0]):
        raise ValueError("VTT must start with a WEBVTT header.")
    if "-->" in lines[0]:
        raise ValueError("Invalid WEBVTT header.")
    output = [lines[0]]
    cursor = 1
    # Header metadata extends to the first blank line. It is never caption text.
    while cursor < len(lines) and line_parts(lines[cursor])[0].strip():
        if "-->" in lines[cursor]:
            raise ValueError("VTT header must end with a blank line before cues.")
        output.append(lines[cursor])
        cursor += 1
    cue_count = 0
    previous_start = -1
    while cursor < len(lines):
        if not line_parts(lines[cursor])[0].strip():
            output.append(lines[cursor])
            cursor += 1
            continue
        block_start = cursor
        while cursor < len(lines) and line_parts(lines[cursor])[0].strip():
            cursor += 1
        block = lines[block_start:cursor]
        first = line_parts(block[0])[0]
        if re.fullmatch(r"NOTE(?:[ \t].*)?", first) or first in ("STYLE", "REGION"):
            output.extend(block)
            continue
        timing_index = 0 if VTT_TIME.fullmatch(first) else 1
        if timing_index and "-->" in first:
            raise ValueError(f"Invalid VTT timestamp line: {first!r}")
        if len(block) <= timing_index:
            raise ValueError(f"VTT cue is missing its timestamp line: {first!r}")
        timing = line_parts(block[timing_index])[0]
        match = VTT_TIME.fullmatch(timing)
        if not match:
            raise ValueError(f"Invalid VTT timestamp line: {timing!r}")
        if len(block) <= timing_index + 1:
            raise ValueError("VTT cue has no subtitle text.")
        start, end = timestamp_ms(match["start"]), timestamp_ms(match["end"])
        validate_times(start, end, previous_start, "VTT cue")
        previous_start = start
        output.extend(block[:timing_index + 1])
        for line in block[timing_index + 1:]:
            text, newline = line_parts(line)
            if "-->" in text:
                raise ValueError("Invalid VTT cue text; cues must be separated by a blank line.")
            output.append(caption_text(text, romanizer) + newline)
        cue_count += 1
    if not cue_count:
        raise ValueError("No VTT cues found.")
    return "".join(output)


def romanize_tsv(source: str, romanizer: Romanizer) -> str:
    """Whisper TSV: keep the header, literal millisecond fields and line endings."""
    lines = source.splitlines(keepends=True)
    if not lines or line_parts(lines[0])[0] != "start\tend\ttext":
        raise ValueError("TSV must have the header: start<TAB>end<TAB>text.")
    if len(lines) < 2:
        raise ValueError("No TSV rows found.")
    output = [lines[0]]
    previous_start = -1
    for number, line in enumerate(lines[1:], 2):
        text, newline = line_parts(line)
        columns = text.split("\t")
        if len(columns) != 3 or not all(re.fullmatch(r"[0-9]+", x) for x in columns[:2]):
            raise ValueError(f"Invalid TSV row {number}; expected integer start/end and one text column.")
        start, end = int(columns[0]), int(columns[1])
        validate_times(start, end, previous_start, f"TSV row {number}")
        previous_start = start
        output.append("\t".join((columns[0], columns[1], romanizer.text(columns[2]))) + newline)
    return "".join(output)


def paths_match(first: Path, second: Path) -> bool:
    return first.resolve() == second.resolve() or (
        first.exists() and second.exists() and first.samefile(second))


def validate_outputs(outputs: dict[str, Path], sources: list[Path]) -> None:
    """Check every destination, including TXT/audit, before creating any output."""
    paths = list(outputs.values())
    for index, destination in enumerate(paths):
        for source in sources:
            if paths_match(destination, source):
                raise ValueError(f"Output must not overwrite an input file: {destination}")
        if destination.exists() and not destination.is_file():
            raise ValueError(f"Output is not a regular file: {destination}")
        for other in paths[:index]:
            if paths_match(destination, other):
                raise ValueError(f"Output paths refer to the same file: {destination} and {other}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("srt", type=Path, help="existing/corrected SRT; no audio extraction or Whisper run")
    p.add_argument("--output-prefix", type=Path, required=True)
    p.add_argument("--glossary", type=Path, default=DEFAULT_GLOSSARY)
    p.add_argument("--vtt", type=Path, help="optional source VTT; preserve its existing timing and metadata")
    p.add_argument("--tsv", type=Path, help="optional source Whisper TSV; preserve its millisecond fields")
    args = p.parse_args()
    inputs = {"srt": args.srt}
    if args.vtt is not None:
        inputs["vtt"] = args.vtt
    if args.tsv is not None:
        inputs["tsv"] = args.tsv
    suffixes = [".srt", ".txt"] + [f".{kind}" for kind in inputs if kind != "srt"] + [".romanization.json"]
    outputs = {suffix: Path(str(args.output_prefix) + suffix) for suffix in suffixes}
    validate_outputs(outputs, [*inputs.values(), args.glossary])
    converted: dict[str, str] = {}
    format_audits: dict[str, dict] = {}
    # No output is written unless all explicitly requested inputs are valid.
    for kind, source in inputs.items():
        engine = Romanizer(args.glossary)
        content = source.read_bytes().decode("utf-8-sig")
        if kind == "srt":
            converted[".srt"], converted[".txt"] = romanize_srt(content, engine)
        elif kind == "vtt":
            converted[".vtt"] = romanize_vtt(content, engine)
        else:
            converted[".tsv"] = romanize_tsv(content, engine)
        format_audits[kind] = {"source": str(source.resolve()),
                              "output": str(outputs[f".{kind}"].resolve()), **engine.audit()}
    # Keep legacy audit fields; union spelling lists instead of counting duplicate
    # representations. The legacy replacement count describes the primary SRT.
    audit = {key: value for key, value in format_audits["srt"].items() if key not in ("source", "output")}
    audit["fallback_spellings_to_review"] = {
        word: spelling for details in format_audits.values()
        for word, spelling in details["fallback_spellings_to_review"].items()}
    audit["technical_spellings_applied"] = {
        word: spelling for details in format_audits.values()
        for word, spelling in details["technical_spellings_applied"].items()}
    audit["requires_review"] = any(details["requires_review"] for details in format_audits.values())
    audit["replacement_character_count_scope"] = "Primary SRT only; each supplied format has a separate count under formats. TXT is derived from SRT."
    audit["formats"] = format_audits
    converted[".romanization.json"] = json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for suffix, content in converted.items():
        outputs[suffix].write_bytes(content.encode("utf-8"))
    print("Romanized caption text; original timestamps and TSV millisecond fields unchanged.")
    print("Source completeness was NOT checked. Output: " + " / ".join(str(path) for path in outputs.values()))
    if audit["requires_review"]:
        print("REVIEW REQUIRED: approximate spellings or replacement characters remain; see the audit JSON.")
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Error: {exc}")
