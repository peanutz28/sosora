"""Local CPU speech recognition; model must be downloaded before starting.

Run from repo root: ml/.venv312/bin/python -m uvicorn beacon.asr_server:app --port 8003
No filename-based transcript lookup and no road-name prompting: text comes from audio.
"""
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

MODEL_PATH = Path(__file__).resolve().parents[1] / 'ml/artifacts/asr-tiny.en'


@asynccontextmanager
async def lifespan(app):
    from faster_whisper import WhisperModel
    app.state.recognizer = WhisperModel(
        str(MODEL_PATH), device='cpu', compute_type='int8', local_files_only=True,
        cpu_threads=4, num_workers=1)
    app.state.recognition_lock = Lock()
    yield


app = FastAPI(title='SOSora local speech recognition', lifespan=lifespan)


def recognize(app, audio):
    # Serialize CPU work and consume the lazy segment iterator under the lock.
    with app.state.recognition_lock:
        segments, _ = app.state.recognizer.transcribe(
            BytesIO(audio), language='en', beam_size=5, condition_on_previous_text=False)
        return ' '.join(segment.text.strip() for segment in segments).strip()


@app.get('/health')
def health():
    return {'status': 'ready', 'model': 'tiny.en', 'device': 'cpu', 'offline': True}


@app.post('/audio/transcriptions')
async def transcriptions(file: UploadFile = File(...), model: str = Form('tiny.en')):
    if model != 'tiny.en':
        raise HTTPException(422, 'This server serves only tiny.en')
    audio = await file.read(20_000_001)
    if not audio or len(audio) > 20_000_000:
        raise HTTPException(422, 'Audio must be 1 byte to 20 MB')
    try:
        text = await run_in_threadpool(recognize, app, audio)
    except Exception as exc:
        raise HTTPException(422, 'Audio could not be transcribed') from exc
    if not text:
        raise HTTPException(422, 'No speech recognized')
    return {'text': text, 'model': 'tiny.en', 'mode': 'live'}
