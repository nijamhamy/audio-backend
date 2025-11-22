import os
import shutil
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import soundfile as sf

# Detect ffmpeg
FFMPEG_PATH = shutil.which("ffmpeg")
AudioSegment.converter = FFMPEG_PATH

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
async def root():
    return {"message": "Simplified Audio Enhancer Backend Running"}

@app.post("/enhance")
async def enhance_audio(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1].lower()
    input_file = f"input.{ext}"
    wav_file = "input.wav"
    output_file = "enhanced.wav"

    # Save input file
    with open(input_file, "wb") as f:
        f.write(await file.read())

    # Convert to wav mono
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(44100)
    audio.export(wav_file, format="wav")

    # Load audio
    data, sr = sf.read(wav_file)

    # ============================================================
    #          LIGHT ENHANCEMENT (Railway-friendly)
    # ============================================================

    # 1) Remove low-level noise (very light gate)
    threshold = 0.015
    data = np.where(np.abs(data) < threshold, 0, data)

    # 2) Normalize to -1..1
    peak = np.max(np.abs(data))
    if peak > 0:
        data = data / peak

    # 3) Light volume boost
    data = np.clip(data * 1.25, -1.0, 1.0)

    # Save file
    sf.write(output_file, data, sr)

    return FileResponse(
        output_file,
        media_type="audio/wav",
        filename="enhanced.wav",
        headers={"Access-Control-Allow-Origin": "*"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
