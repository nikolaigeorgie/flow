"""Floating on-screen dictation indicator with spring animations.

States (from the app):  rec -> busy -> done | cancel  -> hidden
Never takes focus or mouse clicks, so pasting still goes to the app you were typing in.
"""
import math
import time
from collections import deque

import objc
from AppKit import (NSBackingStoreBuffered, NSBezierPath, NSColor, NSEvent, NSFont,
                    NSFontAttributeName, NSForegroundColorAttributeName, NSGraphicsContext,
                    NSMakeRect, NSPanel, NSScreen, NSShadow, NSView)
from Foundation import NSMakePoint, NSMakeSize, NSString

WIN_W, WIN_H = 320, 110           # transparent canvas; the pill animates inside it
PH = 44                           # pill height
WIDTH = {"rec": 216, "busy": 128, "done": PH, "cancel": PH}
BARS = 23
NONACTIVATING_PANEL = 1 << 7
STATUS_LEVEL = 25
BEHAVIOR = (1 << 0) | (1 << 4) | (1 << 6) | (1 << 8)  # all spaces, stationary, no cmd-tab, over full-screen

PINK, ORANGE = (1.0, 0.31, 0.69), (1.0, 0.72, 0.30)
MINT, RED = (0.36, 0.95, 0.70), (1.0, 0.36, 0.48)

levels = deque([0.0] * BARS, maxlen=BARS)  # fed from the audio callback


def push_level(rms):
    levels.append(min(1.0, max(0.0, rms - 0.003) * 14) ** 0.7)


