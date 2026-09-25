"""Build the audio evaluation set once; reuse it forever.

    uv run python -m evals.audio.build_set            # generate missing clips only
    uv run python -m evals.audio.build_set --force    # regenerate everything

Reads utterances.yaml x voices.yaml, synthesizes each pair with Cartesia TTS, and
writes clips/<hash>.wav plus one manifest.jsonl line per clip. The hash covers
text + voice id + TTS model, so a rerun only generates what is missing, and the
manifest pins everything needed to reproduce a clip.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
import wave
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

CLIPS = HERE / "clips"
MANIFEST = HERE / "manifest.jsonl"
TTS_MODEL = "sonic-3"
SAMPLE_RATE = 16000  # telephony-adjacent; what the STT models are happiest with
API = "https://api.cartesia.ai/tts/bytes"


def clip_hash(text: str, voice_id: str, model: str) -> str:
    return hashlib.sha1(f"{model}|{voice_id}|{text}".encode()).hexdigest()[:16]


def synthesize(text: str, voice_id: str, key: str) -> bytes:
    """Return a well-formed 16 kHz mono PCM WAV. The API streams its WAV, so the
    header carries a placeholder length; we rewrap the PCM payload."""
    r = httpx.post(API, timeout=60, headers={"X-API-Key": key, "Cartesia-Version": "2025-04-16"}, json={
        "model_id": TTS_MODEL, "transcript": text, "voice": {"id": voice_id}, "language": "en",
        "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": SAMPLE_RATE},
    })
    r.raise_for_status()
    data_at = r.content.find(b"data")
    pcm = r.content[data_at + 8:] if data_at >= 0 else r.content[44:]  # skip "data" tag + length
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(pcm)
    return buf.getvalue()


def main(force: bool) -> None:
    key = os.environ["CARTESIA_API_KEY"]
    utterances = yaml.safe_load((HERE / "utterances.yaml").read_text())
    voices = yaml.safe_load((HERE / "voices.yaml").read_text())
    CLIPS.mkdir(exist_ok=True)
    existing = {}
    if MANIFEST.exists() and not force:
        for line in MANIFEST.read_text().splitlines():
            d = json.loads(line); existing[d["hash"]] = d
    rows, made, t0 = [], 0, time.perf_counter()
    for v in voices:
        for u in utterances:
            h = clip_hash(u["text"], v["id"], TTS_MODEL)
            path = CLIPS / f"{h}.wav"
            if h in existing and path.exists():
                rows.append(existing[h]); continue
            wav = synthesize(u["text"], v["id"], key)
            path.write_bytes(wav)
            with wave.open(str(path)) as w:
                secs = round(w.getnframes() / w.getframerate(), 2)
            rows.append({"hash": h, "file": f"clips/{h}.wav", "utterance_id": u["id"], "kind": u["kind"], "text": u["text"],
                         "drugs": u.get("drugs", []), "numbers": u.get("numbers", []),
                         "voice_id": v["id"], "voice": v["name"], "accent": v["accent"], "gender": v["gender"],
                         "tts_model": TTS_MODEL, "sample_rate": SAMPLE_RATE, "seconds": secs,
                         "generated": time.strftime("%Y-%m-%d")})
            made += 1
            print(f"  + {v['name']:8s} {u['id']} {secs:5.2f}s  {u['text'][:60]}", flush=True)
    MANIFEST.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    total = sum(r["seconds"] for r in rows)
    print(f"{len(rows)} clips in manifest ({made} new, {len(rows) - made} reused), {total/60:.1f} min of audio, "
          f"{len(voices)} voices x {len(utterances)} utterances, {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    main(ap.parse_args().force)
