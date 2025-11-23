import os
import numpy as np
import shutil

# ============================================================
#               FFMPEG CONFIG (LINUX FRIENDLY)
# ============================================================
FFMPEG_PATH = shutil.which("ffmpeg")
FFPROBE_PATH = shutil.which("ffprobe")

print("Using FFmpeg:", FFMPEG_PATH)

if FFMPEG_PATH:
    os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)

from pydub import AudioSegment
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH

# ============================================================
#                     IMPORTS
# ============================================================
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import librosa
import noisereduce as nr
import soundfile as sf
import pyloudnorm as pyln

from pedalboard import (
    Pedalboard,
    Compressor,
    HighpassFilter,
    HighShelfFilter,
    Limiter
)

# ============================================================
#                   FASTAPI APP
# ============================================================
app = FastAPI()

# CORS FIX (Netlify → Railway)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ai-audio-enhancer.netlify.app",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OPTIONS preflight handler
@app.options("/enhance")
async def options_enhance():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

# ============================================================
#                   ROUTES
# ============================================================
@app.get("/")
async def root():
    return {"message": "AI Audio Enhancer Backend is running"}

@app.head("/enhance")
async def head_enhance():
    return {"status": "ok"}

@app.post("/enhance")
async def enhance_audio(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1].lower()
    original_file = f"temp_input.{ext}"
    wav_file = "temp_input.wav"
    output_file = "enhanced_output.wav"

    with open(original_file, "wb") as f:
        f.write(await file.read())

    try:
        audio = AudioSegment.from_file(original_file)
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(44100)
        audio.export(wav_file, format="wav")
    except Exception as e:
        return {"error": f"FFmpeg conversion failed: {str(e)}"}

    try:
        y, sr = librosa.load(wav_file, sr=None)
    except Exception as e:
        return {"error": f"Error loading WAV: {str(e)}"}

    # Noise reduction
    try:
        cleaned = nr.reduce_noise(y=y, sr=sr, prop_decrease=0.65)
    except:
        cleaned = y

    # EQ + compress
    try:
        board = Pedalboard([
            HighpassFilter(80),
            Compressor(threshold_db=-18, ratio=4, attack_ms=5, release_ms=120),
            HighShelfFilter(gain_db=3.0, cutoff_frequency_hz=10000)
        ])
        processed = board(np.expand_dims(cleaned, 0), sr).squeeze()
    except:
        processed = cleaned

    # Loudness normalize
    try:
        meter = pyln.Meter(sr)
        loudness = meter.integrated_loudness(processed)
        normalized = pyln.normalize.loudness(processed, loudness, -16.0)
        normalized = np.clip(normalized, -1.0, 1.0)
    except:
        normalized = processed

    # Limiter
    try:
        limiter = Pedalboard([Limiter(threshold_db=-1.0)])
        final_audio = limiter(np.expand_dims(normalized, 0), sr).squeeze()
    except:
        final_audio = normalized

    # Save final file
    try:
        sf.write(output_file, final_audio.astype(np.float32), sr)
    except Exception as e:
        return {"error": f"Saving failed: {str(e)}"}

    # FINAL RESPONSE WITH CORS HEADERS
    return FileResponse(
        output_file,
        media_type="audio/wav",
        filename="enhanced_audio.wav",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("Starting server on port:", port)
    uvicorn.run("main:app", host="0.0.0.0", port=port)
