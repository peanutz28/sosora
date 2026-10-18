"""Speech to text for SOSora Beacon voice reports.

Radio is voice. The Beacon (Raspberry Pi + USB mic) records a WAV and posts it to
POST /api/radio/audio; this module turns it into text for the radio pipeline.

Configuration (all optional):
  ASR_BASE_URL   OpenAI-compatible server exposing POST {base}/audio/transcriptions
                 (e.g. an NVIDIA ASR NIM / Parakeet served on our Brev GPU).
  ASR_MODEL      model name sent with the request.
  ASR_API_KEY    bearer token if the server needs one.

TODO(beacon/ASR owner): confirm with organizers that the ASR model does not count toward
the 33B generative-LM cap (it is a speech recognizer, not a generative LM), then serve it
on Brev next to Nemotron Lightning and record latency in docs/VLLM_RESULTS.md.
"""
from __future__ import annotations

import os

import httpx

from app.ml_client import demo_mode


class ASRUnavailable(RuntimeError):
    pass


# SIMULATED demo recordings: a file named demo_<key>.wav replays this transcript when no
# ASR server is configured, so the video never depends on a live model.
DEMO_TRANSCRIPTS = {
    "demo_hero": ("[SIMULATED] Command, Engine 4... the bridge on Warren Wilson Road is gone, river took it... "
                  "three families on the far side, we can't get across. Over."),
}


async def transcribe(audio: bytes, filename: str = "audio.wav") -> dict:
    base = os.getenv("ASR_BASE_URL", "").rstrip("/")
    stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if not base:
        if stem in DEMO_TRANSCRIPTS:
            return {"text": DEMO_TRANSCRIPTS[stem], "mode": "cached_demo_transcript", "model": None}
        raise ASRUnavailable("ASR_BASE_URL is not configured")
    headers = {"Authorization": "Bearer " + os.environ["ASR_API_KEY"]} if os.getenv("ASR_API_KEY") else {}
    data = {"model": os.getenv("ASR_MODEL", "nvidia/parakeet-tdt-0.6b-v2"), "response_format": "json"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(base + "/audio/transcriptions", headers=headers, data=data,
                                         files={"file": (filename, audio, "audio/wav")})
            response.raise_for_status()
            text = (response.json().get("text") or "").strip()
    except (httpx.HTTPError, ValueError) as exc:
        if demo_mode() and stem in DEMO_TRANSCRIPTS:
            return {"text": DEMO_TRANSCRIPTS[stem], "mode": "cached_demo_transcript", "model": None}
        raise ASRUnavailable(f"ASR request failed: {type(exc).__name__}") from exc
    if not text:
        raise ASRUnavailable("ASR returned no text")
    return {"text": text, "mode": "live", "model": data["model"]}
