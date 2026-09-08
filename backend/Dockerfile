FROM python:3.10-slim

# Install FFmpeg & git
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt-get/lists/*

# Set folder kerja ke /app/backend
WORKDIR /app/backend

# Copy seluruh file dari folder backend di GitHub ke folder kerja Docker
COPY . .

# Install dependency Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

# Jalankan uvicorn dari folder backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
