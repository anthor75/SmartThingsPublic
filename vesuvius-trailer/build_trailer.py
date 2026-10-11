#!/usr/bin/env python3
"""VESUVIUS - teaser trailer builder (60 s, 1920x1080, 24 fps).

Renders every frame procedurally (Ken Burns, grading, flashes, shake, embers,
title cards), synthesizes a heartbeat-driven score + sound design, generates a
guide voice-over (espeak-ng + mbrola it3, pitched down) and muxes everything
with ffmpeg.

Two masters are written:
  vesuvius_trailer.mp4        - full mix with the guide voice-over
  vesuvius_trailer_noVO.mp4   - music + SFX only, ready for recording the real VO

Requirements: python3, numpy, pillow, scipy, ffmpeg (with rubberband),
espeak-ng, mbrola + mbrola-it3.
"""
import argparse
import math
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from scipy import signal

W, H, FPS, DUR = 1920, 1080, 24, 60.0
NFRAMES = int(DUR * FPS)
AR = 2.2                      # scope-ish aspect inside the 16:9 frame
CH = int(round(W / AR / 2) * 2)
BAR = (H - CH) // 2
SR = 48000
FONT_DIR = "/usr/share/fonts/opentype/inter"
F_BLACK = f"{FONT_DIR}/InterDisplay-Black.otf"
F_BOLD = f"{FONT_DIR}/InterDisplay-Bold.otf"
F_LIGHT = f"{FONT_DIR}/InterDisplay-Light.otf"

# --------------------------------------------------------------------------
# Script: voice-over lines (start time, text) - Italian, deep trailer voice
# --------------------------------------------------------------------------
VO_LINES = [
    (3.7, "Di giorno, guido aziende."),
    (6.85, "Numeri. Decisioni."),
    (9.9, "Ho sempre cercato il limite."),
    (14.2, "Ma sotto la superficie, qualcosa si muove."),
    (21.0, "Quando la terra trema, e la giustizia tace,"),
    (26.7, "qualcuno deve rispondere."),
    (30.5, "Allora, lascio uscire lui."),
    (46.6, "Io sono Antonello."),
    (50.7, "Vesuvius."),
    (55.7, "Ogni uomo ha un vulcano dentro."),
]

# Text cards: (start, end, text, style, size)
CARDS = [
    (0.6, 3.2, "NAPOLI.  OGGI.", "steel", 64),
    (9.0, 9.9, "INGEGNERE.", "steel", 96),
    (9.9, 10.8, "MANAGER.", "steel", 96),
    (10.8, 11.7, "SPORTIVO.", "steel", 96),
    (11.7, 12.9, "VISIONARIO.", "steel", 96),
    (20.6, 23.4, "QUANDO LA TERRA TREMA", "ember", 92),
    (23.7, 26.3, "QUANDO LA GIUSTIZIA TACE", "ember", 92),
    (26.5, 29.3, "QUALCUNO DEVE RISPONDERE", "ember", 92),
    (38.5, 39.3, "UN UOMO.", "fire", 150),
    (41.0, 41.8, "UN VULCANO.", "fire", 150),
    (43.5, 44.3, "UN'ANIMA SOLA.", "fire", 150),
    (55.5, 58.2, "OGNI UOMO HA UN VULCANO DENTRO.", "steel", 60),
    (58.2, 60.0, "PROSSIMAMENTE", "steel", 54),
]
# cards drawn over a picture instead of black
OVERLAY_CARDS = {"INGEGNERE.", "MANAGER.", "SPORTIVO.", "VISIONARIO."}


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lerp(a, b, x):
    return a + (b - a) * x


