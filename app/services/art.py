"""Procedurally generated studio-style garment artwork (SVG).

Used as the default product imagery so the catalogue looks complete with no
external image dependencies. Uploading an image in the admin overrides it.
"""
from functools import lru_cache

# Silhouette paths on a 400x500 canvas. Each entry: (body path, detail svg)
_ZIP = '<path d="M200 70 L200 430" stroke="rgba(0,0,0,.35)" stroke-width="2"/><path d="M203 70 L203 430" stroke="rgba(255,255,255,.12)" stroke-width="1"/>'
_STITCH = 'stroke="rgba(255,255,255,.16)" stroke-width="1.2" stroke-dasharray="4 4" fill="none"'

GARMENTS = {
    "tee": (
        "M140 62 Q200 98 260 62 L342 98 L318 166 L276 148 L276 432 Q200 448 124 432 L124 148 L82 166 L58 98 Z",
        f'<path d="M140 62 Q200 118 260 62 Q200 92 140 62Z" fill="rgba(0,0,0,.45)"/>'
        f'<path d="M124 148 L124 430" {_STITCH}/><path d="M276 148 L276 430" {_STITCH}/>'
        f'<path d="M126 420 Q200 436 274 420" {_STITCH}/>',
    ),
    "tank": (
        "M152 52 L176 52 Q200 124 224 52 L248 52 L284 168 Q272 214 278 270 L278 432 Q200 448 122 432 L122 270 Q128 214 116 168 Z",
        f'<path d="M122 270 L122 430" {_STITCH}/><path d="M278 270 L278 430" {_STITCH}/>'
        f'<path d="M126 420 Q200 436 274 420" {_STITCH}/>',
    ),
    "shorts": (
        "M108 110 L292 110 L316 340 Q262 352 214 346 L200 214 L186 346 Q138 352 84 340 Z",
        '<rect x="108" y="110" width="184" height="26" fill="rgba(0,0,0,.28)"/>'
        '<path d="M130 148 L150 148" stroke="rgba(255,255,255,.35)" stroke-width="3" stroke-linecap="round"/>'
        f'<path d="M110 336 Q148 344 186 340" {_STITCH}/><path d="M290 336 Q252 344 214 340" {_STITCH}/>',
    ),
    "pants": (
        "M118 54 L282 54 L304 462 L226 468 L200 170 L174 468 L96 462 Z",
        '<rect x="118" y="54" width="164" height="28" fill="rgba(0,0,0,.28)"/>'
        '<path d="M130 100 L128 462" stroke="var(--trim)" stroke-width="4"/><path d="M270 100 L272 462" stroke="var(--trim)" stroke-width="4"/>'
        f'<path d="M104 452 Q140 460 176 456" {_STITCH}/><path d="M296 452 Q260 460 224 456" {_STITCH}/>',
    ),
    "jacket": (
        "M146 54 Q200 82 254 54 L334 90 L376 336 L330 342 L288 174 L288 434 L112 434 L112 174 L70 342 L24 336 L66 90 Z",
        '<path d="M146 54 L158 28 Q200 44 242 28 L254 54 Q200 90 146 54Z" fill="rgba(0,0,0,.4)"/>'
        + _ZIP
        + '<path d="M70 342 L112 174" stroke="var(--trim)" stroke-width="4"/><path d="M330 342 L288 174" stroke="var(--trim)" stroke-width="4"/>'
        '<rect x="226" y="300" width="42" height="3" fill="rgba(0,0,0,.35)"/><rect x="132" y="300" width="42" height="3" fill="rgba(0,0,0,.35)"/>',
    ),
    "hoodie": (
        "M146 70 Q200 96 254 70 L334 104 L376 346 L330 352 L288 186 L288 440 L112 440 L112 186 L70 352 L24 346 L66 104 Z",
        '<path d="M142 70 Q130 14 200 10 Q270 14 258 70 Q200 112 142 70Z" fill="rgba(0,0,0,.42)"/>'
        '<path d="M170 110 L166 170 M230 110 L234 170" stroke="rgba(255,255,255,.35)" stroke-width="2.5" stroke-linecap="round"/>'
        '<path d="M136 320 Q200 296 264 320 L276 400 Q200 414 124 400 Z" fill="rgba(0,0,0,.2)"/>',
    ),
    "compression": (
        "M148 58 Q200 88 252 58 L324 92 L354 400 L322 404 L284 176 L284 424 Q200 440 116 424 L116 176 L78 404 L46 400 L76 92 Z",
        '<path d="M148 58 Q200 108 252 58 Q200 82 148 58Z" fill="rgba(0,0,0,.45)"/>'
        '<path d="M116 176 Q200 200 284 176" stroke="rgba(255,255,255,.12)" stroke-width="1.5" fill="none"/>'
        '<path d="M200 96 L200 420" stroke="var(--trim)" stroke-width="3" opacity=".9"/>'
        f'<path d="M76 92 L46 400" {_STITCH}/><path d="M324 92 L354 400" {_STITCH}/>',
    ),
    "bra": (
        "M136 70 L162 70 L176 156 Q200 182 224 156 L238 70 L264 70 L292 214 Q200 262 108 214 Z M112 232 Q200 276 288 232 L288 300 Q200 330 112 300 Z",
        '<path d="M176 156 Q200 182 224 156" stroke="rgba(0,0,0,.4)" stroke-width="2" fill="none"/>'
        '<path d="M112 266 Q200 304 288 266" stroke="var(--trim)" stroke-width="3" fill="none"/>',
    ),
}


