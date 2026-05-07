from utils.theme_extractor import _luminance, _contrast, _best_anchor, _CROSSOVER_LUMINANCE, _NEAR_WHITE, _NEAR_BLACK, _rgb_to_hex

# Simulate the warm tan background from the screenshot
tan_bg = (190, 160, 120)   # warm golden-tan from screenshot

lum = _luminance(tan_bg)
cr_white = _contrast(_NEAR_WHITE, tan_bg)
cr_black = _contrast(_NEAR_BLACK, tan_bg)
anchor   = _best_anchor(tan_bg)

print(f'BG color:       {tan_bg}  hex={_rgb_to_hex(tan_bg)}')
print(f'BG luminance:   {lum:.4f}  (crossover={_CROSSOVER_LUMINANCE})')
print(f'Contrast white: {cr_white:.2f}:1')
print(f'Contrast black: {cr_black:.2f}:1')
print(f'Best anchor:    {_rgb_to_hex(anchor)}  ({anchor})')
print()
print('Old buggy logic (threshold=0.5):')
print(f'  Would pick:  {"dark" if lum > 0.5 else "LIGHT (WRONG)"}')
print()
print('New correct logic (threshold=0.179):')
print(f'  Will pick:   {"DARK" if lum > _CROSSOVER_LUMINANCE else "light"}  ← correct')
