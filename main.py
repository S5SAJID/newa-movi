from moviepy import VideoFileClip, CompositeVideoClip, TextClip
from utils.video_effects import apply_blur, crop_to_aspect_ratio
from utils.pinterest_video import _apply_border_radius
from utils.theme_extractor import FastThemeExtractor
from utils.pinterest_video import PinterestVideoClip
from utils.custom_halo_moviepy import CustomHaloLogger
import textwrap
from halo import Halo

video_size = (1080, 1920)
target_width = video_size[0]
target_height = video_size[1]

padding = 40
padding_top = padding + 260

spinner = Halo(text="Loading video...", spinner="dots", color="cyan")
spinner.start()

clip = PinterestVideoClip("lofi aesthetic clips").subclipped(0,2)

spinner.text = "Croping & Rounding video..."
fg_clip = crop_to_aspect_ratio(clip, 6/4)
fg_clip = fg_clip.resized(width=target_width - padding * 2)
fg_clip = _apply_border_radius(fg_clip, 60)

spinner.text = "Processing bg..."
bg_clip = clip.image_transform(apply_blur).resized(6.0).cropped(x1=0, y1=0, width=target_width, height=target_height)

spinner.text = "Extracting theme..."
theme = FastThemeExtractor.extract_palette(clip.resized(6.0).cropped(x1=0, y1=0, width=target_width, height=target_height))

spinner.text = "Generating text..."
text = TextClip(
    text="""جب ممکن کا کوئی بھی چارہ باقی نہیں رہتا تب تمہاری دعائیں ہی تمہارے لئے معجزہ بنتی ہیں"""+ "\n\n",
    font_size=32, 
    font="NotoNastaliqUrdu-Regular.ttf", 
    size=(target_width - (padding * 11), None), 
    color=theme['full_palette_hex'][3],
    method="caption",
    text_align="right",
)

eng_text = TextClip(
    text=textwrap.fill("When no other options are left, it is only your two hands that can create a miracle for you.", width=40) + "\n\n", 
    font_size=38,  
    size=(int(target_width - (padding * 9.6)), None), 
    font="fonts/Lora-Regular.ttf", 
    color=theme['text_color_rgb'], 
    method="caption",
    text_align="left",
)
watermark_text = TextClip(
    text="@s5poetry",
    font_size=24,  
    font="fonts/Lora-Regular.ttf", 
    color=theme['full_palette_hex'][0], 
).with_opacity(0.5)

spinner.text = "Compositing..."
# 4. Composite
# Position at (10, 10) to create the uniform 10px padding
final_video = CompositeVideoClip(
    [
        bg_clip, 
        fg_clip.with_position((padding, padding_top)),
        eng_text.with_position((padding * 2, target_height * 0.54)),
        text.with_position((0.34, 0.625), relative=True),
        watermark_text.with_position(("center", 0.86), relative=True)
    ],
    size=(target_width, target_height)
)

final_video.duration = clip.duration
spinner.text = "Rendering..."

# custom_logger = CustomHaloLogger(spinner)

# # final_video.write_videofile("output_composite.mp4", fps=10) #clip.fps
# final_video.write_videofile(
#     "output_composite.mp4", 
#     fps=10, 
#     threads=4,      
#     preset="ultrafast",       
#     logger=custom_logger                 
# )

spinner.text = "Cleaning up temporary files..."
final_video.save_frame("preview.png", t=1)
spinner.succeed("All done!")