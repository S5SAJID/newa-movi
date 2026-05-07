from PIL import Image, ImageFilter
import numpy as np

def apply_blur(image):
    # Convert numpy array to PIL Image
    pil_img = Image.fromarray(image)
    # Apply Gaussian blur (radius = intensity)
    blurred_pil = pil_img.filter(ImageFilter.GaussianBlur(radius=30))
    # Convert back to numpy array for MoviePy
    return np.array(blurred_pil)

from moviepy import VideoFileClip

def crop_to_aspect_ratio(clip, aspect_ratio=6/4):
    # Current dimensions
    w, h = clip.w, clip.h
    
    # Calculate potential width and height
    # Formula: Aspect Ratio = Width / Height
    target_w = h * aspect_ratio
    target_h = w / aspect_ratio

    if target_w <= w:
        # Video is wider than target (e.g., 16:9 -> 4:3)
        # Use full height, crop the width
        final_w, final_h = target_w, h
    else:
        # Video is narrower than target (e.g., 9:16 -> 4:3)
        # Use full width, crop the height
        final_w, final_h = w, target_h

    # Use MoviePy 2.0's .cropped() method
    return clip.cropped(
        x_center=w / 2,
        y_center=h / 2,
        width=final_w,
        height=final_h
    )