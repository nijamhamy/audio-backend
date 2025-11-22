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

# Copy backend code into container
COPY . .

# Railway will NOT use $PORT inside CMD, so we manually expose 8000
EXPOSE 8000

# Start server on fixed port (8000)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
