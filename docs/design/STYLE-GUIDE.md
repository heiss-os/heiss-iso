# Style guide (tokens, first version)

Source of truth: `branding/tokens/heiss-tokens.json`. Edit it, then run `python3 scripts/gen-theme.py`. Outputs land in `branding/tokens/generated/` (KDE color schemes, GTK3/GTK4 named colors, kitty and Konsole themes). They are staged for the future `heiss-theme` package and are NOT yet installed into the image.

## Frozen vs derived

- Frozen (never change): the palette in the token file's `base` section and the KDE scheme layout. Test `tests/test_tokens.py` proves the generator reproduces every existing key of the shipped schemes.
- Added: `info` (blue, per theme) and the 16-color terminal palette. ANSI 1, 2, 3 in Dark reuse the frozen negative/positive/neutral.
- Derived (integer math, round half up): hover = mix(button, text, 8%), pressed = mix(button, text, 14%), border = mix(window, text, 14%), disabled text = mix(text, window, 55%), focus ring and selection = accent.

## Contrast findings from frozen values (Light theme)

These pairs are below WCAG AA 4.5:1 because of existing palette values. Nothing was changed; they need an owner decision (Tier A/B item):

| Pair | Ratio |
|---|---|
| accent #8C7448 on window / view / panel / button | 4.03 / 4.24 / 3.68 / 3.20 |
| text_secondary #6B6963 on button | 3.94 |
| on_accent #F5F3EF on accent | 4.03 |
| neutral #B7791F on window | 3.29 |
| positive #1F8A65 on window | 3.88 |

Dark has no failing pair. Not verified visually: where these pairs appear on screen (needs screenshots).

## Terminal palette

Terminal background = view color (`#1E1F21` Dark, `#FAF9F6` Light). ANSI 1-7 and 9-15 are at least 4.5:1, ANSI 0 and 8 at least 3:1 (asserted in CI). In Light the terminal selection uses accent_alt so selected text reaches 4.5:1. Not verified in a real Konsole or kitty yet.

## Motion, radii, spacing, fonts

Values live in the token file (`motion`, `radius`, `spacing`, `font`). Nothing consumes them yet.
