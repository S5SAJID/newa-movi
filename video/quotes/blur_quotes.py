from moviepy import VideoFileClip, CompositeVideoClip, TextClip
from utils.video_effects import apply_blur, crop_to_aspect_ratio
from utils.pinterest_video import _apply_border_radius
from utils.theme_extractor import FastThemeExtractor
from utils.pinterest_video import PinterestVideoClip
from utils.custom_halo_moviepy import CustomHaloLogger
import textwrap
from halo import Halo

example_quote = {
    "primary": "When no other options are left, it is only your two hands that can create a miracle for you.",
    "secondary": "جب ممکن کا کوئی بھی چارہ باقی نہیں رہتا تب تمہاری دعائیں ہی تمہارے لئے معجزہ بنتی ہیں",
}

def create_blur_quote_video(
        video_size=(1080, 1920), 
        padding=40,
        subclip=None,
        blur_scale=6.0,
        quote=example_quote,
        watermark_text_string=None,
        video_fps = 24,
        render_video = True,
        bg_clip_query="aesthetic clips"
    ):
    target_width = video_size[0]
    target_height = video_size[1]

    padding_top = padding + 260

    yield "Loading video..."
    if subclip:
        clip = PinterestVideoClip(bg_clip_query)
    else:
        clip = PinterestVideoClip(bg_clip_query).subclipped(subclip)
    
    yield "Croping & Rounding video..."
    fg_clip = crop_to_aspect_ratio(clip, 6/4)
    fg_clip = fg_clip.resized(width=target_width - padding * 2)
    fg_clip = _apply_border_radius(fg_clip, 60)

    yield"Processing bg..."
    bg_clip = clip.image_transform(apply_blur).resized(blur_scale).cropped(x1=0, y1=0, width=target_width, height=target_height)

    yield "Extracting theme..."
    theme = FastThemeExtractor.extract_palette(clip)

    yield "Generating text..."
    text = TextClip(
        text=quote["secondary"] + "\n\n",
        font_size=32, 
        font="./fonts/NotoNastaliqUrdu-Regular.ttf", 
        size=(target_width - (padding * 11), None), 
        color=theme['full_palette_hex'][0],
        method="caption",
        text_align="right",
    )

    eng_text = TextClip(
        text=textwrap.fill(quote["primary"], width=40) + "\n\n", 
        font_size=38,  
        size=(int(target_width - (padding * 9.6)), None), 
        font="./fonts/Lora-Regular.ttf", 
        color=theme['text_color_rgb'], 
        method="caption",
        text_align="left",
    )

    if watermark_text_string:
        watermark_text = TextClip(
            text=watermark_text_string,
            font_size=24,  
            font="fonts/Lora-Regular.ttf", 
            color=theme['full_palette_hex'][0], 
        ).with_opacity(0.5)

    yield "Compositing..."
    final_video = CompositeVideoClip(
        [
            bg_clip, 
            fg_clip.with_position((padding, padding_top)),
            eng_text.with_position((padding * 2, target_height * 0.54)),
            text.with_position((0.34, 0.625), relative=True),
            watermark_text.with_position(("center", 0.86), relative=True) if watermark_text_string else None
        ],
        size=(target_width, target_height)
    )

    final_video.duration = clip.duration
    yield "Rendering..."
    if render_video:
        final_video.write_videofile(
            "output_composite.mp4", 
            fps=video_fps, 
            threads=4,      
            preset="ultrafast",       
        )

    final_video.save_frame("preview.png", t=1)
    yield "All done!"