# --------------------------------------------------------------------------
# Graphics helpers
# --------------------------------------------------------------------------
def text_layer(text, style, size):
    """Return a tight RGBA image of the styled text with glow."""
    font = ImageFont.truetype(F_BLACK if style != "steel" or size > 80 else F_BOLD, size)
    tracking = int(size * (0.18 if style != "fire" else 0.08))
    widths = [font.getbbox(c)[2] - font.getbbox(c)[0] if c != " " else size // 3 for c in text]
    tw = sum(widths) + tracking * (len(text) - 1)
    asc, desc = font.getmetrics()
    pad = int(size * 0.9)
    w, h = tw + 2 * pad, asc + desc + 2 * pad
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    x = pad
    for c, cw in zip(text, widths):
        if c != " ":
            d.text((x - font.getbbox(c)[0], pad), c, font=font, fill=255)
        x += cw + tracking
    m = np.asarray(mask, np.float32) / 255.0
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    if style == "fire":
        top = np.array([255, 236, 150], np.float32)
        mid = np.array([255, 140, 20], np.float32)
        bot = np.array([170, 20, 0], np.float32)
        g = np.where((yy < 0.5)[..., None], lerp(top, mid, (yy / 0.5)[..., None]),
                     lerp(mid, bot, ((yy - 0.5) / 0.5)[..., None]))
        g = np.broadcast_to(g, (h, w, 3))
        glow_col, glow_r, glow_a = (255, 90, 0), size * 0.35, 1.3
    elif style == "ember":
        g = np.broadcast_to(lerp(np.array([255, 200, 160], np.float32),
                                 np.array([230, 40, 10], np.float32), yy[..., None]), (h, w, 3))
        glow_col, glow_r, glow_a = (220, 30, 0), size * 0.3, 0.9
    else:  # steel
        g = np.broadcast_to(lerp(np.array([255, 255, 255], np.float32),
                                 np.array([150, 160, 175], np.float32), yy[..., None]), (h, w, 3))
        glow_col, glow_r, glow_a = (180, 200, 255), size * 0.25, 0.35
    glow = np.asarray(mask.filter(ImageFilter.GaussianBlur(glow_r)), np.float32) / 255.0
    glow = np.clip(glow * glow_a, 0, 1)
    alpha = np.clip(m + glow * (1 - m), 0, 1)
    rgb = (g * m[..., None] + np.array(glow_col, np.float32) * (glow * (1 - m))[..., None])
    rgb = rgb / np.maximum(alpha[..., None], 1e-4)
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def crop_shot(img, cx, cy, cw, shake=(0.0, 0.0)):
    """Crop a window of width cw (content aspect) centred at cx,cy; return W x CH float array."""
    chh = cw / AR
    x0 = cx - cw / 2 + shake[0] * cw
    y0 = cy - chh / 2 + shake[1] * chh
    x0 = min(max(x0, 0), img.width - cw)
    y0 = min(max(y0, 0), img.height - chh)
    out = img.resize((W, CH), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + chh))
    return np.asarray(out, np.float32)


def grade(a, mode, amt=1.0):
    lum = (a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114)[..., None]
    if mode == "cold":
        a = lerp(a, lum, 0.55 * amt)
        a = a * np.array([0.88, 1.0, 1.12], np.float32)
        a = (a - 128) * 1.15 + 120
    elif mode == "warm":
        a = lerp(a, lum, 0.3 * amt)
        a = a * np.array([1.12, 0.95, 0.82], np.float32)
        a = (a - 128) * 1.2 + 124
    elif mode == "fire":
        a = lerp(lum, a, 1.0 + 0.35 * amt)
        a = (a - 128) * 1.25 + 130
        a = a * np.array([1.08, 0.98, 0.9], np.float32)
    return a


class Embers:
    def __init__(self, n=220, seed=7):
        r = np.random.default_rng(seed)
        self.x = r.uniform(0, W, n)
        self.y = r.uniform(0, H, n)
        self.v = r.uniform(40, 220, n)
        self.s = r.uniform(1.5, 5.0, n)
        self.ph = r.uniform(0, 6.28, n)
        self.b = r.uniform(0.4, 1.0, n)

    def layer(self, t, density=1.0):
        img = Image.new("RGB", (W // 2, H // 2), 0)
        d = ImageDraw.Draw(img)
        n = int(len(self.x) * min(density, 1.0))
        for i in range(n):
            x = (self.x[i] + 30 * math.sin(t * 1.3 + self.ph[i])) / 2
            y = ((self.y[i] - self.v[i] * t) % H) / 2
            s = self.s[i] / 2
            fl = self.b[i] * (0.6 + 0.4 * math.sin(t * 9 + self.ph[i]))
            d.ellipse((x - s, y - s, x + s, y + s), fill=(int(255 * fl), int(120 * fl), int(20 * fl)))
        glow = img.filter(ImageFilter.GaussianBlur(4))
        a = np.asarray(img, np.float32) + np.asarray(glow, np.float32) * 2.0
        return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W, H)), np.float32)


