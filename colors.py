"""24-bit ANSI TrueColor yardımcıları ve ısı haritası gradyanı (0 bağımlılık)."""
import os
import re
import sys

ESC = "\x1b"
RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"
DIM = f"{ESC}[2m"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
ALT_SCREEN_ON = f"{ESC}[?1049h"
ALT_SCREEN_OFF = f"{ESC}[?1049l"
HOME = f"{ESC}[H"
CLEAR = f"{ESC}[2J{ESC}[H"

RGB = tuple  # (r, g, b)

# Isı haritası durakları: Koyu Mavi -> Siyan -> Sarı -> Alev Kırmızı
HEAT_STOPS = (
    (0.00, (12, 24, 110)),
    (0.33, (0, 215, 230)),
    (0.66, (255, 230, 40)),
    (1.00, (235, 40, 15)),
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def fg(r, g, b):
    return f"{ESC}[38;2;{int(r)};{int(g)};{int(b)}m"


def bg(r, g, b):
    return f"{ESC}[48;2;{int(r)};{int(g)};{int(b)}m"


def paint(text, fore=None, back=None, bold=False):
    """Metni 24-bit ön/arka plan renkleriyle sarar ve RESET ile kapatır."""
    pre = ""
    if bold:
        pre += BOLD
    if fore is not None:
        pre += fg(*fore)
    if back is not None:
        pre += bg(*back)
    return f"{pre}{text}{RESET}" if pre else text


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgb(c1, c2, t):
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


def heat_color(t):
    """0..1 aralığını Koyu Mavi -> Siyan -> Sarı -> Alev Kırmızı renge çevirir."""
    t = 0.0 if t != t else max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(HEAT_STOPS, HEAT_STOPS[1:]):
        if t <= t1:
            return lerp_rgb(c0, c1, (t - t0) / (t1 - t0))
    return HEAT_STOPS[-1][1]


def heat_gradient(n):
    """n adımlık gradyan renk listesi üretir."""
    if n <= 1:
        return [heat_color(0.0)]
    return [heat_color(i / (n - 1)) for i in range(n)]


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_fg(rgb):
    """Arka plana göre okunaklı (siyah/beyaz) yazı rengi."""
    return (0, 0, 0) if luminance(rgb) > 140 else (255, 255, 255)


def gradient_bar(width, label_lo="", label_hi=""):
    """Yatay gradyan çubuğu (açıklama için)."""
    cells = "".join(bg(*heat_color(i / max(1, width - 1))) + " " for i in range(width))
    return f"{label_lo} {cells}{RESET} {label_hi}".strip()


def strip_ansi(s):
    return _ANSI_RE.sub("", s)


def visible_len(s):
    return len(strip_ansi(s))


def pad(s, width, align="left"):
    """Görünür uzunluğa göre doldurur; taşarsa ANSI'yi bozmadan keser."""
    n = visible_len(s)
    if n > width:
        return clip(s, width)
    gap = " " * (width - n)
    if align == "right":
        return gap + s
    if align == "center":
        left = (width - n) // 2
        return " " * left + s + " " * (width - n - left)
    return s + gap


def clip(s, width):
    """ANSI dizisini koruyarak görünür genişliği `width` ile sınırlar."""
    out, count, i = [], 0, 0
    while i < len(s) and count < width:
        m = _ANSI_RE.match(s, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        out.append(s[i])
        count += 1
        i += 1
    return "".join(out) + RESET


def enable_vt():
    """Windows konsolunda ANSI/VT işlemeyi açar ve stdout'u UTF-8 yapar."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False
