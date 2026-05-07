import json
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import VideoClip, CompositeVideoClip, ColorClip
from typing import Union, List, Dict, Optional, Tuple, Callable
import os
import math

# ─────────────────────────────────────────────────────────────────────────────
#  AESTHETIC PRESETS
# ─────────────────────────────────────────────────────────────────────────────
PRESETS = {
    "minimal_white": dict(
        bg_color               = (0, 0, 0, 0),
        normal_text_color      = (255, 255, 255),
        highlight_text_color   = (255, 255, 255),
        normal_box_color       = (0, 0, 0, 0),        # no box
        highlight_box_color    = (0, 0, 0, 0),
        normal_border_color    = (0, 0, 0, 0),
        highlight_border_color = (0, 0, 0, 0),
        border_radius          = 0,
        border_width           = 0,
        use_underline          = True,
        underline_color        = (255, 255, 255),
        underline_thickness    = 2,
        text_shadow            = False,
    ),
    "elegant_dark": dict(
        bg_color               = (0, 0, 0, 0),
        normal_text_color      = (200, 200, 200),
        highlight_text_color   = (255, 255, 255),
        normal_box_color       = (0, 0, 0, 0),
        highlight_box_color    = (0, 0, 0, 0),
        normal_border_color    = (0, 0, 0, 0),
        highlight_border_color = (0, 0, 0, 0),
        border_radius          = 0,
        border_width           = 0,
        use_underline          = False,
        underline_color        = (255, 255, 255),
        underline_thickness    = 2,
        text_shadow            = True,
        shadow_color           = (0, 0, 0),
        shadow_blur            = 8,
        shadow_offset          = (2, 3),
    ),
    "glass": dict(
        bg_color               = (0, 0, 0, 0),
        normal_text_color      = (255, 255, 255),
        highlight_text_color   = (255, 255, 255),
        normal_box_color       = (255, 255, 255, 18),
        highlight_box_color    = (255, 255, 255, 35),
        normal_border_color    = (255, 255, 255, 60),
        highlight_border_color = (255, 255, 255, 120),
        border_radius          = 12,
        border_width           = 1,
        use_underline          = False,
        underline_color        = (255, 255, 255),
        underline_thickness    = 1,
        text_shadow            = True,
        shadow_color           = (0, 0, 0),
        shadow_blur            = 6,
        shadow_offset          = (1, 2),
    ),
    "neon": dict(
        bg_color               = (0, 0, 0, 0),
        normal_text_color      = (180, 180, 180),
        highlight_text_color   = (0, 255, 180),
        normal_box_color       = (0, 0, 0, 0),
        highlight_box_color    = (0, 0, 0, 0),
        normal_border_color    = (0, 0, 0, 0),
        highlight_border_color = (0, 0, 0, 0),
        border_radius          = 0,
        border_width           = 0,
        use_underline          = True,
        underline_color        = (0, 255, 180),
        underline_thickness    = 2,
        text_shadow            = True,
        shadow_color           = (0, 255, 180),
        shadow_blur            = 14,
        shadow_offset          = (0, 0),
    ),
    "bold_cards": dict(
        bg_color               = (0, 0, 0, 0),
        normal_text_color      = (15, 15, 15),
        highlight_text_color   = (255, 255, 255),
        normal_box_color       = (240, 240, 240, 255),
        highlight_box_color    = (15, 15, 15, 255),
        normal_border_color    = (200, 200, 200),
        highlight_border_color = (15, 15, 15),
        border_radius          = 8,
        border_width           = 0,
        use_underline          = False,
        underline_color        = (0, 0, 0),
        underline_thickness    = 2,
        text_shadow            = False,
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
#  FONT SIZE RHYTHM PATTERNS
#  Each pattern defines relative scale per word-position in a window
#  e.g. "wave" → center word is biggest
# ─────────────────────────────────────────────────────────────────────────────
def _rhythm_flat(i: int, n: int) -> float:
    return 1.0


def _rhythm_wave(i: int, n: int) -> float:
    """Center word biggest, shoulders smaller."""
    center = (n - 1) / 2
    dist   = abs(i - center) / max(center, 1)
    return 1.0 - 0.28 * dist


def _rhythm_crescendo(i: int, n: int) -> float:
    """Words grow larger as they appear."""
    return 0.72 + 0.28 * (i / max(n - 1, 1))


def _rhythm_highlight_focus(i: int, n: int) -> float:
    """Slight variation — keeps things readable but alive."""
    pattern = [0.82, 0.88, 1.0, 0.88, 0.82]
    return pattern[i % len(pattern)]


RHYTHM_PATTERNS = {
    "flat":             _rhythm_flat,
    "wave":             _rhythm_wave,
    "crescendo":        _rhythm_crescendo,
    "highlight_focus":  _rhythm_highlight_focus,
}

# ─────────────────────────────────────────────────────────────────────────────
#  FONT LOADER
# ─────────────────────────────────────────────────────────────────────────────
_font_cache: Dict[Tuple, ImageFont.FreeTypeFont] = {}

def _load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    key = (font_path, size)
    if key in _font_cache:
        return _font_cache[key]

    font = None
    if font_path and os.path.exists(font_path):
        font = ImageFont.truetype(font_path, size)
    else:
        fallbacks = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        for fb in fallbacks:
            if os.path.exists(fb):
                font = ImageFont.truetype(fb, size)
                break

    if font is None:
        font = ImageFont.load_default()

    _font_cache[key] = font
    return font


# ─────────────────────────────────────────────────────────────────────────────
#  MEASURE WORD ACCURATELY
# ─────────────────────────────────────────────────────────────────────────────
_measure_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

def _measure(text: str, font: ImageFont.FreeTypeFont, padding: int) -> Tuple[int, int, tuple]:
    """Returns box_w, box_h, raw_bbox."""
    bbox = _measure_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    return tw + padding * 2, th + padding * 2, bbox


# ─────────────────────────────────────────────────────────────────────────────
#  HIGHLIGHT STRATEGIES
# ─────────────────────────────────────────────────────────────────────────────
HIGHLIGHT_STRATEGIES = {
    "every_nth":  lambda i, words, n=2: i % n == 0,
    "random":     lambda i, words, seed=42: random.Random(seed + i).random() > 0.55,
    "long_words": lambda i, words, min_len=4: len(words[i]["word"].strip(".,!?;:")) >= min_len,
    "none":       lambda i, words: False,
    "all":        lambda i, words: True,
    "nouns_caps": lambda i, words: words[i]["word"][0].isupper() and i != 0,
}


# ─────────────────────────────────────────────────────────────────────────────
#  LAYOUT ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def _compute_layout(
    words: List[Dict],
    font_path: Optional[str],
    base_size: int,
    highlight_size: int,
    highlight_fn: Callable,
    rhythm_fn: Callable,
    words_in_window: int,
    word_spacing: int,
    line_spacing: int,
    padding: int,
    canvas_width: int,
) -> List[Dict]:
    """
    Pre-bake layout for every word.
    Font sizes follow the rhythm pattern applied to the sliding window.
    """
    n = len(words)
    laid: List[Dict] = []

    for i, wd in enumerate(words):
        is_hl = highlight_fn(i, words)

        # ── Rhythm-based size within current window ────────────
        win_start = max(0, i - words_in_window + 1)
        win_i     = i - win_start          # position inside window
        win_n     = min(words_in_window, i + 1)
        scale     = rhythm_fn(win_i, win_n)

        if is_hl:
            size = highlight_size
        else:
            size = max(12, int(base_size * scale))

        font        = _load_font(font_path, size)
        bw, bh, raw = _measure(wd["word"], font, padding)

        laid.append({
            **wd,
            "font":         font,
            "size":         size,
            "is_highlighted": is_hl,
            "w":            bw,
            "h":            bh,
            "raw_bbox":     raw,
        })

    # ── Wrap into lines based on canvas_width ─────────────────
    lines: List[List[Dict]] = []
    line: List[Dict] = []
    x = 0

    for wd in laid:
        if line and x + wd["w"] > canvas_width:
            lines.append(line)
            line = []
            x    = 0
        line.append(wd)
        x += wd["w"] + word_spacing

    if line:
        lines.append(line)

    # ── Assign pixel positions ─────────────────────────────────
    result: List[Dict] = []
    y = 0
    for ln in lines:
        line_h = max(w["h"] for w in ln)
        x = 0
        for wd in ln:
            wd_y = y + (line_h - wd["h"]) // 2
            result.append({**wd, "x": x, "y": wd_y, "line_h": line_h})
            x += wd["w"] + word_spacing
        y += line_h + line_spacing

    return result, y  # y = total height


# ─────────────────────────────────────────────────────────────────────────────
#  EASING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3

def _ease_out_expo(t: float) -> float:
    return 1 if t >= 1 else 1 - 2 ** (-10 * t)

def _ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


EASING = {
    "ease_out_cubic": _ease_out_cubic,
    "ease_out_expo":  _ease_out_expo,
    "ease_sine":      _ease_in_out_sine,
    "linear":         lambda t: t,
}


# ─────────────────────────────────────────────────────────────────────────────
#  SHADOW HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _draw_text_with_shadow(
    canvas: Image.Image,
    pos: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    color: Tuple,
    shadow_color: Tuple,
    shadow_offset: Tuple[int, int],
    shadow_blur: int,
    alpha: int,
):
    """Renders text with a soft blurred shadow onto canvas."""
    # ── Shadow layer ───────────────────────────────────────────
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sx = pos[0] + shadow_offset[0]
    sy = pos[1] + shadow_offset[1]
    sd.text((sx, sy), text, font=font, fill=(*shadow_color[:3], alpha))
    if shadow_blur > 0:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
    canvas.alpha_composite(shadow_layer)

    # ── Text ───────────────────────────────────────────────────
    d = ImageDraw.Draw(canvas)
    d.text(pos, text, font=font, fill=(*color[:3], alpha))


