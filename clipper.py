import os
import subprocess
import json
import re
import requests
import openai

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_video_id(url):
    """Mengambil Video ID 11 karakter dari URL YouTube"""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if match:
        return match.group(1)
    return url


def download_audio_via_cobalt(youtube_url, output_path="outputs/temp_audio.mp3"):
    """
    Mengunduh audio dari YouTube.
    Coba lewat Cobalt API dulu (kalau tersedia), kalau gagal apapun sebabnya
    (domain mati, timeout, IP diblokir, dll) langsung fallback ke yt-dlp
    dengan player_client=android supaya lebih tahan terhadap blokir IP cloud.
    """
    os.makedirs("outputs", exist_ok=True)
    clean_url = f"https://www.youtube.com/watch?v={extract_video_id(youtube_url)}"

    try:
        api_url = "https://co.wuk.sh/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "url": clean_url,
            "isAudioOnly": True,
            "aFormat": "mp3",
        }

        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "url" in data:
            audio_stream_url = data["url"]
            audio_data = requests.get(audio_stream_url, timeout=30).content
            with open(output_path, "wb") as f:
                f.write(audio_data)
            return output_path

        # Response berhasil tapi tidak ada URL audio -> anggap gagal, lanjut fallback
        print("Cobalt merespons tanpa URL audio, fallback ke yt-dlp...")

    except Exception as e:
        # Menangkap SEMUA jenis kegagalan Cobalt: DNS mati, timeout,
        # koneksi ditolak, response bukan JSON, dsb.
        print(f"Cobalt gagal ({e}), fallback ke yt-dlp...")

    # --- Fallback: yt-dlp dengan android player client ---
    cmd = [
        "yt-dlp", "-f", "ba/b", "-x", "--audio-format", "mp3",
        "--extractor-args", "youtube:player_client=android",
        "-o", output_path, "--force-overwrites", clean_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Lempar error yang isinya pesan asli dari yt-dlp, bukan cuma exit status
        raise RuntimeError(f"yt-dlp gagal: {result.stderr.strip()}")
    return output_path


def transcribe_audio_whisper_api(audio_path):
    """Transkripsi audio dengan OpenAI Whisper API"""
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    return transcript.segments


def get_viral_timestamps(transcript_text):
    prompt = f"""
Berikut adalah transkrip video beserta timestamp:
{transcript_text}

Pilih 2-3 bagian terbaik berdurasi 30-60 detik yang memiliki Hook menarik untuk media sosial.
Kembalikan respon HANYA berupa JSON valid dengan format:
[
    {{"title": "Judul Klip 1", "start": 10.5, "end": 45.0, "reason": "Alasan viral"}}
]
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def crop_video_to_vertical(youtube_url, start_time, duration, output_filename):
    clean_url = f"https://www.youtube.com/watch?v={extract_video_id(youtube_url)}"

    cmd_url = [
        "yt-dlp",
        "-g",
        "-f", "b/bestvideo+bestaudio",
        "--extractor-args", "youtube:player_client=ios",
        clean_url,
    ]
    video_stream_url = subprocess.check_output(cmd_url).decode("utf-8").strip().split("\n")[0]

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-ss", str(start_time),
        "-i", video_stream_url, "-t", str(duration),
        "-vf", "crop=ih*(9/16):ih",
        "-c:v", "libx264", "-c:a", "aac", output_filename,
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    return output_filename


def process_video_pipeline(youtube_url):
    os.makedirs("outputs", exist_ok=True)

    # 1. Download audio (Cobalt -> fallback yt-dlp otomatis)
    audio_file = download_audio_via_cobalt(youtube_url)

    # 2. Transkripsi audio via OpenAI Whisper
    segments = transcribe_audio_whisper_api(audio_file)
    transcript_text = "".join(
        [f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}\n" for seg in segments]
    )

    # 3. AI memilih timestamp viral
    clips_data = get_viral_timestamps(transcript_text)
    if isinstance(clips_data, dict) and "clips" in clips_data:
        clips_data = clips_data["clips"]
    elif isinstance(clips_data, dict):
        clips_data = list(clips_data.values())[0]

    # 4. Potong klip vertikal
    processed_clips = []
    for idx, clip in enumerate(clips_data):
        start, end = clip["start"], clip["end"]
        out_name = f"outputs/clip_{idx+1}.mp4"
        crop_video_to_vertical(youtube_url, start, end - start, out_name)
        processed_clips.append({
            "title": clip.get("title", f"Klip {idx+1}"),
            "reason": clip.get("reason", ""),
            "download_url": f"/download/clip_{idx+1}.mp4",
        })

    return processed_clips
