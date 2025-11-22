import os
import sys
import shutil
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import soundfile as sf

# Allow large uploads (50MB)
sys.setrecursionlimit(1000000)

# ==========================================
#  Detect FFmpeg
# ==========================================
FFMPEG_PATH = shutil.which("ffmpeg")
if FFMPEG_PATH:
    AudioSegment.converter = FFMPEG_PATH
    print("FFmpeg found:", FFMPEG_PATH)
else:
    print("⚠ Warning: FFmpeg not found")

# ==========================================
#  FastAPI App (50MB upload limit)
# ==========================================
app = FastAPI(max_request_size=1024 * 1024 * 50)

# CORS (Netlify → Railway)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

@app.options("/enhance")
async def options_enhance():
    return JSONResponse(
        {"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/")
async def root():
    return {"message": "Audio Enhancer Backend Running!"}

# ==========================================
#  MAIN AUDIO ENHANCE ROUTE
# ==========================================
@app.post("/enhance")
async def enhance_audio(file: UploadFile = File(...)):
    try:
        ext = file.filename.split(".")[-1].lower()
        raw_file = f"input.{ext}"
        wav_file = "converted.wav"
        out_file = "enhanced.wav"

        # Save file
        with open(raw_file, "wb") as f:
            f.write(await file.read())

        # Convert → wav (mono, 44.1kHz)
        audio = AudioSegment.from_file(raw_file)
        audio = audio.set_channels(1).set_frame_rate(44100)
        audio.export(wav_file, format="wav")

        # Read wav
        data, sr = sf.read(wav_file)

        # Light noise reduction
        data = np.where(np.abs(data) < 0.015, 0, data)

        # Normalize
        peak = np.max(np.abs(data)) or 1.0
        data = data / peak

        # Volume boost
        data = np.clip(data * 1.25, -1.0, 1.0)

        # Save output
        sf.write(out_file, data, sr)

        # Return final file
        return FileResponse(
            out_file,
            media_type="audio/wav",
            filename="enhanced.wav",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as e:
        print("⚠ ERROR:", e)
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )


# ==========================================
#  LOCAL RUN
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
