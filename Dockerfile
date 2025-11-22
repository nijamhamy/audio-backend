FROM python:3.10-slim

# Install FFmpeg + dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Start uvicorn on fixed port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
