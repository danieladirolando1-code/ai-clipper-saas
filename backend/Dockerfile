FROM python:3.10-slim

# Install FFmpeg & dependency sistem
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

# Copy requirements dari folder backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh isi folder backend ke container
COPY . .

EXPOSE 8000

# Jalankan Uvicorn dari file main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