# ─────────────────────────────────────────────────────────────────────────────
#  APPEARANCE ANIMATIONS
# ─────────────────────────────────────────────────────────────────────────────
def _get_word_alpha_offset(
    elapsed: float,
    appear_duration: float,
    appear_style: str,
    easing_fn: Callable,
) -> Tuple[int, int, int]:
    """
    Returns (alpha 0-255, y_offset, x_offset) for appearance animation.
    """
    if elapsed >= appear_duration:
        return 255, 0, 0

    p = easing_fn(elapsed / appear_duration)  # 0 → 1

    alpha = int(255 * p)

    y_offset = 0
    x_offset = 0

    if appear_style == "slide_up":
        y_offset = int(18 * (1 - p))
    elif appear_style == "slide_down":
        y_offset = int(-18 * (1 - p))
    elif appear_style == "slide_right":
        x_offset = int(-14 * (1 - p))
    elif appear_style == "scale":
        pass   # handled separately in caller
    elif appear_style == "fade":
        pass   # just alpha

    return alpha, y_offset, x_offset


# ─────────────────────────────────────────────────────────────────────────────
#  FRAME RENDERER
# ─────────────────────────────────────────────────────────────────────────────
def _render_frame(
    t: float,
    laid_out: List[Dict],
    canvas_size: Tuple[int, int],
    # Window
    words_in_window: int,
    # Colors
    bg_color,
    normal_text_color,
    highlight_text_color,
    normal_box_color,
    highlight_box_color,
    normal_border_color,
    highlight_border_color,
    # Box style
    border_radius: int,
    border_width: int,
    padding: int,
    # Underline
    use_underline: bool,
    underline_color: Tuple,
    underline_thickness: int,
    # Shadow
    text_shadow: bool,
    shadow_color: Tuple = (0, 0, 0),
    shadow_blur: int = 6,
    shadow_offset: Tuple = (1, 2),
    # Animation
    appear_duration: float = 0.18,
    appear_style: str = "slide_up",
    easing: str = "ease_out_cubic",
    # Scale pop (separate from appear)
    scale_pop: bool = True,
    scale_pop_duration: float = 0.12,
    scale_pop_amount: float = 0.12,
) -> np.ndarray:

    W, H     = canvas_size
    canvas   = Image.new("RGBA", (W, H), bg_color)
    ease_fn  = EASING.get(easing, _ease_out_cubic)

    # ── Visible words ──────────────────────────────────────────
    visible = [wd for wd in laid_out if wd["start"] <= t]
    if words_in_window and len(visible) > words_in_window:
        visible = visible[-words_in_window:]
    if not visible:
        return np.array(canvas)

    # ── Re-center visible block vertically in canvas ──────────
    min_y  = min(wd["y"] for wd in visible)
    max_y  = max(wd["y"] + wd["h"] for wd in visible)
    blk_h  = max_y - min_y
    y_base = (H - blk_h) // 2 - min_y

    draw = ImageDraw.Draw(canvas)

    for wd in visible:
        elapsed  = t - wd["start"]
        is_hl    = wd["is_highlighted"]
        font     = wd["font"]
        text     = wd["word"]
        raw_bbox = wd["raw_bbox"]

        # ── Animation ─────────────────────────────────────────
        alpha, dy, dx = _get_word_alpha_offset(
            elapsed, appear_duration, appear_style, ease_fn
        )

        # ── Scale pop ─────────────────────────────────────────
        scale = 1.0
        if scale_pop and elapsed < scale_pop_duration:
            p     = elapsed / scale_pop_duration
            scale = 1.0 + scale_pop_amount * ease_fn(1 - p)

        # ── Box geometry ──────────────────────────────────────
        bx = wd["x"] + dx
        by = wd["y"] + y_base + dy
        bw = wd["w"]
        bh = wd["h"]
        cx = bx + bw / 2
        cy = by + bh / 2
        sbw = int(bw * scale)
        sbh = int(bh * scale)
        bx  = int(cx - sbw / 2)
        by  = int(cy - sbh / 2)

        # ── Colors with alpha ─────────────────────────────────
        box_col    = highlight_box_color    if is_hl else normal_box_color
        txt_col    = highlight_text_color   if is_hl else normal_text_color
        brd_col    = highlight_border_color if is_hl else normal_border_color

        box_rgba = (*box_col[:3], min(alpha, box_col[3] if len(box_col) == 4 else 255))
        brd_rgba = (*brd_col[:3], min(alpha, brd_col[3] if len(brd_col) == 4 else 255))

        # ── Draw box (if visible) ─────────────────────────────
        if box_rgba[3] > 0 and border_radius >= 0:
            draw.rounded_rectangle(
                [bx, by, bx + sbw, by + sbh],
                radius = border_radius,
                fill   = box_rgba,
                outline= brd_rgba if border_width > 0 else None,
                width  = border_width,
            )

        # ── Text position (centered inside box) ───────────────
        tw = raw_bbox[2] - raw_bbox[0]
        th = raw_bbox[3] - raw_bbox[1]
        tx = bx + (sbw - tw) // 2 - raw_bbox[0]
        ty = by + (sbh - th) // 2 - raw_bbox[1]

        # ── Draw text ─────────────────────────────────────────
        if text_shadow:
            _draw_text_with_shadow(
                canvas       = canvas,
                pos          = (tx, ty),
                text         = text,
                font         = font,
                color        = txt_col,
                shadow_color = shadow_color,
                shadow_offset= shadow_offset,
                shadow_blur  = shadow_blur,
                alpha        = alpha,
            )
        else:
            draw.text((tx, ty), text, font=font, fill=(*txt_col[:3], alpha))

        # ── Underline ─────────────────────────────────────────
        if use_underline and is_hl:
            ul_y = by + sbh - 4
            draw.rectangle(
                [tx, ul_y, tx + tw, ul_y + underline_thickness],
                fill=(*underline_color[:3], alpha),
            )

    return np.array(canvas)


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC CLASS
# ─────────────────────────────────────────────────────────────────────────────
class AestheticSubtitles:
    """
    Aesthetic incremental word-by-word subtitles for MoviePy 2.0.

    Quick start with a preset
    ─────────────────────────
    >>> subs = AestheticSubtitles(words, video_size=(1920,1080), preset="elegant_dark")

    Parameters
    ──────────
    transcription       Word-level list/json: [{word, start, end}, ...]
    video_size          (width, height) of target video
    position            "bottom" | "top" | "center" | (x, y)
    preset              One of: minimal_white, elegant_dark, glass, neon, bold_cards
    font_path           Path to .ttf/.otf (None = auto fallback)
    base_size           Normal word font size
    highlight_size      Highlighted word font size
    highlight_strategy  "every_nth"|"random"|"long_words"|"none"|"all"|"nouns_caps"
                        or callable(i, words) -> bool
    highlight_kwargs    Extra kwargs for built-in strategies
    rhythm              "flat"|"wave"|"crescendo"|"highlight_focus"
                        Controls per-word size variation in each window
    words_in_window     Max visible words at once
    word_spacing        Horizontal gap between words (px)
    line_spacing        Vertical gap between lines (px)
    padding             Inner padding inside word boxes (px)
    appear_style        "slide_up"|"slide_down"|"slide_right"|"fade"|"scale"
    appear_duration     Seconds for appear animation
    easing              "ease_out_cubic"|"ease_out_expo"|"ease_sine"|"linear"
    scale_pop           Brief scale bounce on appear
    canvas_h_pad        Extra vertical padding on canvas
    """

    def __init__(
        self,
        transcription: Union[str, List[Dict]],
        video_size: Tuple[int, int] = (1920, 1080),
        position: Union[str, Tuple] = "bottom",
        # Preset overrides everything — then individual params override preset
        preset: Optional[str] = "elegant_dark",
        # Font
        font_path: Optional[str] = None,
        base_size: int = 58,
        highlight_size: int = 72,
        # Highlight
        highlight_strategy: Union[str, Callable] = "long_words",
        highlight_kwargs: Optional[Dict] = None,
        # Rhythm
        rhythm: str = "wave",
        # Layout
        words_in_window: int = 5,
        word_spacing: int = 18,
        line_spacing: int = 22,
        padding: int = 12,
        canvas_h_pad: int = 60,
        # Animation
        appear_style: str = "slide_up",
        appear_duration: float = 0.18,
        easing: str = "ease_out_cubic",
        scale_pop: bool = True,
        scale_pop_duration: float = 0.10,
        scale_pop_amount: float = 0.10,
        # Style (overridden by preset if preset given)
        bg_color               = (0, 0, 0, 0),
        normal_text_color      = (200, 200, 200),
        highlight_text_color   = (255, 255, 255),
        normal_box_color       = (0, 0, 0, 0),
        highlight_box_color    = (0, 0, 0, 0),
        normal_border_color    = (0, 0, 0, 0),
        highlight_border_color = (0, 0, 0, 0),
        border_radius: int     = 0,
        border_width: int      = 0,
        use_underline: bool    = False,
        underline_color        = (255, 255, 255),
        underline_thickness: int = 2,
        text_shadow: bool      = True,
        shadow_color           = (0, 0, 0),
        shadow_blur: int       = 8,
        shadow_offset          = (2, 3),
    ):
        # ── Parse transcription ───────────────────────────────
        if isinstance(transcription, str):
            self.words = json.loads(transcription)
        else:
            self.words = list(transcription)
        if not self.words:
            raise ValueError("Transcription is empty.")

        # ── Apply preset then allow override ──────────────────
        style = {}
        if preset and preset in PRESETS:
            style.update(PRESETS[preset])

        # Manual overrides (only if preset didn't set them, or user explicitly passed)
        local_style = dict(
            bg_color=bg_color, normal_text_color=normal_text_color,
            highlight_text_color=highlight_text_color,
            normal_box_color=normal_box_color, highlight_box_color=highlight_box_color,
            normal_border_color=normal_border_color, highlight_border_color=highlight_border_color,
            border_radius=border_radius, border_width=border_width,
            use_underline=use_underline, underline_color=underline_color,
            underline_thickness=underline_thickness, text_shadow=text_shadow,
            shadow_color=shadow_color, shadow_blur=shadow_blur, shadow_offset=shadow_offset,
        )
        if not preset:
            style.update(local_style)
        self._style = style

        # ── Highlight fn ──────────────────────────────────────
        hl_kw = highlight_kwargs or {}
        if callable(highlight_strategy):
            self._hl_fn = highlight_strategy
        else:
            base_fn = HIGHLIGHT_STRATEGIES[highlight_strategy]
            self._hl_fn = lambda i, w, _f=base_fn, _kw=hl_kw: _f(i, w, **_kw)

        # ── Rhythm fn ─────────────────────────────────────────
        self._rhythm_fn = RHYTHM_PATTERNS.get(rhythm, _rhythm_wave)

        # ── Layout ────────────────────────────────────────────
        self.video_size  = video_size
        self.position    = position
        self._font_path  = font_path
        self._base_size  = base_size
        self._hl_size    = highlight_size

        self._laid_out, total_h = _compute_layout(
            words           = self.words,
            font_path       = font_path,
            base_size       = base_size,
            highlight_size  = highlight_size,
            highlight_fn    = self._hl_fn,
            rhythm_fn       = self._rhythm_fn,
            words_in_window = words_in_window,
            word_spacing    = word_spacing,
            line_spacing    = line_spacing,
            padding         = padding,
            canvas_width    = video_size[0] - 120,  # side margins
        )

        self.canvas_width  = video_size[0]
        self.canvas_height = max(total_h + canvas_h_pad, highlight_size * 3)
        self.duration      = self.words[-1]["end"]

        # ── Store animation params ────────────────────────────
        self._anim = dict(
            words_in_window    = words_in_window,
            appear_style       = appear_style,
            appear_duration    = appear_duration,
            easing             = easing,
            scale_pop          = scale_pop,
            scale_pop_duration = scale_pop_duration,
            scale_pop_amount   = scale_pop_amount,
            padding            = padding,
        )

    # ─────────────────────────────────────────────────────────
    def make_clip(self) -> VideoClip:
        laid_out = self._laid_out
        style    = self._style
        anim     = self._anim
        size     = (self.canvas_width, self.canvas_height)
        duration = self.duration

        def make_frame(t):
            return _render_frame(t=t, laid_out=laid_out,
                                 canvas_size=size, **anim, **style)

        clip = VideoClip(make_frame, duration=duration)

        # ── Position ──────────────────────────────────────────
        vw, vh = self.video_size
        if self.position == "bottom":
            pos = ("center", vh - self.canvas_height - 50)
        elif self.position == "top":
            pos = ("center", 50)
        elif self.position == "center":
            pos = ("center", "center")
        else:
            pos = tuple(self.position)

        return clip.with_position(pos)

    def composite_on(self, video) -> CompositeVideoClip:
        return CompositeVideoClip([video, self.make_clip()])

    def preview(self, t: float = 0.8) -> Image.Image:
        """PIL preview of a single frame. No moviepy needed."""
        frame = _render_frame(
            t=t, laid_out=self._laid_out,
            canvas_size=(self.canvas_width, self.canvas_height),
            **{**self._anim, "appear_duration": 0},   # skip animation in preview
            **self._style,
        )
        return Image.fromarray(frame)

