"""Synthesizes Flow's retro UI sounds (soft chiptune voice + echo) into assets/*.wav."""
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent / "assets"


def voice(freq, dur, glide_to=None, bright=2.2, decay=9.0):
    """Softened square wave (tanh-saturated sine) with pluck envelope and optional pitch glide."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = np.full(n, freq) if glide_to is None else freq * (glide_to / freq) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    tone = np.tanh(bright * np.sin(phase)) / np.tanh(bright)
    tone += 0.3 * np.sin(2 * phase)                       # a bit of octave sparkle
    env = np.minimum(1, t / 0.004) * np.exp(-t * decay)   # 4ms attack, exponential decay
    return tone * env


def seq(notes, gap):
    """notes: list of (freq, dur, kwargs); each starts `gap` seconds after the previous."""
    total = int(SR * (gap * (len(notes) - 1) + max(d for _, d, _ in notes))) + 1
    out = np.zeros(total)
    for i, (f, d, kw) in enumerate(notes):
        v = voice(f, d, **kw)
        s = int(SR * gap * i)
        out[s:s + len(v)] += v
    return out


def finish(x, vol, echo=0.18, delay=0.075, lp=0.35):
    x = np.concatenate([x, np.zeros(int(SR * 0.35))])
    y = np.copy(x)
    for k in range(1, 4):                                  # slap-back echo, retro console style
        d = int(SR * delay * k)
        y[d:] += x[:-d] * echo ** k
    for i in range(1, len(y)):                             # one-pole low-pass: takes the edge off
        y[i] = y[i - 1] + lp * (y[i] - y[i - 1])
    y = y / np.max(np.abs(y)) * vol
    fade = int(SR * 0.02)
    y[-fade:] *= np.linspace(1, 0, fade)
    return y


def save(name, y):
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    # Start: quick rising two-step blip (D5 -> A5), "power on".
    save("start", finish(seq([(587, 0.09, {}), (880, 0.16, {"decay": 12})], 0.055), 0.42))
    # Finish: sparkly major arpeggio up (G5 B5 D6 G6), last note rings.
    save("done", finish(seq([(784, 0.08, {}), (988, 0.08, {}), (1175, 0.08, {}),
                             (1568, 0.35, {"decay": 7})], 0.045), 0.38, echo=0.25))
    # Cancel: two descending notes with a downward pitch bend, "bwow-bwow".
    save("cancel", finish(seq([(660, 0.11, {"glide_to": 520}),
                               (440, 0.2, {"glide_to": 300, "decay": 8})], 0.09), 0.4, lp=0.25))
    print("ok")
