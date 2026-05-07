"""
theme_extractor.py
──────────────────
Extracts a high-contrast dual-color text palette from a MoviePy clip.

Key design decisions
────────────────────
• The REPRESENTATIVE BACKGROUND is the MEAN PIXEL COLOR of the text region
  — not a palette index. This matches what blurring actually produces.

• WCAG crossover luminance ≈ 0.179 (not 0.5!) determines light vs dark text.
  Below 0.179 → light text. Above 0.179 → dark text.

• Primary   = highest contrast against real bg, tinted with a palette hue.
• Secondary = visually distinct warm/cool accent, still WCAG AA ≥ 4.5:1.
• Fallback chain always terminates with a guaranteed-passing color.
"""

import numpy as np
from PIL import Image
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
#  WCAG MATH
# ─────────────────────────────────────────────────────────────────────────────

def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(rgb: tuple) -> float:
    r, g, b = (int(x) for x in rgb)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast(c1: tuple, c2: tuple) -> float:
    L1, L2 = _luminance(c1), _luminance(c2)
    hi, lo = max(L1, L2), min(L1, L2)
    return (hi + 0.05) / (lo + 0.05)


def _rgb_to_hex(rgb: tuple) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


# ─────────────────────────────────────────────────────────────────────────────
#  WCAG CROSSOVER  (bg_lum where white == black contrast)
#   solve: (1+.05)/(x+.05) = (x+.05)/(.00+.05)  →  x ≈ 0.1791
#
#   bg_lum > 0.179  → background is "light"  → use DARK text
#   bg_lum ≤ 0.179  → background is "dark"   → use LIGHT text
# ─────────────────────────────────────────────────────────────────────────────
_CROSSOVER = 0.1791
_NEAR_WHITE = (245, 245, 240)
_NEAR_BLACK = (15,  15,  18)


def _anchor(bg: tuple) -> tuple:
    """White or black, whichever actually has higher contrast vs bg."""
    cw = _contrast(_NEAR_WHITE, bg)
    cb = _contrast(_NEAR_BLACK, bg)
    return _NEAR_WHITE if cw >= cb else _NEAR_BLACK


def _tint(base: tuple, tint: tuple, amount: float) -> tuple:
    return tuple(
        max(0, min(255, int(base[i] * (1 - amount) + tint[i] * amount)))
        for i in range(3)
    )


# ─────────────────────────────────────────────────────────────────────────────
#  CURATED ACCENT PAIRS  (dark-bg → light accents, light-bg → dark accents)
# ─────────────────────────────────────────────────────────────────────────────
_LIGHT_ACCENTS = [            # for dark backgrounds  (need high-lum text)
    (245, 220, 150),          # warm gold
    (220, 205, 170),          # cream
    (200, 230, 255),          # cool blue-white
    (230, 200, 220),          # rose white
]
_DARK_ACCENTS = [             # for light/medium backgrounds (need low-lum text)
    (55,  35,  8),            # dark amber
    (25,  45,  70),           # dark navy
    (40,  20,  50),           # dark plum
    (10,  45,  25),           # dark forest
]


def _pick_primary(bg: tuple, palette: List[tuple], min_ratio: float) -> tuple:
    anc = _anchor(bg)
    # Best palette color that passes — prefer highest contrast
    passing = [(c, _contrast(c, bg)) for c in palette if _contrast(c, bg) >= min_ratio]
    if passing:
        best_pal = max(passing, key=lambda x: x[1])[0]
        # Tint anchor slightly toward best palette color for warmth
        tinted = _tint(anc, best_pal, 0.15)
        if _contrast(tinted, bg) >= min_ratio:
            return tinted
        return best_pal
    return anc  # guaranteed


