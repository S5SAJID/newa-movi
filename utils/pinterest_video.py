import os
import json
import requests
import subprocess
import numpy as np
from PIL import Image, ImageDraw
from moviepy import VideoFileClip, ColorClip, CompositeVideoClip, ImageClip
from dotenv import load_dotenv

# --- RE-ADDED: Secure API Key loading from .env ---
load_dotenv()
API_KEY = os.getenv("PINTEREST_API_KEY")

class PinterestCacheManager:
    # RE-ADDED: Default api_key=API_KEY fallback
    def __init__(self, api_key=API_KEY, cache_dir=".pinterest_cache"):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.json_cache_path = os.path.join(cache_dir, "query_cache.json")
        self.video_dir = os.path.join(cache_dir, "videos")
        
        os.makedirs(self.video_dir, exist_ok=True)
        
        if os.path.exists(self.json_cache_path):
            with open(self.json_cache_path, "r") as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

    def _save_cache(self):
        with open(self.json_cache_path, "w") as f:
            json.dump(self.cache, f, indent=4)

    def fetch_api_data(self, query, num="20"):
        url = "https://unofficial-pinterest-api.p.rapidapi.com/pinterest/videos/relevance"
        querystring = {"keyword": query, "num": num}
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "unofficial-pinterest-api.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
        print(f"Fetching from Pinterest API for query: '{query}'...")
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        
        data = response.json().get("data", [])
        valid_videos = []
        for pin in data:
            try:
                video_list = pin.get("videos", {}).get("video_list", {})
                hls_url = video_list.get("V_HLSV4", {}).get("url") or video_list.get("V_HLSV3_MOBILE", {}).get("url")
                video_id = pin.get("id")
                
                if hls_url and video_id:
                    valid_videos.append({
                        "id": video_id,
                        "url": hls_url,
                        "title": pin.get("title", "Untitled")
                    })
            except Exception:
                continue
                
        return valid_videos

    def get_next_video(self, query):
        query_lower = query.lower()
        if query_lower not in self.cache or self.cache[query_lower]["current_index"] >= len(self.cache[query_lower]["videos"]):
            videos = self.fetch_api_data(query)
            if not videos:
                raise ValueError(f"No videos found for query: '{query}'")
                
            self.cache[query_lower] = {
                "current_index": 0,
                "videos": videos
            }
            self._save_cache()

        current_data = self.cache[query_lower]
        video_data = current_data["videos"][current_data["current_index"]]
        
        current_data["current_index"] += 1
        self._save_cache()
        
        return self._download_and_convert(video_data["id"], video_data["url"])

    def _download_and_convert(self, video_id, m3u8_url):
        output_file = os.path.join(self.video_dir, f"{video_id}.mp4")
        if os.path.exists(output_file):
            # RE-ADDED: Local cache log
            print(f"Loaded video {video_id} from local cache.")
            return output_file
            
        # RE-ADDED: Download start log
        print(f"Downloading and converting HLS stream for video {video_id}...")
        command = [
            "ffmpeg", "-y", "-i", m3u8_url, "-c", "copy", 
            "-bsf:a", "aac_adtstoasc", output_file
        ]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # RE-ADDED: Safety check to ensure FFmpeg didn't fail
        if not os.path.exists(output_file):
            raise Exception("Failed to download video stream via FFmpeg.")
            
        return output_file

# ---------------------------------------------------------
# Formatting Utilities
# ---------------------------------------------------------

def _apply_border_radius(clip, radius):
    """Generates a rounded mask and applies it to the clip."""
    if radius <= 0:
        return clip
        
    # Create an image mask matching the clip's size
    mask_img = Image.new('L', (clip.w, clip.h), 0)
    draw = ImageDraw.Draw(mask_img)
    # Draw a solid white rounded rectangle
    draw.rounded_rectangle((0, 0, clip.w, clip.h), radius=radius, fill=255)
    
    # Convert mask to numpy array (normalized 0.0 to 1.0)
    mask_np = np.array(mask_img) / 255.0
    
    # In MoviePy v2.0+, use 'with_mask' or assignment to .mask
    # ImageClip no longer takes 'ismask'
    mask_clip = ImageClip(mask_np)
    
    # Return the clip with the mask applied
    return clip.with_mask(mask_clip)


# ---------------------------------------------------------
# The Main MoviePy Function
# ---------------------------------------------------------

# RE-ADDED: Default api_key=API_KEY fallback
def PinterestVideoClip(query, api_key=API_KEY, mute=False, volume=1.0, 
                       target_size=None, padding=(0,0), border_radius=0, 
                       bg_color=(0, 0, 0), **kwargs):
    """
    Args:
        query (str): The search term.
        api_key (str): Your RapidAPI Key.
        mute (bool): Mutes the video if True.
        volume (float): Adjusts audio volume.
        target_size (tuple): Output video dimensions (width, height) e.g., (1080, 1920).
        padding (int): Pixels of space to leave on the sides.
        border_radius (int): Corner roundness of the inner video clip.
        bg_color (tuple): Background color RGB e.g., (0,0,0) for black.
    """
    
    # 1. Fetch the video
    cache_manager = PinterestCacheManager(api_key=api_key)
    local_mp4_path = cache_manager.get_next_video(query)
    
    clip = VideoFileClip(local_mp4_path, **kwargs)
    
    # 2. Audio adjustments
    if mute:
        clip = clip.without_audio()
    elif volume != 1.0 and clip.audio is not None:
        clip = clip.volumex(volume)
        
    # 3. Formatting (Target size, Padding, Border Radius)
    if target_size is not None:
        # Calculate the maximum size the video can be while respecting padding
        max_w = target_size[0] - (2 * padding[0])
        max_h = target_size[1] - (2 * padding[1])
        
        # Maintain aspect ratio while fitting it into the allowed space
        clip_ratio = clip.w / clip.h
        target_ratio = max_w / max_h
        
        if clip_ratio > target_ratio:
            # Video is wider than the target box
            clip = clip.resized(width=max_w)
        else:
            # Video is taller than the target box
            clip = clip.resized(height=max_h)
            
        # Apply the rounded corners to the resized video
        clip = _apply_border_radius(clip, border_radius)
        
        # Create a solid color background of the exact target_size
        background = ColorClip(size=target_size, color=bg_color, duration=clip.duration)
        
        # Paste the rounded video perfectly in the center of the background
        clip = CompositeVideoClip([background, clip.with_position("center")])

    return clip