# --------------------------------------------------------------------------
# Picture
# --------------------------------------------------------------------------
def load_clip(path, tmp):
    raw = os.path.join(tmp, "clip.rgb")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-f", "rawvideo",
                    "-pix_fmt", "rgb24", raw], check=True)
    data = np.fromfile(raw, np.uint8)
    n = data.size // (560 * 560 * 3)
    return data[: n * 560 * 560 * 3].reshape(n, 560, 560, 3)


def render_video(args, tmp, out_path):
    office1 = Image.open(args.office1).convert("RGB")
    office2 = Image.open(args.office2).convert("RGB")
    head = Image.open(args.headshot).convert("RGB")
    poster = Image.open(args.poster).convert("RGB")
    clip = load_clip(args.clip, tmp)
    nclip = len(clip)
    clip_imgs = [Image.fromarray(f) for f in clip]

    cards = [(s, e, txt, text_layer(txt, st, sz)) for s, e, txt, st, sz in CARDS]
    title = text_layer("VESUVIUS", "fire", 230)
    subtitle = text_layer("IL PRIMO CAPITOLO", "steel", 40)
    embers = Embers()
    rng = np.random.default_rng(3)
    grains = [rng.normal(0, 6, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vign = 1 - 0.55 * np.clip(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2, 0, 1)
    vign = vign[..., None]

    def clip_shot(t, t0, t1, f0, f1, c0, c1):
        x = (t - t0) / (t1 - t0)
        fi = int(round(lerp(f0, f1, x)))
        fi = min(max(fi, 0), nclip - 1)
        cx, cy, cw = (lerp(c0[i], c1[i], ease(x)) for i in range(3))
        img = clip_imgs[fi]
        a = crop_shot(img, cx, cy, cw, shake=(rng.normal(0, 0.004), rng.normal(0, 0.004)))
        return grade(a, "fire", 0.6)

    def shot(img, t, t0, t1, c0, c1, mode, shake_amt=0.0):
        x = ease((t - t0) / (t1 - t0))
        cx, cy, cw = (lerp(c0[i], c1[i], x) for i in range(3))
        sh = (rng.normal(0, shake_amt), rng.normal(0, shake_amt)) if shake_amt else (0, 0)
        return grade(crop_shot(img, cx, cy, cw, sh), mode)

    def paste_layer(frame, layer, alpha, scale=1.0, cy=H / 2, dx=0.0):
        if alpha <= 0.01:
            return frame
        L = layer if abs(scale - 1) < 1e-3 else layer.resize(
            (max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.BICUBIC)
        la = np.asarray(L, np.float32)
        lw, lh = L.width, L.height
        x0 = int(W / 2 - lw / 2 + dx)
        y0 = int(cy - lh / 2)
        fx0, fy0 = max(x0, 0), max(y0, 0)
        fx1, fy1 = min(x0 + lw, W), min(y0 + lh, H)
        if fx1 <= fx0 or fy1 <= fy0:
            return frame
        sub = la[fy0 - y0: fy1 - y0, fx0 - x0: fx1 - x0]
        a = sub[..., 3:4] / 255.0 * alpha
        frame[fy0:fy1, fx0:fx1] = frame[fy0:fy1, fx0:fx1] * (1 - a) + sub[..., :3] * a
        return frame

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                           "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p", out_path],
                          stdin=subprocess.PIPE)

    for fi in range(NFRAMES):
        t = fi / FPS
        frame = np.zeros((H, W, 3), np.float32)
        content = None
        flash = 0.0           # >0 white flash, <0 red flash
        ember_d = 0.0
        fade = 1.0

        # ---------------- picture timeline ----------------
        if 3.2 <= t < 8.0:     # Antonello - profile, cold
            content = shot(office1, t, 3.2, 8.0, (966, 1380, 1932), (560, 1420, 1350), "cold")
            fade = ease((t - 3.2) / 0.6) * ease((8.0 - t) / 0.15)
            if 7.2 <= t < 7.29:  # subliminal flash of the poster
                content = shot(poster, t, 7.2, 7.3, (600, 415, 520), (600, 415, 500), "fire")
        elif 8.15 <= t < 13.0:  # selfie - looking at camera
            content = shot(office2, t, 8.15, 13.0, (966, 1450, 1932), (620, 1460, 1400), "cold")
            fade = ease((t - 8.15) / 0.2) * ease((13.0 - t) / 0.3)
            # darken the lower third so the overlay words read
            content = content * np.clip(1.25 - np.linspace(0, 1, CH, dtype=np.float32) ** 1.5, 0.3, 1)[:, None, None]
            if 12.55 <= t < 12.64:
                content = shot(poster, t, 12.5, 12.7, (600, 415, 480), (600, 415, 470), "fire")
        elif 13.4 <= t < 20.5:  # headshot push into the eyes, warming up
            k = (t - 13.4) / 7.1
            content = shot(head, t, 13.4, 20.5, (645, 610, 1290), (645, 540, 640),
                           "warm", shake_amt=0.006 * k ** 2)
            content = content * np.array([1 + 0.25 * k, 1 - 0.1 * k, 1 - 0.25 * k], np.float32)
            fade = ease((t - 13.4) / 0.8)
            if t >= 19.3 and int(t * 24) % 3 == 0:  # glitch into Vesuvius
                content = shot(poster, t, 19.3, 20.5, (560, 420, 640), (600, 415, 500), "fire")
                content = np.roll(content, 12, axis=1)
                content[..., 2] = np.roll(content[..., 2], -24, axis=1)
            ember_d = max(0, (k - 0.6)) * 0.8
        elif 23.4 <= t < 23.7 or 26.3 <= t < 26.5:  # flash frames between threat cards
            content = clip_shot(t, 23.4, 26.5, 2, 60, (280, 150, 300), (280, 200, 520)) * 0.75
            flash = -0.5
        elif 30.0 <= t < 35.0:  # the transformation - poster
            content = shot(poster, t, 30.0, 35.0, (543, 440, 1086), (600, 412, 430), "fire",
                           shake_amt=0.003 if t > 30.3 else 0.015)
            flash = max(0, 1 - (t - 30.0) / 0.35)
            ember_d = 1.0
        elif 35.0 <= t < 38.5:
            content = clip_shot(t, 35.0, 38.5, 0, 40, (280, 165, 380), (280, 175, 560))
            ember_d = 0.8
            flash = max(0, 1 - (t - 35.0) / 0.2) * 0.8
        elif 39.3 <= t < 41.0:
            content = clip_shot(t, 39.3, 41.0, 40, 78, (280, 215, 560), (280, 225, 520))
            ember_d = 0.8
        elif 41.8 <= t < 43.5:
            content = clip_shot(t, 41.8, 43.5, 78, 112, (280, 245, 560), (285, 250, 500))
            ember_d = 0.8
        elif 44.3 <= t < 46.3:
            content = clip_shot(t, 44.3, 46.0, 112, nclip - 1, (300, 255, 520), (310, 260, 380))
            flash = max(0, (t - 45.6) / 0.4) * 1.0 + max(0, 1 - (t - 44.3) / 0.15) * 0.5
            ember_d = 1.0
        elif 50.0 <= t < 55.3:
            ember_d = 1.0

        if content is not None:
            if fade < 1:
                content = content * fade
            frame[BAR:BAR + CH] = content

        # ---------------- text cards ----------------
        for s, e, txt, lay in cards:
            if s <= t < e:
                x = (t - s) / (e - s)
                a = ease((t - s) / 0.25) * ease((e - t) / 0.25)
                sc = 1.0 + 0.06 * x
                if lay.height > 300:  # big fire cards: slam in
                    sc = 1.25 - 0.25 * ease((t - s) / 0.12) + 0.04 * x
                    a = 1.0 if t - s > 0.05 else 0.5
                cy = H / 2 if txt not in OVERLAY_CARDS else BAR + CH * 0.8
                frame = paste_layer(frame, lay, a, sc, cy)

        # ---------------- title ----------------
        if 50.0 <= t < 55.3:
            x = t - 50.0
            sc = 1.6 - 0.6 * ease(x / 0.18) + 0.05 * (x / 5.3)
            a = ease((55.3 - t) / 0.5)
            frame = paste_layer(frame, title, a, sc, H / 2 - 20)
            if x > 1.2:
                frame = paste_layer(frame, subtitle, a * ease((x - 1.2) / 0.8), 1.0, H / 2 + 150)
            flash = max(flash, max(0, 1 - x / 0.3) * 0.9)

        # ---------------- fx ----------------
        if ember_d > 0:
            frame += embers.layer(t, ember_d) * 0.9
        if flash > 0:
            frame = lerp(frame, np.array([255, 245, 225], np.float32), min(flash, 1.0))
        elif flash < 0:
            frame = frame * (1 + flash * 0.3) + np.array([120, 10, 0], np.float32) * (-flash) * 0.3
        frame *= vign
        g = grains[fi % len(grains)]
        frame += np.repeat(np.repeat(g, 2, 0), 2, 1)
        frame[:BAR] = 0
        frame[BAR + CH:] = 0
        ff.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        if fi % 120 == 0:
            print(f"  frame {fi}/{NFRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()


# --------------------------------------------------------------------------
# Sound
# --------------------------------------------------------------------------
N = int(SR * DUR)
TT = np.arange(N) / SR


def env_exp(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def add(buf, t0, x, gain=1.0):
    i0 = int(t0 * SR)
    if i0 >= len(buf):
        return
    x = x[: len(buf) - i0]
    if buf.ndim == 2 and x.ndim == 1:
        x = np.stack([x, x], 1)
    buf[i0: i0 + len(x)] += x * gain


def lowpass(x, fc, order=4):
    sos = signal.butter(order, fc, "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def highpass(x, fc, order=2):
    sos = signal.butter(order, fc, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def saw(f, n, detune=0.0, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f * (1 + detune) + phase) % 1.0) - 1


def heartbeat(intensity=1.0, gap=0.24):
    def thump(f0, f1, dur, amp):
        n = int(dur * SR)
        t = np.arange(n) / SR
        f = f1 + (f0 - f1) * np.exp(-t / 0.03)
        ph = 2 * np.pi * np.cumsum(f) / SR
        e = (1 - np.exp(-t / 0.004)) * np.exp(-t / 0.09)
        x = np.sin(ph) * e
        click = lowpass(np.random.default_rng(1).normal(0, 1, n) * np.exp(-t / 0.006), 900)
        return np.tanh((x + click * 0.25) * 2.2 * intensity) * amp
    lub = thump(95, 42, 0.45, 1.0)
    dub = thump(110, 52, 0.4, 0.7)
    out = np.zeros(int((gap + 0.45) * SR))
    out[: len(lub)] += lub
    out[int(gap * SR): int(gap * SR) + len(dub)] += dub
    return out


def impact(size=1.0, seed=0):
    n = int(3.5 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    f = 30 + 90 * np.exp(-t / 0.08)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.7 * size))
    noise = lowpass(rng.normal(0, 1, n), 2500) * np.exp(-t / 0.12)
    crack = highpass(rng.normal(0, 1, n), 2000) * np.exp(-t / 0.02) * 0.5
    return np.tanh((sub * 1.4 + noise * 0.6 + crack) * 1.5) * size


def braam(dur=4.0, root=36.71, size=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for mult, g in ((1, 1.0), (1.5, 0.7), (2, 0.6), (2.378, 0.45), (4, 0.25)):
        for d in (-0.004, 0.0, 0.005):
            x += saw(root * mult, n, d, phase=np.random.rand()) * g
    x = np.tanh(x * 0.6)
    a = lowpass(x, 300)
    b = lowpass(x, 1800)
    sweep = np.exp(-t / 0.5)
    x = a * (1 - sweep) + b * sweep
    e = (1 - np.exp(-t / 0.02)) * np.exp(-t / (dur * 0.45))
    return x * e * size * 0.5


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(9)
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    seg = n // 24
    for i in range(24):
        fc = 200 * (40 ** (i / 23))
        out[i * seg:(i + 1) * seg] = signal.sosfilt(
            signal.butter(2, [fc * 0.7, min(fc * 1.4, 20000)], "band", fs=SR, output="sos"),
            noise[i * seg:(i + 1) * seg])
    f = 80 * (16 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    return (out * 0.8 + tone) * (t / dur) ** 2.2


def whoosh(dur=0.7, seed=4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = signal.sosfilt(signal.butter(2, [300, 4000], "band", fs=SR, output="sos"),
                       np.random.default_rng(seed).normal(0, 1, n))
    return x * np.sin(np.pi * t / dur) ** 2 * 0.5


def tom(f=110, dur=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    fr = f * 0.55 + f * 0.45 * np.exp(-t / 0.05)
    return np.tanh(np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.18) * 2)


def string_note(f, dur, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = saw(f, n, -0.003) + saw(f, n, 0.004) + 0.5 * saw(f * 2, n, 0.001)
    x = lowpass(x, 900 + 2600 * bright, 2)
    return x * (1 - np.exp(-t / 0.005)) * np.exp(-t / 0.09) * 0.25


def piano(f, dur=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) * (0.6 ** k) * np.exp(-t * (0.8 + k * 0.6)) for k in range(1, 7))
    return x * (1 - np.exp(-t / 0.002)) * 0.5


def reverb_ir(dur=2.8, seed=11):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t / (dur / 6.9))[:, None]
    ir = lowpass(ir, 6000)
    ir[:int(0.012 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0))


def beat_times(t0, t1, bpm0, bpm1):
    out, t = [], t0
    while t < t1:
        out.append(t)
        bpm = lerp(bpm0, bpm1, (t - t0) / (t1 - t0))
        t += 60.0 / bpm
    return out


def build_music():
    dry = np.zeros((N, 2))
    send = np.zeros((N, 2))  # reverb send

    # --- heartbeat (the pulse of the whole trailer) ---
    for bt in beat_times(0.3, 13.0, 56, 60):
        add(dry, bt, heartbeat(0.9, 0.26), 0.9)
    for bt in beat_times(13.0, 20.5, 60, 88):
        add(dry, bt, heartbeat(1.0, 0.23), 1.0)
    for bt in beat_times(20.5, 29.25, 92, 158):
        add(dry, bt, heartbeat(1.15, max(0.13, 0.22 - (bt - 20.5) * 0.01)), 1.05)
    for bt in (48.6,):
        add(dry, bt, heartbeat(1.3, 0.26), 1.3)
        add(send, bt, heartbeat(1.3, 0.26), 0.5)
    for bt in beat_times(53.5, 59.0, 62, 48):
        add(dry, bt, heartbeat(0.9, 0.27), lerp(0.8, 0.35, (bt - 53.5) / 5.5))

    # --- low drone + earth rumble ---
    def drone(t0, t1, root, amp, cutoff=180):
        n = int((t1 - t0) * SR)
        t = np.arange(n) / SR
        x = saw(root, n, -0.003) + saw(root, n, 0.004) + 0.6 * saw(root * 1.5, n, 0.002)
        x = lowpass(x, cutoff)
        e = np.minimum(1, t / 1.5) * np.minimum(1, (n / SR - t) / 0.3)
        return x * e * amp
    add(dry, 0.0, drone(0.0, 13.0, 36.71, 0.10))
    add(dry, 13.0, drone(13.0, 29.3, 36.71, 0.16, 260) * np.linspace(0.6, 1.4, int(16.3 * SR)))
    add(dry, 50.0, drone(50.0, 59.5, 36.71, 0.18, 220))
    rng = np.random.default_rng(5)
    n = int(16.3 * SR)
    rumble = lowpass(np.cumsum(rng.normal(0, 1, n)) * 0.02, 120)
    rumble = rumble / np.abs(rumble).max() * np.linspace(0, 1, n) ** 1.5
    add(dry, 13.0, rumble, 0.5)

    # --- risers / whooshes / impacts ---
    add(dry, 25.9, riser(3.35), 0.55)
    add(send, 25.9, riser(3.35), 0.25)
    for t0 in (0.5, 8.9, 9.8, 10.7, 11.6, 55.3):
        add(dry, t0, whoosh(0.6, int(t0 * 10)), 0.45)
    for t0, s in ((8.0, 0.5), (13.0, 0.5), (20.55, 0.9), (23.65, 0.9), (26.45, 0.9),
                  (38.5, 0.9), (41.0, 0.9), (43.5, 0.9)):
        add(dry, t0, impact(s, int(t0)), 0.7)
        add(send, t0, impact(s, int(t0)), 0.35)
    for t0 in (30.0, 46.0, 50.0):  # the big ones
        add(dry, t0, impact(1.3, int(t0)), 1.0)
        add(send, t0, impact(1.3, int(t0)), 0.6)

    # --- braams ---
    add(dry, 30.0, braam(5.0, 36.71, 1.0))
    add(send, 30.0, braam(5.0, 36.71, 1.0), 0.4)
    add(dry, 50.0, braam(6.5, 36.71, 1.3))
    add(send, 50.0, braam(6.5, 36.71, 1.3), 0.6)
    add(dry, 38.5, braam(2.4, 43.65, 0.8))
    add(dry, 43.5, braam(2.4, 48.99, 0.8))

    # --- action section: 140 bpm string ostinato + toms + heart kick ---
    bpm = 140
    s16 = 60 / bpm / 4
    d3 = 146.83
    pattern = [1, 1, 1.189, 1, 1.498, 1, 1.335, 1.189] * 2   # D minor riff
    t, i = 35.0, 0
    while t < 46.0:
        k = (t - 35.0) / 11.0
        f = d3 * pattern[i % len(pattern)] * (2 if (i // 64) % 2 else 1)
        add(dry, t, string_note(f, 0.18, 0.3 + 0.7 * k), 0.8 + 0.4 * k)
        if i % 4 == 0:
            add(dry, t, heartbeat(1.2, 0.12)[: int(0.3 * SR)], 0.9)
        if i % 8 == 4:
            add(dry, t, tom(90), 0.5)
            add(send, t, tom(90), 0.2)
        if i % 16 in (14, 15) and k > 0.4:
            add(dry, t, tom(140, 0.3), 0.45)
        t += s16
        i += 1
    # low pedal under the riff
    add(dry, 35.0, drone(35.0, 46.0, 36.71, 0.18, 300))
    add(dry, 44.0, riser(2.0), 0.5)
    # 30-35: half-time pulse under the reveal
    for bt in beat_times(30.6, 35.0, 70, 70):
        add(dry, bt, heartbeat(1.3, 0.2), 1.0)
        add(dry, bt, tom(70, 0.8), 0.4)

    # --- final piano note on the tagline ---
    add(dry, 55.5, piano(146.83, 4.5), 0.35)
    add(dry, 55.5, piano(220.0, 4.5), 0.2)
    add(send, 55.5, piano(146.83, 4.5), 0.4)

    wet = signal.fftconvolve(send, reverb_ir(), axes=0)[:N]
    mix = dry + wet * 0.8
    # hard silence before the drop and before the title
    for a, b in ((29.3, 30.0), (49.55, 50.0)):
        i0, i1 = int(a * SR), int(b * SR)
        fade = int(0.03 * SR)
        mix[i0:i0 + fade] *= np.linspace(1, 0, fade)[:, None]
        mix[i0 + fade:i1] = 0
    return mix


def build_vo(tmp):
    """Guide voice: espeak-ng phonemes -> mbrola it3 (male) -> deep, compressed trailer voice."""
    vo = np.zeros((N, 2))
    for k, (t0, text) in enumerate(VO_LINES):
        pho = os.path.join(tmp, f"l{k}.pho")
        raw = os.path.join(tmp, f"l{k}.wav")
        proc = os.path.join(tmp, f"l{k}p.wav")
        slow = 100 if t0 > 46 else 112
        p = subprocess.run(["espeak-ng", "-v", "mb-it3", "-s", str(slow), "-p", "25", "-q",
                            "--pho", text], capture_output=True, text=True, check=True)
        # it3 lacks the stressed-i diphones espeak asks for; map them to plain i
        fixed = "\n".join(("i" + l[2:]) if l.startswith("i/\t") else l for l in p.stdout.splitlines())
        with open(pho, "w") as f:
            f.write(fixed + "\n")
        subprocess.run(["mbrola", "-e", "/usr/share/mbrola/it3/it3", pho, raw], check=True)
        whisper = text == "Vesuvius."
        af = ("aresample=48000,rubberband=pitch=0.84:formant=shifted:tempo=0.94,"
              "highpass=f=55,equalizer=f=110:t=q:w=1:g=6,equalizer=f=2800:t=q:w=1.5:g=3,"
              "acompressor=threshold=-22dB:ratio=5:attack=5:release=120:makeup=6,"
              "aecho=0.8:0.5:45|90:0.18|0.10")
        if whisper:
            af = af.replace("pitch=0.84", "pitch=0.74")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ac", "1",
                        "-ar", str(SR), proc], check=True)
        from scipy.io import wavfile
        sr, x = wavfile.read(proc)
        x = x.astype(np.float64) / (32768.0 if x.dtype == np.int16 else 1.0)
        x = x / (np.abs(x).max() + 1e-9) * 0.9
        print(f"  VO {t0:5.1f}s  {len(x) / SR:4.2f}s  {text}")
        add(vo, t0, x)
    return vo


def write_wav(path, x):
    from scipy.io import wavfile
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def master(music, vo=None):
    m = music / (np.abs(music).max() + 1e-9) * 0.8
    if vo is not None:
        env = np.abs(vo).max(1)
        env = signal.sosfilt(signal.butter(1, 4, fs=SR, output="sos"), env)
        env = np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
        m = m * (1 - 0.5 * env)[:, None] + vo * 0.85
    m = np.tanh(m * 1.4) / np.tanh(1.4)
    return m / (np.abs(m).max() + 1e-9) * 0.95


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--office1", required=True, help="profile photo in the office")
    ap.add_argument("--office2", required=True, help="selfie in the office")
    ap.add_argument("--headshot", required=True)
    ap.add_argument("--poster", required=True, help="Antonello/Vesuvius split poster")
    ap.add_argument("--clip", required=True, help="Vesuvius action clip (560x560)")
    ap.add_argument("--out", required=True, help="output directory")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        print("audio...")
        music = build_music()
        vo = build_vo(tmp)
        write_wav(os.path.join(args.out, "audio_full.wav"), master(music, vo))
        write_wav(os.path.join(args.out, "audio_noVO.wav"), master(music))
        write_wav(os.path.join(args.out, "vo_guide.wav"), vo / (np.abs(vo).max() + 1e-9) * 0.9)
        print("video...")
        silent = os.path.join(tmp, "picture.mp4")
        render_video(args, tmp, silent)
        for name, wav in (("vesuvius_trailer.mp4", "audio_full.wav"),
                          ("vesuvius_trailer_noVO.mp4", "audio_noVO.wav")):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i",
                            os.path.join(args.out, wav), "-c:v", "copy", "-c:a", "aac",
                            "-b:a", "256k", "-shortest", "-movflags", "+faststart",
                            os.path.join(args.out, name)], check=True)
    print("done")


if __name__ == "__main__":
    main()