def _shade(hex_color, f):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if f >= 0:
        r, g, b = (int(c + (255 - c) * f) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1 + f)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _luma(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


@lru_cache(maxsize=512)
def garment_svg(garment: str, hex_color: str) -> str:
    garment = garment if garment in GARMENTS else "tee"
    base = "#" + hex_color.lstrip("#")[:6].ljust(6, "0")
    body, detail = GARMENTS[garment]
    light = _luma(base) > 0.6
    trim = "#c6ff3d" if not light else "#16161a"
    hi, lo = _shade(base, 0.16), _shade(base, -0.32)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" preserveAspectRatio="xMidYMid slice">
<defs>
<radialGradient id="bg" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="#2a2b2f"/><stop offset=".6" stop-color="#17171a"/><stop offset="1" stop-color="#0c0c0e"/></radialGradient>
<linearGradient id="fab" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{hi}"/><stop offset=".5" stop-color="{base}"/><stop offset="1" stop-color="{lo}"/></linearGradient>
<linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".32"/><stop offset=".3" stop-color="#000" stop-opacity="0"/><stop offset=".72" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#000" stop-opacity=".38"/></linearGradient>
<radialGradient id="floor" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#000" stop-opacity=".55"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .05 0"/></filter>
</defs>
<rect width="400" height="500" fill="url(#bg)"/>
<ellipse cx="200" cy="468" rx="130" ry="14" fill="url(#floor)"/>
<g style="--trim:{trim}">
<path d="{body}" fill="url(#fab)" stroke="rgba(0,0,0,.35)" stroke-width="1.5" stroke-linejoin="round"/>
<path d="{body}" fill="url(#sh)"/>
{detail}
</g>
<rect width="400" height="500" filter="url(#grain)"/>
</svg>"""


def hero_svg() -> str:
    """Wide cinematic hero: spotlight, motion lines and a hero jacket."""
    body, detail = GARMENTS["jacket"]
    lines = "".join(
        f'<rect x="{-200 + i * 53 % 700}" y="{90 + i * 42}" width="{260 + (i * 97) % 340}" height="2" fill="#fff" opacity="{0.05 + (i % 4) * 0.025}"/>'
        for i in range(14)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
<defs>
<radialGradient id="spot" cx="68%" cy="42%" r="55%"><stop offset="0" stop-color="#3a3c42"/><stop offset=".45" stop-color="#1a1b1e"/><stop offset="1" stop-color="#09090a"/></radialGradient>
<linearGradient id="fab" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4a4f57"/><stop offset=".5" stop-color="#25282d"/><stop offset="1" stop-color="#0f1013"/></linearGradient>
<linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".3"/><stop offset=".35" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></linearGradient>
<radialGradient id="floor" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#000" stop-opacity=".7"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="9"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .05 0"/></filter>
</defs>
<rect width="1600" height="900" fill="url(#spot)"/>
{lines}
<ellipse cx="1090" cy="838" rx="360" ry="28" fill="url(#floor)"/>
<g transform="translate(700 20) scale(1.95)" style="--trim:#c6ff3d">
<path d="{body}" fill="url(#fab)" stroke="rgba(0,0,0,.4)" stroke-width="1" stroke-linejoin="round"/>
<path d="{body}" fill="url(#sh)"/>{detail}
</g>
<rect width="1600" height="900" filter="url(#grain)"/>
</svg>"""
