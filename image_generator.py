import io
import os
import math
from datetime import datetime, timezone
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")

COLORS = {
    "bg": (11, 11, 15),
    "surface": (17, 17, 26),
    "surface2": (22, 22, 34),
    "border": (30, 30, 46),
    "text_primary": (245, 246, 250),
    "text_secondary": (140, 148, 163),
    "text_muted": (72, 80, 100),
    "accent_purple": (124, 58, 237),
    "accent_blue": (59, 130, 246),
    "low": (16, 185, 129),
    "medium": (245, 158, 11),
    "high": (239, 68, 68),
    "white": (255, 255, 255),
}

W, H = 920, 510

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        path = FONT_BOLD if bold else FONT_REGULAR
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def _risk_color(classification: str) -> tuple[int, int, int]:
    return {"LOW": COLORS["low"], "MEDIUM": COLORS["medium"], "HIGH": COLORS["high"]}.get(
        classification, COLORS["text_muted"]
    )

def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple,
    radius: int,
    fill: tuple,
    outline: Optional[tuple] = None,
    outline_width: int = 1,
) -> None:
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                            outline=outline, width=outline_width)

def _draw_gradient_bar(
    img: Image.Image, x0: int, y0: int, x1: int, y1: int,
    color_start: tuple, color_end: tuple, radius: int = 6
) -> None:
    width = x1 - x0
    if width <= 0:
        return
    bar = Image.new("RGBA", (width, y1 - y0), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)
    for i in range(width):
        t = i / max(width - 1, 1)
        r = int(color_start[0] * (1 - t) + color_end[0] * t)
        g = int(color_start[1] * (1 - t) + color_end[1] * t)
        b = int(color_start[2] * (1 - t) + color_end[2] * t)
        draw.line([(i, 0), (i, y1 - y0)], fill=(r, g, b, 255))
    mask = Image.new("L", (width, y1 - y0), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, width - 1, y1 - y0 - 1], radius=radius, fill=255)
    bar.putalpha(mask)
    img.alpha_composite(bar, dest=(x0, y0))

def _glow_circle(img: Image.Image, cx: int, cy: int, radius: int, color: tuple, alpha: int = 60) -> None:
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for r in range(radius, 0, -max(radius // 30, 1)):
        a = int(alpha * (1 - r / radius) ** 1.5)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, max(a, 0)))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=radius // 5))
    img.alpha_composite(glow)

