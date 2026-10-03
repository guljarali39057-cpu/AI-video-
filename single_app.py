import os
import time
import random
import glob
import subprocess
import asyncio
import logging

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

import google.auth.transport.requests
import google.oauth2.credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Logging setup
logging.basicConfig(
    filename='snake_channel_daemon.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def generate_cute_voice(text, output_audio="voiceover.mp3"):
    import edge_tts
    voice = "en-US-AnaNeural" 
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_audio)

def get_authenticated_service():
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"Error loading existing token: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(google.auth.transport.requests.Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists('client_secret.json'):
                print("Error: client_secret.json file is missing!")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', 
                SCOPES, 
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print("\n==========================================")
            print("GOOGLE ACCOUNT AUTHORIZATION REQUIRED:")
            print("1. Copy this link and open it in your phone browser:")
            print(auth_url)
            print("2. Allow permission and copy the authorization code.")
            print("==========================================")
            
            code = input("Paste the authorization code here: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def generate_and_upload_short():
    print("\n==========================================")
    print("Starting Automated Generation & Upload Cycle...")
    print("==========================================")
    
    animal_topics = [
        {"query": "amazing lion facts short", "name": "Lion", "fact": "Did you know a lion's roar can be heard from up to 5 miles away? Absolute king of the jungle!"},
        {"query": "great white shark facts short", "name": "Shark", "fact": "Sharks have been around on Earth even before trees and dinosaurs! Truly ancient hunters."},
        {"query": "dangerous cobra snake facts short", "name": "Cobra", "fact": "Cobras can raise up to one third of their body straight up and look you right in the eye!"},
        {"query": "golden eagle hunting facts short", "name": "Eagle", "fact": "Golden eagles can dive at speeds of over 150 miles per hour when catching their prey!"},
        {"query": "tiger wildlife facts short", "name": "Tiger", "fact": "Every tiger has a completely unique pattern of stripes, just like human fingerprints!"}
    ]
    
    selected_topic = random.choice(animal_topics)
    query = selected_topic["query"]
    animal_name = selected_topic["name"]
    selected_fact = selected_topic["fact"]
    
    print(f"Selected Animal: {animal_name} | Query: {query}")
    
    output_filename = "gta6_clip.mp4"
    history_file = "downloaded_ids.txt"
    voice_audio = "voiceover.mp3"
    
    downloaded_ids = set()
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            downloaded_ids = set(line.strip() for line in f if line.strip())
            
    try:
        for f in glob.glob("downloaded_temp.*"):
            os.remove(f)
        if os.path.exists(output_filename):
            os.remove(output_filename)
        if os.path.exists(voice_audio):
            os.remove(voice_audio)
            
        print("Generating cute voiceover...")
        asyncio.run(generate_cute_voice(selected_fact, voice_audio))
        
        cmd_json = [
            "yt-dlp",
            f"ytsearch15:{query}",
            "--print", "%(id)s",
            "--flat-playlist"
        ]
        
        result = subprocess.run(cmd_json, capture_output=True, text=True, check=True)
        video_ids = [vid.strip() for vid in result.stdout.strip().split("\n") if vid.strip()]
        
        available_entries = [vid for vid in video_ids if vid not in downloaded_ids]
        if not available_entries:
            downloaded_ids.clear()
            if os.path.exists(history_file):
                os.remove(history_file)
            available_entries = video_ids
            
        if not available_entries:
            print("Error: Koi nayi video nahi mili!")
            return False
            
        selected_id = random.choice(available_entries)
        print(f"Selected unique Video ID: {selected_id}")
        
        video_url = f"https://www.youtube.com/watch?v={selected_id}"
        cmd_download = [
            "yt-dlp",
            video_url,
            "--output", "downloaded_temp.%(ext)s"
        ]
        
        print("Downloading selected unique video...")
        subprocess.run(cmd_download, check=True)
        
        with open(history_file, "a") as f:
            f.write(selected_id + "\n")
            
        downloaded_files = glob.glob("downloaded_temp.*")
        if not downloaded_files:
            print("Error: Video download nahi ho payi!")
            return False
            
        temp_download = downloaded_files[0]
        
        print("Processing video and mixing cute voiceover...")
        clip = VideoFileClip(temp_download)
        
        if clip.duration > 30:
            max_start = int(clip.duration - 30)
            start_time = random.randint(0, max_start)
            end_time = start_time + 30
            try:
                clip = clip.subclip(start_time, end_time)
            except AttributeError:
                try:
                    clip = clip.subclipped(start_time, end_time)
                except AttributeError:
                    clip = clip.with_start(start_time).with_end(end_time)
                    
        voice_clip = AudioFileClip(voice_audio)
        
        try:
            voice_clip = voice_clip.volumetrics(1.0)
        except AttributeError:
            try:
                voice_clip = voice_clip.multiply_volume(1.0)
            except AttributeError:
                pass
                
        if clip.audio is not None:
            try:
                original_audio = clip.audio.volumetrics(0.2)
            except AttributeError:
                try:
                    original_audio = clip.audio.multiply_volume(0.2)
                except AttributeError:
                    original_audio = clip.audio
            final_audio = CompositeAudioClip([original_audio, voice_clip])
        else:
            final_audio = voice_clip
            
        clip = clip.set_audio(final_audio) if hasattr(clip, 'set_audio') else clip.with_audio(final_audio)
            
        clip.write_videofile(
            output_filename,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4
        )
        
        if os.path.exists(temp_download):
            os.remove(temp_download)
        if os.path.exists(voice_audio):
            os.remove(voice_audio)
            
        title = f"Unbelievable {animal_name} Facts! #shorts"
        description = f"{selected_fact} Subscribe for more amazing wildlife facts! #shorts #{animal_name.lower()}"
        
        print("Initializing YouTube upload service...")
        youtube = get_authenticated_service()
        if not youtube:
            print("Failed to authenticate with YouTube.")
            return False

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['animals', animal_name.lower(), 'facts', 'shorts', 'wildlife'],
                'categoryId': '15'
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(output_filename, chunksize=-1, resumable=True)
        print(f"Uploading {output_filename} to YouTube...")
        
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Upload progress: {int(status.progress() * 100)}%")

        print(f"Video uploaded successfully! Video ID: {response.get('id')}")
        logging.info(f"Successfully uploaded short: {title} (ID: {response.get('id')})")
        return True

    except Exception as e:
        print(f"Error in pipeline cycle: {e}")
        logging.error(f"Error in pipeline cycle: {e}")
        return False

if __name__ == "__main__":
    print("Single-File 24/7 Animal Automation Daemon Started!")
    logging.info("Single-file daemon started.")
    
    UPLOAD_INTERVAL_SECONDS = 144 * 60  # Har 144 minute (2.4 ghante) mein ek video
    
    while True:
        success = generate_and_upload_short()
        if success:
            print("Agla upload 144 minute baad hoga...")
        else:
            print("Kuch error aaya, thodi der baad retry karenge...")
        time.sleep(UPLOAD_INTERVAL_SECONDS)
