"""
blur_quotes.py
──────────────
Generates a blurred-background quote video with adaptive, high-contrast
dual-color text (primary English + secondary Urdu).

Color strategy
──────────────
• The text region (bottom half of the video) is sampled across several
  frames so contrast is evaluated against the actual backdrop the text sits on.
• `primary_text`   → highest-contrast palette color (WCAG AA ≥ 4.5 : 1)
  used for the English / main quote.
• `secondary_text` → visually distinct accent, still WCAG AA compliant,
  used for the Urdu / secondary quote & the watermark.
• Both colors are hex strings ready for TextClip.
"""

from moviepy import VideoFileClip, CompositeVideoClip, TextClip
from utils.video_effects import apply_blur, crop_to_aspect_ratio
from utils.pinterest_video import _apply_border_radius, PinterestVideoClip
from utils.theme_extractor import FastThemeExtractor
from utils.custom_halo_moviepy import CustomHaloLogger
import textwrap


# ─────────────────────────────────────────────────────────────────────────────
#  EXAMPLE QUOTE
# ─────────────────────────────────────────────────────────────────────────────
example_quote = {
    "primary":   "When no other options are left, it is only your two hands that can create a miracle for you.",
    "secondary": "جب ممکن کا کوئی بھی چارہ باقی نہیں رہتا تب تمہاری دعائیں ہی تمہارے لئے معجزہ بنتی ہیں",
}


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def create_blur_quote_video(
        video_size=(1080, 1920),
        padding=40,
        subclip=None,
        blur_scale=6.0,
        quote=example_quote,
        watermark_text_string=None,
        video_fps=24,
        render_video=True,
        bg_clip_query="aesthetic clips",
):
    target_width  = video_size[0]
    target_height = video_size[1]
    padding_top   = padding + 260

    # ── 1. Load video ────────────────────────────────────────────────────────
    yield "Loading video..."
    if subclip:
        clip = PinterestVideoClip(bg_clip_query).subclipped(*subclip)
    else:
        clip = PinterestVideoClip(bg_clip_query)

    # ── 2. Foreground clip (cropped + rounded) ────────────────────────────
    yield "Cropping & rounding video..."
    fg_clip = crop_to_aspect_ratio(clip, 6 / 4)
    fg_clip = fg_clip.resized(width=target_width - padding * 2)
    fg_clip = _apply_border_radius(fg_clip, 60)

    # ── 3. Background clip (blurred, full-frame) ──────────────────────────
    yield "Processing background..."
    bg_clip = (
        clip
        .image_transform(apply_blur)
        .resized(blur_scale)
        .cropped(x1=0, y1=0, width=target_width, height=target_height)
    )

    # ── 4. Theme extraction ───────────────────────────────────────────────
    #    Sample the bottom 52 % of the frame (where text lives) across 6
    #    frames so the palette reflects the actual text backdrop.
    yield "Extracting theme..."
    # ← Sample from bg_clip (blurred), NOT the raw clip.
    #   Blurring averages all pixels into a smooth, uniform tone that is
    #   completely different from the raw clip's dark shadows / bright highlights.
    #   Measuring contrast against the wrong source was the root cause of
    #   unreadable text on warm/golden/green backgrounds.
    theme = FastThemeExtractor.extract_palette(
        bg_clip,
        num_colors=10,
        samples=6,
        text_region="bottom",
        text_region_fraction=0.52,
        min_contrast=4.5,
    )

    # Human-readable contrast info for debugging
    yield (
        f"Theme → primary: {theme['primary_text_hex']} "
        f"({theme['primary_contrast']}:1) | "
        f"secondary: {theme['secondary_text_hex']} "
        f"({theme['secondary_contrast']}:1)"
    )

    primary_color   = theme["primary_text_hex"]    # hex str, e.g. "#f2efe8"
    secondary_color = theme["secondary_text_hex"]  # hex str, e.g. "#c4a96b"

    # ── 5. Build text clips ───────────────────────────────────────────────
    yield "Generating text..."

    # ── English (primary quote) ── uses primary color
    eng_text = TextClip(
        text=textwrap.fill(quote["primary"], width=40) + "\n\n",
        font_size=38,
        size=(int(target_width - padding * 9.6), None),
        font="./fonts/Lora-Regular.ttf",
        color=primary_color,       # ← hex, guaranteed high contrast
        method="caption",
        text_align="left",
    )

    # ── Urdu (secondary quote) ── uses secondary accent color
    urdu_text = TextClip(
        text=quote["secondary"] + "\n\n",
        font_size=32,
        font="./fonts/NotoNastaliqUrdu-Regular.ttf",
        size=(target_width - padding * 11, None),
        color=secondary_color,     # ← hex, still WCAG AA, visually distinct
        method="caption",
        text_align="right",
    )

    # ── Watermark ── uses secondary color at reduced opacity
    watermark_clip = None
    if watermark_text_string:
        watermark_clip = TextClip(
            text=watermark_text_string,
            font_size=24,
            font="./fonts/Lora-Regular.ttf",
            color=secondary_color,
        ).with_opacity(0.55)

    # ── 6. Composite ─────────────────────────────────────────────────────
    yield "Compositing..."
    layers = [
        bg_clip,
        fg_clip.with_position((padding, padding_top)),
        eng_text.with_position((padding * 2, target_height * 0.54)),
        urdu_text.with_position((0.34, 0.625), relative=True),
    ]
    if watermark_clip is not None:
        layers.append(watermark_clip.with_position(("center", 0.86), relative=True))

    final_video = CompositeVideoClip(layers, size=(target_width, target_height))
    final_video.duration = clip.duration

    # ── 7. Render ─────────────────────────────────────────────────────────
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