if __name__ == "__main__":
    words = [
        {'word': 'Hello',     'start': 0.0,  'end': 0.28},
        {'word': 'world,',    'start': 0.34, 'end': 0.59},
        {'word': 'how',       'start': 0.62, 'end': 0.77},
        {'word': 'are',       'start': 0.82, 'end': 0.97},
        {'word': 'you',       'start': 1.03, 'end': 1.39},
        {'word': 'doing',     'start': 1.42, 'end': 1.80},
        {'word': 'today?',    'start': 1.85, 'end': 2.30},
    ]

    video = ColorClip(color=(0, 0, 0), duration=10, size=(1080, 1920))


    # ── 1. Elegant Dark (clean, shadow-based, no boxes) ──────────
    subs = AestheticSubtitles(
        transcription = words,
        video_size    = video.size,
        preset        = "elegant_dark",
        rhythm        = "wave",           # center word biggest
        appear_style  = "slide_up",
        font_path     = "Montserrat-Black.ttf",
    )


    # ── 2. Glass morphism ────────────────────────────────────────
    subs2 = AestheticSubtitles(
        transcription = words,
        video_size    = video.size,
        preset        = "glass",
        rhythm        = "highlight_focus",
        appear_style  = "fade",
        highlight_strategy = "long_words",
    )


    # ── 3. Neon with glow ────────────────────────────────────────
    subs3 = AestheticSubtitles(
        transcription = words,
        video_size    = video.size,
        preset        = "neon",
        rhythm        = "crescendo",
        appear_style  = "slide_right",
        easing        = "ease_out_expo",
    )


    # ── 4. Bold Cards (high contrast) ────────────────────────────
    subs4 = AestheticSubtitles(
        transcription      = words,
        video_size         = video.size,
        preset             = "bold_cards",
        rhythm             = "wave",
        highlight_strategy = "every_nth",
        highlight_kwargs   = {"n": 3},
        appear_style       = "slide_up",
        scale_pop          = True,
    )


    # ── 5. Fully custom (no preset) ──────────────────────────────
    subs5 = AestheticSubtitles(
        transcription          = words,
        video_size             = video.size,
        preset                 = None,          # disable preset
        font_path              = "Montserrat-Black.ttf",
        base_size              = 54,
        highlight_size         = 76,
        rhythm                 = "wave",
        highlight_strategy     = "long_words",
        normal_text_color      = (180, 180, 180),
        highlight_text_color   = (255, 255, 255),
        normal_box_color       = (0, 0, 0, 0),
        highlight_box_color    = (0, 0, 0, 0),
        text_shadow            = True,
        shadow_blur            = 10,
        shadow_color           = (0, 0, 0),
        shadow_offset          = (2, 4),
        appear_style           = "slide_up",
        easing                 = "ease_out_expo",
        words_in_window        = 5,
    )


    # ── Render ────────────────────────────────────────────────────
    final = subs3.composite_on(video)
    final.write_videofile("output.mp4", fps=30, codec="libx264")

    # ── Quick frame preview ───────────────────────────────────────
    subs3.preview(t=1.2).save("preview.png")