FROM python:3.10-slim

# Install FFmpeg + system libs
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Railway / Render / Fly.io compatible start command
CMD uvicorn backend:app --host 0.0.0.0 --port ${PORT}
