import os
import shutil
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import soundfile as sf

# ============================================================
#               DETECT FFMPEG (Safe for Railway)
# ============================================================
FFMPEG_PATH = shutil.which("ffmpeg")
if FFMPEG_PATH:
    AudioSegment.converter = FFMPEG_PATH
else:
    print("⚠ FFmpeg not found! Audio conversion may fail.")


# ============================================================
#                  FASTAPI APP
# ============================================================
app = FastAPI()

# CORS - FULL OPEN (Netlify → Railway)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow any frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# OPTIONS preflight
@app.options("/enhance")
async def options_enhance():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ============================================================
#                     ROUTES
# ============================================================
@app.get("/")
async def root():
    return {"message": "Simplified AI Audio Enhancer Backend Running!"}


@app.post("/enhance")
async def enhance_audio(file: UploadFile = File(...)):
    try:
        ext = file.filename.split(".")[-1].lower()
        input_file = f"input.{ext}"
        wav_file = "input.wav"
        output_file = "enhanced.wav"

        # Save uploaded file
        with open(input_file, "wb") as f:
            f.write(await file.read())

        # Convert to WAV mono 44.1KHz
        audio = AudioSegment.from_file(input_file)
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(44100)
        audio.export(wav_file, format="wav")

        # Load audio
        data, sr = sf.read(wav_file)

        # ============================================================
        #           LIGHTWEIGHT ENHANCEMENT (RAM-SAFE)
        # ============================================================

        # 1) Remove low background noise
        threshold = 0.015
        data = np.where(np.abs(data) < threshold, 0, data)

        # 2) Normalize
        peak = np.max(np.abs(data))
        if peak > 0:
            data = data / peak

        # 3) Light volume boost
        data = np.clip(data * 1.25, -1.0, 1.0)

        # Save final output
        sf.write(output_file, data, sr)

        return FileResponse(
            output_file,
            media_type="audio/wav",
            filename="enhanced.wav",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )


# ============================================================
#                    LOCAL RUN SUPPORT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
