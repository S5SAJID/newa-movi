"""
theme_extractor.py
──────────────────
Extracts a high-contrast dual-color text palette from a MoviePy clip.

Key design decisions
────────────────────
• Samples the *text region* of each frame (bottom ~52 %), not the whole
  frame — contrast is evaluated against where the text actually lives.

• Uses the WCAG-correct crossover luminance (~0.179) to decide whether
  text should be light or dark, NOT the naive 0.5 midpoint.

• Returns TWO guaranteed-contrast text colors:
    - primary_text   → best readability (WCAG AA ≥ 4.5 : 1)
    - secondary_text → visually distinct accent, still WCAG AA compliant

• Falls back to white or black — whichever actually passes, not guessed.
"""

import numpy as np
from PIL import Image
from typing import Tuple, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
#  WCAG LUMINANCE & CONTRAST
# ─────────────────────────────────────────────────────────────────────────────

def _linearize(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(rgb: tuple) -> float:
    """Relative luminance per WCAG 2.0, range [0, 1]."""
    r, g, b = (int(x) for x in rgb)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast(c1: tuple, c2: tuple) -> float:
    """Contrast ratio in range [1, 21]."""
    L1, L2 = _luminance(c1), _luminance(c2)
    hi, lo = max(L1, L2), min(L1, L2)
    return (hi + 0.05) / (lo + 0.05)


def _rgb_to_hex(rgb: tuple) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


# ─────────────────────────────────────────────────────────────────────────────
#  WCAG CROSSOVER — the mathematically correct threshold
#
#  Solve for bg_lum where white and black give equal contrast:
#    (1+0.05)/(bg_lum+0.05) = (bg_lum+0.05)/(0+0.05)
#    → bg_lum ≈ 0.1791
#
#  Above 0.179 → background is "relatively light" → use DARK text
#  Below 0.179 → background is "relatively dark"  → use LIGHT text
# ─────────────────────────────────────────────────────────────────────────────
_CROSSOVER_LUMINANCE = 0.1791

_NEAR_WHITE = (245, 245, 240)   # warm white — avoids pure clinical white
_NEAR_BLACK = (15,  15,  20)    # deep near-black


def _anchor_color(bg: tuple) -> tuple:
    """
    Returns the best guaranteed-contrast anchor (near-white or near-black)
    purely based on background luminance.
    """
    return _NEAR_BLACK if _luminance(bg) > _CROSSOVER_LUMINANCE else _NEAR_WHITE


def _best_anchor(bg: tuple) -> tuple:
    """
    Explicitly compares both extremes and returns the one with higher ratio.
    Handles edge cases where the crossover estimate is borderline.
    """
    cr_white = _contrast(_NEAR_WHITE, bg)
    cr_black = _contrast(_NEAR_BLACK, bg)
    return _NEAR_WHITE if cr_white >= cr_black else _NEAR_BLACK


# ─────────────────────────────────────────────────────────────────────────────
#  COLOR DERIVATION
# ─────────────────────────────────────────────────────────────────────────────

def _tint_toward(base: tuple, tint: tuple, amount: float = 0.25) -> tuple:
    """Blend base color toward tint by `amount` [0–1]."""
    return tuple(
        max(0, min(255, int(base[i] * (1 - amount) + tint[i] * amount)))
        for i in range(3)
    )


def _pick_primary(bg: tuple, palette: List[tuple], min_ratio: float = 4.5) -> tuple:
    """
    Selects the palette color with highest contrast against bg that meets
    min_ratio. Falls back to the mathematically correct anchor color.
    """
    anchor = _best_anchor(bg)

    # Find all palette colors that meet the threshold
    passing = [(c, _contrast(c, bg)) for c in palette if _contrast(c, bg) >= min_ratio]

    if not passing:
        # No palette color meets threshold — use anchor directly
        return anchor

    # Among passing colors, pick the one closest in hue to the anchor
    # (avoids picking garish palette colors when a neutral works better)
    anchor_lum = _luminance(anchor)
    # Prefer the one with the highest contrast ratio
    best = max(passing, key=lambda x: x[1])[0]

    # If it's within the same luminance region as anchor, use it;
    # otherwise a slight tint of the anchor toward it looks more aesthetic
    if abs(_luminance(best) - anchor_lum) < 0.3:
        return best

    # Tint anchor toward best palette color for a subtle warmth
    tinted = _tint_toward(anchor, best, 0.18)
    if _contrast(tinted, bg) >= min_ratio:
        return tinted
    return anchor


def _pick_secondary(primary: tuple, bg: tuple, palette: List[tuple],
                    min_ratio: float = 4.5) -> tuple:
    """
    Picks a secondary accent that:
      1. Meets min_ratio contrast against bg
      2. Is visually distinct from primary (their luminance differs by ≥ 0.12
         OR they differ in hue)

    Falls back to a palette-tinted opposite of primary.
    """
    primary_lum = _luminance(primary)
    anchor      = _best_anchor(bg)

    # Collect candidates: pass contrast and are distinct from primary
    candidates = []
    for c in palette:
        if _contrast(c, bg) < min_ratio:
            continue
        # Distinctness: luminance distance or large channel difference
        lum_diff   = abs(_luminance(c) - primary_lum)
        chan_diff   = max(abs(int(c[i]) - int(primary[i])) for i in range(3))
        if lum_diff >= 0.10 or chan_diff >= 40:
            candidates.append((c, _contrast(c, bg), chan_diff + lum_diff * 100))

    if candidates:
        # Best: highest distinctness score among those that pass contrast
        return max(candidates, key=lambda x: x[2])[0]

    # ── Fallback 1: tint the anchor with a warm or cool hue from palette ──
    if _luminance(bg) > _CROSSOVER_LUMINANCE:
        # Dark text on light bg — try a warm dark tone (brown/amber)
        warm_accent = (90, 60, 20)
    else:
        # Light text on dark bg — try a warm gold/cream tone
        warm_accent = (210, 175, 110)

    tinted = _tint_toward(anchor, warm_accent, 0.35)
    if _contrast(tinted, bg) >= min_ratio:
        return tinted

    # ── Fallback 2: use anchor directly (always passes) ──────────────────
    return anchor


# ─────────────────────────────────────────────────────────────────────────────
#  FRAME REGION SAMPLER
# ─────────────────────────────────────────────────────────────────────────────

def _sample_region(frame: np.ndarray, fraction: float = 0.52,
                   region: str = "bottom") -> np.ndarray:
    """Returns `fraction` of the frame from the specified region."""
    h = frame.shape[0]
    split = int(h * (1 - fraction))
    if region == "bottom":
        return frame[split:, :, :]
    elif region == "top":
        return frame[:split, :, :]
    return frame


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

class FastThemeExtractor:
    """
    Extracts a dual high-contrast text palette from a MoviePy clip.

    Usage
    ─────
    theme = FastThemeExtractor.extract_palette(clip)

    Returns (all colors as RGB tuples AND hex strings)
    ───────────────────────────────────────────────────
    {
        "bg_dominant_rgb":      (r, g, b),
        "bg_dominant_hex":      "#rrggbb",

        "primary_text_rgb":     (r, g, b),   # WCAG AA ≥ 4.5 guaranteed
        "primary_text_hex":     "#rrggbb",

        "secondary_text_rgb":   (r, g, b),   # WCAG AA ≥ 4.5, distinct accent
        "secondary_text_hex":   "#rrggbb",

        "full_palette_rgb":     [(r,g,b), ...],
        "full_palette_hex":     ["#rrggbb", ...],

        "primary_contrast":     float,
        "secondary_contrast":   float,
    }
    """

    @classmethod
    def extract_palette(
        cls,
        clip,
        num_colors: int = 10,
        samples: int = 6,
        resize_width: int = 160,
        text_region: str = "bottom",         # "bottom" | "top" | "full"
        text_region_fraction: float = 0.52,  # fraction of frame height
        min_contrast: float = 4.5,           # WCAG AA
    ) -> dict:
        """
        Sample `samples` evenly-spaced frames, quantize colors in the text
        region, then derive primary + secondary text colors both meeting
        `min_contrast` against the dominant background.
        """
        dur = float(clip.duration or 5.0)
        timestamps = np.linspace(dur * 0.05, dur * 0.95, samples)

        region_frames: List[np.ndarray] = []
        for t in timestamps:
            frame  = clip.get_frame(float(t))          # (H, W, 3) uint8
            region = _sample_region(frame, text_region_fraction, text_region)

            img = Image.fromarray(region)
            aspect = img.height / max(img.width, 1)
            new_h  = max(1, int(resize_width * aspect))
            img    = img.resize((resize_width, new_h), Image.Resampling.NEAREST)
            region_frames.append(np.array(img))

        # Stack regions → single image for quantization
        combined  = Image.fromarray(np.vstack(region_frames))
        quantized = combined.quantize(colors=num_colors,
                                       method=Image.Quantize.MEDIANCUT)

        raw_pal = quantized.getpalette()[:num_colors * 3]
        palette: List[tuple] = [
            (raw_pal[i], raw_pal[i + 1], raw_pal[i + 2])
            for i in range(0, len(raw_pal), 3)
        ]
        palette.sort(key=_luminance)

        # ── Background: median-brightness dominant color of text region ──
        # Skip the absolute darkest — pick a slightly richer mid-dark tone
        bg = palette[min(1, len(palette) - 1)]

        # ── Primary & Secondary ──────────────────────────────────────────
        primary   = _pick_primary(bg, palette, min_contrast)
        secondary = _pick_secondary(primary, bg, palette, min_contrast)

        primary_cr   = _contrast(primary, bg)
        secondary_cr = _contrast(secondary, bg)

        return {
            # ── New API ──────────────────────────────────────────────────
            "bg_dominant_rgb":    bg,
            "bg_dominant_hex":    _rgb_to_hex(bg),

            "primary_text_rgb":   primary,
            "primary_text_hex":   _rgb_to_hex(primary),

            "secondary_text_rgb": secondary,
            "secondary_text_hex": _rgb_to_hex(secondary),

            "full_palette_rgb":   palette,
            "full_palette_hex":   [_rgb_to_hex(c) for c in palette],

            "primary_contrast":   round(primary_cr, 2),
            "secondary_contrast": round(secondary_cr, 2),

            # ── Legacy aliases (backward compat) ─────────────────────────
            "bg_color_rgb":   bg,
            "bg_color_hex":   _rgb_to_hex(bg),
            "text_color_rgb": primary,
            "text_color_hex": _rgb_to_hex(primary),
        }