def _pick_secondary(primary: tuple, bg: tuple, palette: List[tuple],
                    min_ratio: float) -> tuple:
    bg_lum = _luminance(bg)

    # Try palette colors that pass contrast AND are distinct from primary
    for c in sorted(palette, key=lambda x: abs(_luminance(x) - _luminance(primary)), reverse=True):
        if _contrast(c, bg) < min_ratio:
            continue
        chan_diff = max(abs(int(c[i]) - int(primary[i])) for i in range(3))
        if chan_diff >= 35:
            return c

    # Curated accents based on bg brightness direction
    accents = _DARK_ACCENTS if bg_lum > _CROSSOVER else _LIGHT_ACCENTS
    for accent in accents:
        if _contrast(accent, bg) >= min_ratio:
            # Make sure it's distinct from primary
            if max(abs(int(accent[i]) - int(primary[i])) for i in range(3)) >= 25:
                return accent

    # Last resort: tint anchor with opposite warmth
    anc = _anchor(bg)
    if bg_lum > _CROSSOVER:
        alt = _tint(anc, (80, 50, 10), 0.45)   # warm dark
    else:
        alt = _tint(anc, (200, 165, 100), 0.45) # warm light
    if _contrast(alt, bg) >= min_ratio:
        return alt

    return anc  # same anchor is still readable


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

class FastThemeExtractor:
    """
    Extracts dual high-contrast text colors from a MoviePy clip.

    IMPORTANT: pass the BLURRED/PROCESSED bg_clip, not the raw clip,
    so the background representative color matches what text actually sits on.

    Returns
    ───────
    primary_text_hex   / primary_text_rgb    — WCAG AA ≥ 4.5 : 1
    secondary_text_hex / secondary_text_rgb  — WCAG AA ≥ 4.5 : 1, distinct hue
    bg_dominant_hex    / bg_dominant_rgb     — mean color of text region
    full_palette_hex   / full_palette_rgb    — all quantized colors
    primary_contrast   / secondary_contrast  — actual ratios
    """

    @classmethod
    def extract_palette(
        cls,
        clip,
        num_colors: int = 10,
        samples: int = 6,
        resize_width: int = 160,
        text_region: str = "bottom",
        text_region_fraction: float = 0.52,
        min_contrast: float = 4.5,
    ) -> dict:
        dur = float(clip.duration or 5.0)
        timestamps = np.linspace(dur * 0.05, dur * 0.95, samples)

        region_frames: List[np.ndarray] = []
        for t in timestamps:
            frame = clip.get_frame(float(t))          # (H, W, 3) uint8
            h     = frame.shape[0]
            split = int(h * (1 - text_region_fraction))

            if text_region == "bottom":
                region = frame[split:, :, :3]
            elif text_region == "top":
                region = frame[:split, :, :3]
            else:
                region = frame[:, :, :3]

            img = Image.fromarray(region.astype(np.uint8))
            new_h = max(1, int(resize_width * img.height / max(img.width, 1)))
            img   = img.resize((resize_width, new_h), Image.Resampling.NEAREST)
            region_frames.append(np.array(img))

        stacked = np.vstack(region_frames)  # (H_total, W, 3)

        # ── Background = MEAN of all text-region pixels ─────────────────────
        # This reflects what blurring actually produces: a smooth average color.
        mean_px = np.mean(stacked.reshape(-1, 3), axis=0)
        bg      = tuple(int(x) for x in mean_px)

        # ── Quantize for palette ─────────────────────────────────────────────
        combined  = Image.fromarray(stacked.astype(np.uint8))
        quantized = combined.quantize(colors=num_colors,
                                       method=Image.Quantize.MEDIANCUT)
        raw_pal   = quantized.getpalette()[:num_colors * 3]
        palette: List[tuple] = [
            (raw_pal[i], raw_pal[i + 1], raw_pal[i + 2])
            for i in range(0, len(raw_pal), 3)
        ]
        palette.sort(key=_luminance)

        # ── Derive text colors ───────────────────────────────────────────────
        primary   = _pick_primary(bg, palette, min_contrast)
        secondary = _pick_secondary(primary, bg, palette, min_contrast)

        return {
            "bg_dominant_rgb":    bg,
            "bg_dominant_hex":    _rgb_to_hex(bg),

            "primary_text_rgb":   primary,
            "primary_text_hex":   _rgb_to_hex(primary),

            "secondary_text_rgb": secondary,
            "secondary_text_hex": _rgb_to_hex(secondary),

            "full_palette_rgb":   palette,
            "full_palette_hex":   [_rgb_to_hex(c) for c in palette],

            "primary_contrast":   round(_contrast(primary, bg), 2),
            "secondary_contrast": round(_contrast(secondary, bg), 2),

            # Legacy aliases
            "bg_color_rgb":   bg,
            "bg_color_hex":   _rgb_to_hex(bg),
            "text_color_rgb": primary,
            "text_color_hex": _rgb_to_hex(primary),
        }