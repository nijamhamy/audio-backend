import os
import sys
import shutil
import numpy as np
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import soundfile as sf

# Allow large uploads
sys.setrecursionlimit(1000000)

# ================================
#  Detect FFmpeg
# ================================
FFMPEG_PATH = shutil.which("ffmpeg")
if FFMPEG_PATH:
    AudioSegment.converter = FFMPEG_PATH
    print("FFmpeg found:", FFMPEG_PATH)
else:
    print("⚠ Warning: FFmpeg not found")


# ================================
#  FastAPI app
# ================================
app = FastAPI()

# Global CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


# Apply CORS to ALL responses manually
def add_cors(response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.options("/enhance")
async def cors_enhance():
    return add_cors(JSONResponse({"message": "OK"}))


@app.get("/")
async def home():
    return add_cors(JSONResponse({"message": "Backend running"}))


# ================================
#  MAIN ENHANCE ENDPOINT
# ================================
@app.post("/enhance")
async def enhance_audio(file: UploadFile = File(...)):
    try:
        ext = file.filename.split(".")[-1].lower()
        raw_file = f"input.{ext}"
        wav_file = "converted.wav"
        out_file = "enhanced.wav"

        # Save input
        with open(raw_file, "wb") as f:
            f.write(await file.read())

        # Convert → wav
        audio = AudioSegment.from_file(raw_file)
        audio = audio.set_channels(1).set_frame_rate(44100)
        audio.export(wav_file, format="wav")

        # Load wav
        data, sr = sf.read(wav_file)

        # Light noise reduction
        data = np.where(np.abs(data) < 0.015, 0, data)

        # Normalize
        peak = np.max(np.abs(data)) or 1.0
        data = data / peak

        # Volume boost
        data = np.clip(data * 1.25, -1.0, 1.0)

        # Save file
        sf.write(out_file, data, sr)

        # Send audio back
        response = FileResponse(
            out_file,
            media_type="audio/wav",
            filename="enhanced.wav",
        )
        return add_cors(response)

    except Exception as e:
        error = JSONResponse({"error": str(e)}, status_code=500)
        return add_cors(error)


# ================================
#  LOCAL RUN
# ================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
