import numpy as np
from PIL import Image

class FastThemeExtractor:
    """
    Lightweight utility to extract aesthetic color palettes from MoviePy clips.
    Uses Pillow's Median Cut quantization instead of heavy Machine Learning.
    """
    
    @staticmethod
    def _get_luminance(rgb: tuple) -> float:
        """Calculates the relative luminance of a color (WCAG 2.0)."""
        a = [v / 255.0 for v in rgb]
        a = [(v / 12.92) if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in a]
        return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722

    @staticmethod
    def _get_contrast_ratio(rgb1: tuple, rgb2: tuple) -> float:
        """Returns the contrast ratio between two RGB colors (1.0 to 21.0)."""
        lum1 = FastThemeExtractor._get_luminance(rgb1)
        lum2 = FastThemeExtractor._get_luminance(rgb2)
        brightest = max(lum1, lum2)
        darkest = min(lum1, lum2)
        return (brightest + 0.05) / (darkest + 0.05)

    @staticmethod
    def _rgb_to_hex(rgb: tuple) -> str:
        return "#{:02x}{:02x}{:02x}".format(*[int(c) for c in rgb])

    @classmethod
    def extract_palette(cls, clip, num_colors: int = 5, samples: int = 3, resize_width: int = 150) -> dict:
        """
        Samples frames and uses Median Cut Quantization to find dominant colors.
        """
        dur = clip.duration or 5.0
        timestamps = np.linspace(dur * 0.1, dur * 0.9, samples)
        
        frames_resized = []
        for t in timestamps:
            frame = clip.get_frame(t)
            img = Image.fromarray(frame)
            
            # Downscale for extreme speed
            aspect_ratio = img.height / img.width
            new_height = int(resize_width * aspect_ratio)
            img = img.resize((resize_width, new_height), Image.Resampling.NEAREST)
            
            frames_resized.append(np.array(img))
            
        # Stack all sampled frames vertically into one tall image
        combined_array = np.vstack(frames_resized)
        combined_img = Image.fromarray(combined_array)

        # Use Pillow's highly optimized Median Cut quantization to find dominant colors
        quantized = combined_img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
        
        # Extract the palette (returns a flat list [R, G, B, R, G, B...])
        raw_palette = quantized.getpalette()[:num_colors * 3]
        
        # Group into tuples [(R,G,B), (R,G,B)...]
        colors = [(raw_palette[i], raw_palette[i+1], raw_palette[i+2]) for i in range(0, len(raw_palette), 3)]
        
        # Sort colors by Luminance (Darkest to Lightest)
        colors = sorted(colors, key=lambda x: cls._get_luminance(x))

        # --- Smart Selection Logic ---
        
        # 1. Background: Pick a rich, dark theme color (usually 2nd darkest avoids pure blacks)
        bg_rgb = colors[1] if len(colors) > 1 else colors[0]
        
        # 2. Text: Find a color with at least 4.5:1 contrast (WCAG AA)
        text_rgb = None
        for potential_text in reversed(colors): # Check from lightest down
            if cls._get_contrast_ratio(bg_rgb, potential_text) >= 4.5:
                text_rgb = potential_text
                break
                
        # 3. Fallback: If video lacks high contrast colors, force readable black/white
        if not text_rgb:
            is_bg_dark = cls._get_luminance(bg_rgb) < 0.5
            text_rgb = (245, 245, 245) if is_bg_dark else (20, 20, 20)

        return {
            "bg_color_rgb": bg_rgb,
            "bg_color_hex": cls._rgb_to_hex(bg_rgb),
            "text_color_rgb": text_rgb,
            "text_color_hex": cls._rgb_to_hex(text_rgb),
            "full_palette_hex": [cls._rgb_to_hex(c) for c in colors]
        }