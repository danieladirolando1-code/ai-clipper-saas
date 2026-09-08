import os
import subprocess
import json
import whisper
import openai

# Konfigurasi OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY", "SK-YOUR-OPENAI-KEY-HERE")

# Load model whisper (Gunakan 'base' atau 'small' untuk lokal, 'large' jika server kuat)
whisper_model = whisper.load_model("base")

def download_youtube_audio(youtube_url, output_path="audio.mp3"):
    """Mengunduh audio dari link YouTube"""
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "-o", output_path,
        youtube_url,
        "--force-overwrites"
    ]
    subprocess.run(cmd, check=True)
    return output_path

def get_viral_timestamps(transcript_text):
    """Menganalisis transkrip dan mencari momen viral menggunakan AI"""
    prompt = f"""
    Berikut adalah transkrip video beserta timestamp:
    {transcript_text}

    Analisis transkrip di atas dan pilih 2-3 bagian terbaik berdurasi 30-60 detik yang memiliki Hook menarik, konflik, atau jawaban berharga untuk media sosial (TikTok/Shorts).
    
    Kembalikan respon HANYA berupa JSON valid dengan format seperti ini:
    [
        {{
            "title": "Judul Klip 1",
            "start": 10.5,
            "end": 45.0,
            "reason": "Alasan klip ini berpotensi viral"
        }}
    ]
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def crop_video_to_vertical(youtube_url, start_time, duration, output_filename):
    """Memotong video langsung dari YouTube dan mengubah rasio ke 9:16 (Vertikal)"""
    # Mengambil direct stream URL dari YouTube
    cmd_url = f"yt-dlp -g -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]' {youtube_url}"
    video_stream_url = subprocess.check_output(cmd_url, shell=True).decode('utf-8').strip().split('\n')[0]

    # Crop 16:9 menjadi 9:16 di tengah frame menggunakan FFmpeg
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", video_stream_url,
        "-t", str(duration),
        "-vf", "crop=ih*(9/16):ih", # Crop center to 9:16 ratio
        "-c:v", "libx264",
        "-c:a", "aac",
        output_filename
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    return output_filename

def process_video_pipeline(youtube_url):
    """Pipeline Utama"""
    os.makedirs("outputs", exist_ok=True)
    
    # 1. Download Audio
    audio_file = download_youtube_audio(youtube_url, "outputs/temp_audio.mp3")
    
    # 2. Transkripsi dengan Timestamp
    result = whisper_model.transcribe(audio_file)
    segments = result.get("segments", [])
    
    transcript_text = ""
    for seg in segments:
        transcript_text += f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}\n"
    
    # 3. Minta AI Cari Timestamp Terbaik
    clips_data = get_viral_timestamps(transcript_text)
    
    # Handling jika AI mengembalikan object bertingkat
    if isinstance(clips_data, dict) and "clips" in clips_data:
        clips_data = clips_data["clips"]
    elif isinstance(clips_data, dict):
        clips_data = list(clips_data.values())[0]

    processed_clips = []
    
    # 4. Potong Video Berdasarkan Rekomendasi AI
    for idx, clip in enumerate(clips_data):
        start = clip["start"]
        end = clip["end"]
        duration = end - start
        out_name = f"outputs/clip_{idx+1}.mp4"
        
        crop_video_to_vertical(youtube_url, start, duration, out_name)
        
        processed_clips.append({
            "title": clip.get("title", f"Klip {idx+1}"),
            "reason": clip.get("reason", ""),
            "download_url": f"/download/clip_{idx+1}.mp4"
        })
        
    return processed_clips
