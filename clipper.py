import os
import subprocess
import json
import whisper
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")
whisper_model = whisper.load_model("base")

def download_youtube_audio(youtube_url, output_path="audio.mp3"):
    cmd = [
        "yt-dlp", "-x", "--audio-format", "mp3",
        "-o", output_path, youtube_url, "--force-overwrites"
    ]
    subprocess.run(cmd, check=True)
    return output_path

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
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def crop_video_to_vertical(youtube_url, start_time, duration, output_filename):
    cmd_url = f"yt-dlp -g -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]' {youtube_url}"
    video_stream_url = subprocess.check_output(cmd_url, shell=True).decode('utf-8').strip().split('\n')[0]

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-ss", str(start_time),
        "-i", video_stream_url, "-t", str(duration),
        "-vf", "crop=ih*(9/16):ih",
        "-c:v", "libx264", "-c:a", "aac", output_filename
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    return output_filename

def process_video_pipeline(youtube_url):
    os.makedirs("outputs", exist_ok=True)
    audio_file = download_youtube_audio(youtube_url, "outputs/temp_audio.mp3")
    
    result = whisper_model.transcribe(audio_file)
    segments = result.get("segments", [])
    
    transcript_text = "".join([f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}\n" for seg in segments])
    clips_data = get_viral_timestamps(transcript_text)
    
    if isinstance(clips_data, dict) and "clips" in clips_data:
        clips_data = clips_data["clips"]
    elif isinstance(clips_data, dict):
        clips_data = list(clips_data.values())[0]

    processed_clips = []
    for idx, clip in enumerate(clips_data):
        start, end = clip["start"], clip["end"]
        out_name = f"outputs/clip_{idx+1}.mp4"
        crop_video_to_vertical(youtube_url, start, end - start, out_name)
        
        processed_clips.append({
            "title": clip.get("title", f"Klip {idx+1}"),
            "reason": clip.get("reason", ""),
            "download_url": f"/download/clip_{idx+1}.mp4"
        })
    return processed_clips