def rgb(c, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(c[0], c[1], c[2], a)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


class Spring:
    def __init__(self, x, k=0.2, damp=0.7):
        self.x, self.v, self.target, self.k, self.damp = x, 0.0, x, k, damp

    def step(self):
        self.v = (self.v + (self.target - self.x) * self.k) * self.damp
        self.x += self.v
        return self.x


class PillView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(PillView, self).initWithFrame_(frame)
        if self is not None:
            self.o = None
        return self

    def drawRect_(self, rect):
        o = self.o
        if o is None:
            return
        now = time.time()
        w, s = max(PH, o.width.x), o.scale.x   # never squash narrower than a circle
        pw, ph = w * s, PH * s
        cx = WIN_W / 2 + o.shake()
        cy = WIN_H / 2 + o.rise
        box = NSMakeRect(cx - pw / 2, cy - ph / 2, pw, ph)
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(box, ph / 2, ph / 2)

        # Body with soft drop shadow
        NSGraphicsContext.saveGraphicsState()
        sh = NSShadow.alloc().init()
        sh.setShadowBlurRadius_(16)
        sh.setShadowOffset_(NSMakeSize(0, -5))
        sh.setShadowColor_(NSColor.colorWithCalibratedWhite_alpha_(0, 0.45))
        sh.set()
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.06, 0.04, 0.10, 0.94).setFill()
        pill.fill()
        NSGraphicsContext.restoreGraphicsState()

        # Neon rim, tinted by state
        rim = {"rec": PINK, "busy": ORANGE, "done": MINT, "cancel": RED,
               "toast": MINT if getattr(o, "toast_on", True) else (0.6, 0.6, 0.65)}.get(o.mode, PINK)
        pill.setLineWidth_(1.2)
        rgb(rim, 0.38).setStroke()
        pill.stroke()

        NSGraphicsContext.saveGraphicsState()
        pill.addClip()
        if o.mode == "rec":
            self.draw_rec(box, now, clamp((w - 120) / 80))
        elif o.mode == "busy":
            self.draw_busy(box, now, clamp((w - 70) / 50))
        elif o.mode == "done":
            self.draw_check(box, now - o.mode_at)
        elif o.mode == "cancel":
            self.draw_x(box, now - o.mode_at)
        elif o.mode == "toast":
            self.draw_toast(box, clamp((w - PH) / max(1, o.toast_w - PH)))
        NSGraphicsContext.restoreGraphicsState()

    def draw_rec(self, box, now, a):
        if a <= 0:
            return
        midy = box.origin.y + box.size.height / 2
        # Recording dot with expanding ring pulse
        dx = box.origin.x + 24
        ring = (now * 1.2) % 1.0
        rr = 5 + ring * 9
        rgb(RED, a * 0.5 * (1 - ring)).setStroke()
        p = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(dx - rr, midy - rr, rr * 2, rr * 2))
        p.setLineWidth_(1.5)
        p.stroke()
        rgb(RED, a).setFill()
        NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(dx - 5, midy - 5, 10, 10)).fill()

        # Mirrored waveform: newest level in the middle, spreading outward
        o = self.o
        hist = list(levels)
        x0, x1 = box.origin.x + 44, box.origin.x + box.size.width - 56
        step = (x1 - x0) / BARS
        mid = BARS // 2
        for i in range(BARS):
            d = abs(i - mid)
            target = hist[-1 - d] * (1 - d / (BARS * 0.9))
            o.bars[i] += (target - o.bars[i]) * 0.35
            idle = 0.04 * (1 + math.sin(now * 5 + i * 0.7))
            h = 3 + max(o.bars[i], idle) * (PH - 16)
            rgb(mix(PINK, ORANGE, i / (BARS - 1)), a * 0.95).setFill()
            bw = step * 0.5
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x0 + i * step + (step - bw) / 2, midy - h / 2, bw, h), bw / 2, bw / 2).fill()

        el = now - o.started
        attrs = {NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(12.5, 0.23),
                 NSForegroundColorAttributeName: NSColor.colorWithCalibratedWhite_alpha_(1, 0.75 * a)}
        NSString.stringWithString_(f"{int(el) // 60}:{int(el) % 60:02d}").drawAtPoint_withAttributes_(
            NSMakePoint(box.origin.x + box.size.width - 46, midy - 8), attrs)

    def draw_busy(self, box, now, a):
        # Retro "scanner" light sweeping back and forth with a fading trail
        if a <= 0:
            return
        midy = box.origin.y + box.size.height / 2
        n, gap = 9, 9.5
        x0 = box.origin.x + box.size.width / 2 - gap * (n - 1) / 2
        head = (math.sin(now * 5.5) * 0.5 + 0.5) * (n - 1)
        for i in range(n):
            g = math.exp(-abs(i - head) * 1.1)
            r = 2 + 1.6 * g
            rgb(mix(PINK, ORANGE, i / (n - 1)), a * (0.18 + 0.82 * g)).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(x0 + i * gap - r, midy - r, r * 2, r * 2)).fill()

    def draw_toast(self, box, a):
        o = self.o
        midy = box.origin.y + box.size.height / 2
        dx = box.origin.x + 24
        (rgb(MINT, a) if o.toast_on else NSColor.colorWithCalibratedWhite_alpha_(0.6, a)).setFill()
        NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(dx - 5, midy - 5, 10, 10)).fill()
        attrs = {NSFontAttributeName: NSFont.systemFontOfSize_weight_(13, 0.3),
                 NSForegroundColorAttributeName: NSColor.colorWithCalibratedWhite_alpha_(1, 0.92 * a)}
        NSString.stringWithString_(o.toast_text).drawAtPoint_withAttributes_(NSMakePoint(dx + 15, midy - 8.5), attrs)

    def draw_check(self, box, t):
        cx, cy = box.origin.x + box.size.width / 2, box.origin.y + box.size.height / 2
        p = clamp((t - 0.06) / 0.22)
        p = 1 - (1 - p) ** 3
        pts = [(-8, 0), (-2.5, -6), (8.5, 6.5)]
        l1 = math.dist(pts[0], pts[1])
        total = l1 + math.dist(pts[1], pts[2])
        path = NSBezierPath.bezierPath()
        path.moveToPoint_(NSMakePoint(cx + pts[0][0], cy + pts[0][1]))
        L = p * total
        if L <= l1:
            f = L / l1
            path.lineToPoint_(NSMakePoint(cx + pts[0][0] + (pts[1][0] - pts[0][0]) * f,
                                          cy + pts[0][1] + (pts[1][1] - pts[0][1]) * f))
        else:
            f = (L - l1) / (total - l1)
            path.lineToPoint_(NSMakePoint(cx + pts[1][0], cy + pts[1][1]))
            path.lineToPoint_(NSMakePoint(cx + pts[1][0] + (pts[2][0] - pts[1][0]) * f,
                                          cy + pts[1][1] + (pts[2][1] - pts[1][1]) * f))
        path.setLineWidth_(3)
        path.setLineCapStyle_(1)
        path.setLineJoinStyle_(1)
        rgb(MINT).setStroke()
        path.stroke()

    def draw_x(self, box, t):
        cx, cy = box.origin.x + box.size.width / 2, box.origin.y + box.size.height / 2
        k = 6.5 * (1 - (1 - clamp(t / 0.18)) ** 3)
        path = NSBezierPath.bezierPath()
        path.moveToPoint_(NSMakePoint(cx - k, cy - k)); path.lineToPoint_(NSMakePoint(cx + k, cy + k))
        path.moveToPoint_(NSMakePoint(cx - k, cy + k)); path.lineToPoint_(NSMakePoint(cx + k, cy - k))
        path.setLineWidth_(3)
        path.setLineCapStyle_(1)
        rgb(RED).setStroke()
        path.stroke()


