import os
import numpy as np

# ============================================================
#               FFMPEG CONFIG (VERY IMPORTANT)
# ============================================================
FFMPEG_PATH = r"C:\\ffmpeg\\ffmpeg-8.0-essentials_build\\ffmpeg-8.0-essentials_build\\bin\\ffmpeg.exe"
FFPROBE_PATH = r"C:\\ffmpeg\\ffmpeg-8.0-essentials_build\\ffmpeg-8.0-essentials_build\\bin\\ffprobe.exe"

os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)
os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
os.environ["FFPROBE_BINARY"] = FFPROBE_PATH

print("Using FFmpeg:", FFMPEG_PATH)

from pydub import AudioSegment
from pydub.utils import which
AudioSegment.converter = which("ffmpeg") or FFMPEG_PATH
AudioSegment.ffprobe = which("ffprobe") or FFPROBE_PATH

# ============================================================
#                     IMPORTS
# ============================================================
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import librosa
import noisereduce as nr
import soundfile as sf
import pyloudnorm as pyln

# Adobe-style AI enhancement
from demucs.apply import apply_model
from demucs.pretrained import get_model

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

# ---------------- ADD CORS (REQUIRED FOR FRONTEND) ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow all frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#                   ENHANCE AUDIO ROUTE
# ============================================================
@app.post("/enhance")
async def enhance_audio(file: UploadFile = File(...)):

    # ---------------- FILE NAMES ----------------
    ext = file.filename.split(".")[-1].lower()
    original_file = f"temp_input.{ext}"
    wav_file = "temp_input.wav"
    output_file = "enhanced_output.wav"

    # ---------------- SAVE FILE ----------------
    with open(original_file, "wb") as f:
        f.write(await file.read())

    # ---------------- CONVERT TO WAV ----------------
    try:
        audio = AudioSegment.from_file(original_file)
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(44100)
        audio.export(wav_file, format="wav")
    except Exception as e:
        return {"error": f"FFmpeg conversion failed: {str(e)}"}

    # ---------------- LOAD WAV ----------------
    try:
        y, sr = librosa.load(wav_file, sr=None)
    except Exception as e:
        return {"error": f"Error loading WAV: {str(e)}"}

    # ============================================================
    #   STEP A — TRUE AI ENHANCEMENT (ADOBE-STYLE) USING DEMUCS
    # ============================================================
    try:
        print("Running Adobe-AI voice isolation...")

        model = get_model(name="htdemucs")
        sources = apply_model(model, y[None, ...], sr)

        voice_only = sources[0].squeeze()
    except Exception as e:
        print("AI enhance failed → using original audio:", e)
        voice_only = y

    # ============================================================
    #   STEP B — Trim Silence
    # ============================================================
    try:
        y_trim, _ = librosa.effects.trim(voice_only, top_db=25)
    except:
        y_trim = voice_only

    # ============================================================
    #   STEP C — Noise Reduction
    # ============================================================
    try:
        cleaned = nr.reduce_noise(
            y=y_trim,
            sr=sr,
            prop_decrease=0.65
        )
    except:
        cleaned = y_trim

    # ============================================================
    #   STEP D — Studio FX (Compressor + Highpass + Air Boost)
    # ============================================================
    try:
        board = Pedalboard([
            HighpassFilter(80),
            Compressor(threshold_db=-18, ratio=4, attack_ms=5, release_ms=120),
            HighShelfFilter(gain_db=3.0, cutoff_frequency_hz=10000)
        ])

        processed = board(np.expand_dims(cleaned, 0), sr).squeeze()
    except:
        processed = cleaned

    # ============================================================
    #   STEP E — Loudness Normalization (-16 LUFS)
    # ============================================================
    try:
        meter = pyln.Meter(sr)
        loudness = meter.integrated_loudness(processed)

        normalized = pyln.normalize.loudness(processed, loudness, -16.0)
        normalized = np.clip(normalized, -1.0, 1.0)
    except:
        normalized = processed

    # ============================================================
    #   STEP F — Final Limiter
    # ============================================================
    try:
        limiter = Pedalboard([
            Limiter(threshold_db=-1.0)
        ])
        final_audio = limiter(np.expand_dims(normalized, 0), sr).squeeze()
    except:
        final_audio = normalized

    # ============================================================
    #   SAVE OUTPUT
    # ============================================================
    try:
        sf.write(output_file, final_audio.astype(np.float32), sr)
    except Exception as e:
        return {"error": f"Saving failed: {str(e)}"}

    return FileResponse(output_file, media_type="audio/wav", filename="enhanced_audio.wav")