def _paste_avatar(img: Image.Image, avatar_bytes: bytes, x: int, y: int, size: int) -> None:
    try:
        ava = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        result.paste(ava, mask=mask)
        border_size = size + 4
        border_img = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        ImageDraw.Draw(border_img).ellipse([0, 0, border_size - 1, border_size - 1],
                                           fill=(*COLORS["accent_purple"], 180))
        img.alpha_composite(border_img, dest=(x - 2, y - 2))
        img.alpha_composite(result, dest=(x, y))
    except Exception:
        draw = ImageDraw.Draw(img)
        draw.ellipse([x, y, x + size, y + size], fill=COLORS["surface2"])
        f = _font(24, bold=True)
        draw.text((x + size // 2, y + size // 2), "?", font=f, fill=COLORS["text_muted"], anchor="mm")

def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

def generate_card(
    username: str,
    display_name: str,
    user_id: str,
    score: int,
    classification: str,
    reasons: list[str],
    account_age_days: int,
    avatar_bytes: Optional[bytes] = None,
) -> io.BytesIO:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bg = Image.new("RGBA", (W, H), (*COLORS["bg"], 255))

    _glow_circle(bg, -40, -40, 380, COLORS["accent_purple"], alpha=55)
    _glow_circle(bg, W + 40, H + 20, 300, COLORS["accent_blue"], alpha=35)

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=20, fill=255)
    img.paste(bg, mask=mask)

    draw = ImageDraw.Draw(img)

    _draw_gradient_bar(img, 0, 0, W, 4, COLORS["accent_purple"], COLORS["accent_blue"], radius=0)

    PAD = 36

    f_logo = _font(20, bold=True)
    f_subtitle = _font(11)
    f_label = _font(9)
    f_username = _font(19, bold=True)
    f_meta = _font(12)
    f_score_large = _font(72, bold=True)
    f_score_label = _font(10)
    f_class_badge = _font(11, bold=True)
    f_signal = _font(13)
    f_signal_label = _font(9)
    f_footer = _font(11)
    f_breakdown = _font(11)

    logo_y = 22
    draw.text((PAD, logo_y), "NOTHIDE", font=f_logo, fill=COLORS["text_primary"])
    draw.text((PAD, logo_y + 26), "User Risk Intelligence", font=f_subtitle, fill=COLORS["text_muted"])

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ts_w = _text_width(draw, timestamp, f_subtitle)
    draw.text((W - PAD - ts_w, logo_y + 26), timestamp, font=f_subtitle, fill=COLORS["text_muted"])

    sep_y = 76
    draw.line([(PAD, sep_y), (W - PAD, sep_y)], fill=COLORS["border"], width=1)

    AVATAR_SIZE = 72
    avatar_x, avatar_y = PAD, sep_y + 16
    if avatar_bytes:
        _paste_avatar(img, avatar_bytes, avatar_x, avatar_y, AVATAR_SIZE)
    else:
        draw.ellipse([avatar_x, avatar_y, avatar_x + AVATAR_SIZE, avatar_y + AVATAR_SIZE],
                     fill=COLORS["surface2"])

    name_x = avatar_x + AVATAR_SIZE + 16
    draw.text((name_x, avatar_y + 4), display_name[:28], font=f_username, fill=COLORS["text_primary"])
    draw.text((name_x, avatar_y + 30), f"@{username}", font=f_meta, fill=COLORS["text_secondary"])
    draw.text((name_x, avatar_y + 50), f"ID: {user_id}", font=f_meta, fill=COLORS["text_muted"])

    age_text = f"{account_age_days}d old" if account_age_days < 365 else f"{account_age_days//365}y {account_age_days%365}d old"
    age_color = COLORS["high"] if account_age_days < 14 else (COLORS["medium"] if account_age_days < 60 else COLORS["text_muted"])
    draw.text((name_x, avatar_y + 50), f"ID: {user_id}   ·   {age_text}", font=f_meta, fill=COLORS["text_muted"])

    risk_color = _risk_color(classification)

    score_section_y = sep_y + 16 + AVATAR_SIZE + 20
    draw_score_sep_y = score_section_y - 8
    draw.line([(PAD, draw_score_sep_y), (W - PAD, draw_score_sep_y)], fill=COLORS["border"], width=1)

    SCORE_BLOCK_W = 170
    score_cx = PAD + SCORE_BLOCK_W // 2
    draw.text((score_cx, score_section_y + 5), str(score), font=f_score_large,
              fill=risk_color, anchor="mt")

    draw.text((score_cx, score_section_y + 86), "RISK SCORE", font=f_score_label,
              fill=COLORS["text_muted"], anchor="mt")

    badge_x = PAD + SCORE_BLOCK_W + 20
    badge_y = score_section_y + 8

    badge_text = f"  {classification} RISK  "
    badge_tw = _text_width(draw, badge_text, f_class_badge) + 10
    badge_h = 28
    _draw_rounded_rect(draw, (badge_x, badge_y, badge_x + badge_tw, badge_y + badge_h),
                       radius=14, fill=(*risk_color, 30), outline=(*risk_color, 200), outline_width=1)
    draw.text((badge_x + badge_tw // 2, badge_y + badge_h // 2),
              f"{classification} RISK", font=f_class_badge, fill=risk_color, anchor="mm")

    bar_y = badge_y + badge_h + 16
    bar_x0 = badge_x
    bar_x1 = W - PAD
    bar_h = 10
    _draw_rounded_rect(draw, (bar_x0, bar_y, bar_x1, bar_y + bar_h),
                       radius=5, fill=COLORS["surface2"])

    fill_w = int((score / 100) * (bar_x1 - bar_x0))
    if fill_w > 10:
        start_col = COLORS["low"]
        mid_col = COLORS["medium"]
        end_col = COLORS["high"]
        if score < 50:
            cs, ce = start_col, mid_col
        else:
            cs, ce = mid_col, end_col
        _draw_gradient_bar(img, bar_x0, bar_y, bar_x0 + fill_w, bar_y + bar_h, cs, ce, radius=5)

    draw.text((bar_x0, bar_y + bar_h + 6), "0", font=f_score_label, fill=COLORS["text_muted"])
    draw.text(((bar_x0 + bar_x1) // 2, bar_y + bar_h + 6), "50",
              font=f_score_label, fill=COLORS["text_muted"], anchor="mt")
    draw.text((bar_x1, bar_y + bar_h + 6), "100",
              font=f_score_label, fill=COLORS["text_muted"], anchor="rt")

    signals_sep_y = score_section_y + 108
    draw.line([(PAD, signals_sep_y), (W - PAD, signals_sep_y)], fill=COLORS["border"], width=1)

    draw.text((PAD, signals_sep_y + 10), "KEY SIGNALS", font=f_signal_label, fill=COLORS["text_muted"])

    SIG_Y = signals_sep_y + 26
    SIG_SPACING = 28
    dot_radius = 4
    DOT_X = PAD + 6

    display_reasons = reasons[:4] if reasons else ["No notable risk indicators identified"]

    for i, reason in enumerate(display_reasons):
        y = SIG_Y + i * SIG_SPACING
        dot_color = risk_color if i < 2 else COLORS["text_muted"]
        draw.ellipse([DOT_X - dot_radius, y + 7 - dot_radius,
                      DOT_X + dot_radius, y + 7 + dot_radius], fill=dot_color)
        draw.text((DOT_X + dot_radius + 10, y), reason[:72], font=f_signal,
                  fill=COLORS["text_secondary"])

    footer_y = H - 36
    draw.line([(PAD, footer_y), (W - PAD, footer_y)], fill=COLORS["border"], width=1)
    footer_text = "NotHide — Detect What Others Miss"
    ft_w = _text_width(draw, footer_text, f_footer)
    draw.text((W // 2 - ft_w // 2, footer_y + 10), footer_text,
              font=f_footer, fill=COLORS["text_muted"])

    result = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    result.paste(img, mask=mask)

    output = io.BytesIO()
    result.save(output, "PNG", optimize=True)
    output.seek(0)
    return output
