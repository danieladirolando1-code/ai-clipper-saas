import os
import subprocess
import json
import re
import openai
from youtube_transcript_api import YouTubeTranscriptApi

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if match:
        return match.group(1)
    return url

def get_transcript_via_api(video_id):
    try:
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_id, languages=['id', 'en'])
        formatted_transcript = ""
        for item in fetched_transcript.snippet:
            start = item['start']
            duration = item['duration']
            text = item['text']
            formatted_transcript += f"[{start:.1f}s - {start + duration:.1f}s] {text}\n"
        return formatted_transcript
    except Exception:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(['id', 'en'])
            data = transcript.fetch()
            return "".join([f"[{item['start']:.1f}s] {item['text']}\n" for item in data])
        except Exception as e:
            raise Exception(f"Gagal mengambil transkrip YouTube: {str(e)}")

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
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def crop_video_to_vertical(youtube_url, start_time, duration, output_filename):
    cmd_url = [
        "yt-dlp",
        "-g",
        "-f", "b/bestvideo+bestaudio",
        "--extractor-args", "youtube:player_client=ios",
        youtube_url
    ]
    video_stream_url = subprocess.check_output(cmd_url).decode('utf-8').strip().split('\n')[0]

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
    video_id = extract_video_id(youtube_url)
    clean_url = f"https://www.youtube.com/watch?v={video_id}"
    
    transcript_text = get_transcript_via_api(video_id)
    clips_data = get_viral_timestamps(transcript_text)
    
    if isinstance(clips_data, dict) and "clips" in clips_data:
        clips_data = clips_data["clips"]
    elif isinstance(clips_data, dict):
        clips_data = list(clips_data.values())[0]

    processed_clips = []
    for idx, clip in enumerate(clips_data):
        start, end = clip["start"], clip["end"]
        out_name = f"outputs/clip_{idx+1}.mp4"
        crop_video_to_vertical(clean_url, start, end - start, out_name)
        
        processed_clips.append({
            "title": clip.get("title", f"Klip {idx+1}"),
            "reason": clip.get("reason", ""),
            "download_url": f"/download/clip_{idx+1}.mp4"
        })
    return processed_clips
