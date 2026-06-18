#make_dark_plots
#author: Facundo Franchino
"""derive dark-mode variants of the readme plots.

the figures in plots/ are styled for the paper, on a white page. the
readme serves them through a <picture> element so dark-mode viewers get
a dark variant instead. a matplotlib figure is dark ink on white, so a
colour inversion followed by a 180-degree hue rotation turns it into
white ink on a dark canvas whilst preserving the hue of the coloured
data lines. this is the baked-in equivalent of the css
`filter: invert(1) hue-rotate(180deg)` trick, since github sanitises
inline styles out of the rendered readme.

run after make_plots.py, whenever the light figures change.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

#the light figures the readme embeds; each gains a "-dark" sibling
FIGURES = ("equivalence", "rt60_validation", "scaling")


def darken(src: Path, dst: Path) -> None:
    """invert then hue-rotate a figure into its dark-mode variant."""
    rgb = Image.open(src).convert("RGB")
    inverted = 255 - np.asarray(rgb)
    #rotate hue by 180 degrees so coloured lines keep their identity
    hsv = np.asarray(Image.fromarray(inverted).convert("HSV")).copy()
    hsv[..., 0] = (hsv[..., 0].astype(int) + 128) % 256
    Image.fromarray(hsv, "HSV").convert("RGB").save(dst)


def main() -> None:
    plots = Path(__file__).resolve().parent.parent / "plots"
    for name in FIGURES:
        src = plots / f"{name}.png"
        if not src.exists():
            print(f"skip {name}: {src} missing")
            continue
        dst = plots / f"{name}-dark.png"
        darken(src, dst)
        print(f"wrote {dst.relative_to(plots.parent)}")


if __name__ == "__main__":
    main()