class Overlay:
    def __init__(self):
        p = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WIN_W, WIN_H), NONACTIVATING_PANEL, NSBackingStoreBuffered, False)
        p.setLevel_(STATUS_LEVEL)
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(False)
        p.setIgnoresMouseEvents_(True)
        p.setCollectionBehavior_(BEHAVIOR)
        p.setHidesOnDeactivate_(False)
        p.setAlphaValue_(0)
        self.view = PillView.alloc().initWithFrame_(NSMakeRect(0, 0, WIN_W, WIN_H))
        self.view.o = self
        p.setContentView_(self.view)
        self.panel = p
        self.mode, self.mode_at, self.started = "idle", 0.0, 0.0
        self.width, self.scale = Spring(PH, 0.16, 0.72), Spring(0.4, 0.22, 0.62)
        self.alpha, self.rise, self.visible = 0.0, 0.0, False
        self.bars = [0.0] * BARS

    def shake(self):
        if self.mode != "cancel":
            return 0.0
        t = time.time() - self.mode_at
        return 7 * math.sin(t * 45) * math.exp(-t * 7)

    def _place(self):
        mouse = NSEvent.mouseLocation()
        screen = next((s for s in NSScreen.screens()
                       if s.frame().origin.x <= mouse.x <= s.frame().origin.x + s.frame().size.width
                       and s.frame().origin.y <= mouse.y <= s.frame().origin.y + s.frame().size.height),
                      NSScreen.mainScreen())
        f = screen.visibleFrame()
        self.panel.setFrameOrigin_(NSMakePoint(f.origin.x + (f.size.width - WIN_W) / 2, f.origin.y + 30))

    def _set_mode(self, mode):
        self.mode, self.mode_at = mode, time.time()
        self.width.target = WIDTH.get(mode, getattr(self, "toast_w", 150))
        if mode == "rec":
            self.started = self.mode_at
            levels.extend([0.0] * BARS)
            self.bars = [0.0] * BARS
        if mode in ("done", "cancel"):
            self.scale.v += 0.12          # little "bump" when the result lands

    def toast(self, text, on):
        """Brief status pill, e.g. 'Flow is on' / 'Flow is off'."""
        self.toast_text, self.toast_on = text, on
        attrs = {NSFontAttributeName: NSFont.systemFontOfSize_weight_(13, 0.3)}
        self.toast_w = NSString.stringWithString_(text).sizeWithAttributes_(attrs).width + 62
        if not self.visible:
            self._show()
        self.scale.target = 1.0
        self._set_mode("toast")

    def _show(self):
        self._place()
        self.width.x, self.width.v = PH, 0.0
        self.scale.x, self.scale.v, self.alpha, self.rise = 0.4, 0.0, 0.0, 0.0
        self.panel.orderFrontRegardless()
        self.visible = True

    def event(self, kind):
        """'done' or 'cancel' - plays the closing animation."""
        if self.visible:
            self._set_mode(kind)

    def tick(self, state):
        """Call ~60x/second from the main thread with the app state ('idle' | 'rec' | 'busy' | ...)."""
        now = time.time()
        # rec always wins; busy only follows rec (so a finished "done" isn't overridden by a stale busy)
        if (state == "rec" and self.mode != "rec") or (state == "busy" and self.mode == "rec"):
            if not self.visible:
                self._show()
            self.scale.target = 1.0
            self._set_mode(state)
        elif state == "idle" and self.mode in ("rec", "busy"):
            self._set_mode("cancel")      # ended without a result (e.g. silence)
        if not self.visible:
            return

        closing = self.mode in ("done", "cancel", "toast")
        hold = {"done": 0.62, "cancel": 0.5, "toast": 1.5}.get(self.mode, 0.5)
        if closing and now - self.mode_at > hold:
            self.alpha += (0 - self.alpha) * 0.22
            self.rise += 0.6 if self.mode == "done" else 0
            self.scale.target = 0.85
        else:
            self.alpha += (1 - self.alpha) * 0.3
        self.width.step()
        self.scale.step()

        if closing and now - self.mode_at > hold and self.alpha < 0.02:
            self.visible, self.mode = False, "idle"
            self.panel.setAlphaValue_(0)
            self.panel.orderOut_(None)
            return
        self.panel.setAlphaValue_(self.alpha)
        self.view.setNeedsDisplay_(True)
