# -*- coding: utf-8 -*-
"""
Miro-board-style block-diagram renderer (pure Pillow — no external binaries, no Miro account).
Produces high-res PNGs that look like a Miro whiteboard: a light dot-grid board with rounded
cards (optional coral header bars), sticky notes, labelled group frames, and elbow connector
arrows. Palette is harmonised with the premium-deck house style. Requires: Pillow.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BOARD    = (244, 242, 238)
DOT      = (216, 211, 202)
CARD     = (255, 255, 255)
CARD_BD  = (223, 219, 211)
INK      = (33, 32, 30)
MUTED    = (110, 106, 100)
CORAL    = (217, 119, 87)
CORAL_BD = (198, 101, 71)
STICKY   = (247, 217, 160)
LINE     = (150, 145, 136)
SHADOW   = (60, 55, 48)

SS = 3  # supersample factor for crisp edges


def _hex(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
    return c


def _font(size, bold=False):
    cands = (["calibrib.ttf", "Calibri Bold.ttf", "Arialbd.ttf", "Arial Bold.ttf",
              "arialbd.ttf", "DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
             if bold else
             ["calibri.ttf", "Calibri.ttf", "Arial.ttf", "arial.ttf",
              "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for c in cands:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


class MiroBoard:
    def __init__(self, w=2400, h=1400, board=BOARD, dots=True, frame=True):
        self.w, self.h, self.s = w, h, SS
        self.img = Image.new("RGBA", (w*SS, h*SS), (*_hex(board), 255))
        self.d = ImageDraw.Draw(self.img)
        self.nodes = []
        if dots:
            self._dot_grid()
        if frame:
            self._frame()

    def _S(self, v): return int(round(v*self.s))

    def _dot_grid(self, step=46, r=2):
        step_s, r_s = self._S(step), max(1, self._S(r))
        for y in range(step_s, self.h*self.s, step_s):
            for x in range(step_s, self.w*self.s, step_s):
                self.d.ellipse([x-r_s, y-r_s, x+r_s, y+r_s], fill=(*DOT, 255))

    def _frame(self):
        m = self._S(6)
        self.d.rounded_rectangle([m, m, self.w*self.s-m, self.h*self.s-m],
                                 radius=self._S(22), outline=(*CARD_BD, 255),
                                 width=max(1, self._S(2)))

    def _shadow(self, box, radius, blur=10, alpha=55, dx=0, dy=6):
        x0, y0, x1, y1 = box
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle([x0+self._S(dx), y0+self._S(dy), x1+self._S(dx), y1+self._S(dy)],
                             radius=self._S(radius), fill=(*SHADOW, alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(self._S(blur)))
        self.img.alpha_composite(layer)

    def _wrap(self, text, font, max_w):
        words, lines, cur = text.split(), [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if self.d.textlength(trial, font=font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur); cur = wd
        if cur:
            lines.append(cur)
        return lines

    def _text_block(self, x, y, w, text, font, fill, center=False, leading=1.28):
        lines = self._wrap(text, font, w)
        asc, desc = font.getmetrics()
        lh = int((asc+desc)*leading)
        for i, ln in enumerate(lines):
            tx = x + (w - self.d.textlength(ln, font=font))/2 if center else x
            self.d.text((tx, y+i*lh), ln, font=font, fill=(*fill, 255))
        return y + len(lines)*lh

    def card(self, x, y, w, h, title=None, body=None, accent=False,
             fill=None, sticky=False, title_size=30, body_size=24):
        """Rounded Miro card. accent=True gives a coral header bar with white title.
        Returns a handle usable in connect()."""
        bx = [self._S(x), self._S(y), self._S(x+w), self._S(y+h)]
        rad = 16 if not sticky else 8
        if sticky:
            self._shadow(bx, rad, blur=7, alpha=50, dy=5)
            self.d.rounded_rectangle(bx, radius=self._S(rad), fill=(*_hex(fill or STICKY), 255))
            px, tw = self._S(x)+self._S(18), self._S(w)-self._S(36)
            py = self._S(y)+self._S(16)
            if title:
                py = self._text_block(px, py, tw, title, _font(self._S(body_size), bold=True), INK)
                py += self._S(6)
            if body:
                self._text_block(px, py, tw, body, _font(self._S(body_size-2)), INK)
            self.nodes.append((x, y, w, h))
            return (x, y, w, h)

        self._shadow(bx, rad, blur=9, alpha=48, dy=6)
        self.d.rounded_rectangle(bx, radius=self._S(rad),
                                 fill=(*_hex(fill or CARD), 255),
                                 outline=(*CARD_BD, 255), width=max(1, self._S(1.5)))
        pad = self._S(20)
        cy = self._S(y) + pad
        if accent:
            hh = self._S(min(max(h*0.30, 62), 96))
            self.d.rounded_rectangle([bx[0], bx[1], bx[2], bx[1]+hh], radius=self._S(rad),
                                     corners=(True, True, False, False), fill=(*CORAL, 255))
            tf = _font(self._S(title_size), bold=True)
            asc, desc = tf.getmetrics()
            self.d.text((bx[0]+pad, bx[1]+(hh-(asc+desc))/2), title or "", font=tf,
                        fill=(255, 255, 255, 255))
            cy = bx[1]+hh+self._S(16)
            if body:
                self._text_block(bx[0]+pad, cy, self._S(w)-2*pad, body,
                                 _font(self._S(body_size)), INK)
        else:
            if title:
                tf = _font(self._S(title_size), bold=True)
                self.d.text((bx[0]+pad, cy), title, font=tf, fill=(*INK, 255))
                cy += int((tf.getmetrics()[0]+tf.getmetrics()[1])*1.15)
                self.d.line([bx[0]+pad, cy, bx[0]+pad+self._S(46), cy],
                            fill=(*CORAL, 255), width=max(1, self._S(3)))
                cy += self._S(14)
            if body:
                self._text_block(bx[0]+pad, cy, self._S(w)-2*pad, body,
                                 _font(self._S(body_size)), MUTED)
        self.nodes.append((x, y, w, h))
        return (x, y, w, h)

    def group(self, x, y, w, h, label=None, fill=(236, 234, 228)):
        """Labelled frame drawn BEHIND cards (call before the cards it contains)."""
        bx = [self._S(x), self._S(y), self._S(x+w), self._S(y+h)]
        self.d.rounded_rectangle(bx, radius=self._S(18), fill=(*_hex(fill), 255),
                                 outline=(*CARD_BD, 255), width=max(1, self._S(1.5)))
        if label:
            f = _font(self._S(24), bold=True)
            tw = self.d.textlength(label, font=f)
            chip = [bx[0]+self._S(18), bx[1]-self._S(20), bx[0]+self._S(18)+tw+self._S(28),
                    bx[1]+self._S(24)]
            self.d.rounded_rectangle(chip, radius=self._S(11), fill=(*CORAL, 255))
            asc, desc = f.getmetrics()
            self.d.text((chip[0]+self._S(14), (chip[1]+chip[3])/2-(asc+desc)/2), label,
                        font=f, fill=(255, 255, 255, 255))

    def label(self, x, y, text, size=24, color=MUTED, bold=False):
        self.d.text((self._S(x), self._S(y)), text, font=_font(self._S(size), bold=bold),
                    fill=(*color, 255))

    def connect(self, a, b, label=None, arrow="end", dashed=False, width=3):
        """Elbow connector between two cards, routed on the dominant axis."""
        ax, ay, aw, ah = a; bx, by, bw, bh = b
        acx, acy = ax+aw/2, ay+ah/2
        bcx, bcy = bx+bw/2, by+bh/2
        horiz = abs(bcx-acx) >= abs(bcy-acy)
        if horiz:
            if bcx >= acx:
                p0 = (ax+aw, acy); p3 = (bx, bcy)
            else:
                p0 = (ax, acy); p3 = (bx+bw, bcy)
            mx = (p0[0]+p3[0])/2
            pts = [p0, (mx, p0[1]), (mx, p3[1]), p3]
        else:
            if bcy >= acy:
                p0 = (acx, ay+ah); p3 = (bcx, by)
            else:
                p0 = (acx, ay); p3 = (bcx, by+bh)
            my = (p0[1]+p3[1])/2
            pts = [p0, (p0[0], my), (p3[0], my), p3]
        sp = [(self._S(px), self._S(py)) for px, py in pts]
        wln = max(1, self._S(width))
        if dashed:
            self._dashed_path(sp, wln)
        else:
            self.d.line(sp, fill=(*LINE, 255), width=wln, joint="curve")
        if arrow in ("end", "both"):
            self._arrow(sp[-2], sp[-1], wln)
        if arrow == "both":
            self._arrow(sp[1], sp[0], wln)
        if label:
            lx, ly = (pts[1][0]+pts[2][0])/2, (pts[1][1]+pts[2][1])/2
            f = _font(self._S(21), bold=True)
            tw = self.d.textlength(label, font=f)
            asc, desc = f.getmetrics()
            pad = self._S(9)
            box = [self._S(lx)-tw/2-pad, self._S(ly)-(asc+desc)/2-pad/2,
                   self._S(lx)+tw/2+pad, self._S(ly)+(asc+desc)/2+pad/2]
            self.d.rounded_rectangle(box, radius=self._S(8), fill=(*BOARD, 255),
                                     outline=(*CARD_BD, 255), width=max(1, self._S(1)))
            self.d.text((self._S(lx)-tw/2, self._S(ly)-(asc+desc)/2), label, font=f,
                        fill=(*MUTED, 255))

    def _dashed_path(self, pts, wln, dash=22, gap=14):
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            seg = ((x1-x0)**2+(y1-y0)**2)**0.5
            if seg == 0:
                continue
            ux, uy = (x1-x0)/seg, (y1-y0)/seg
            d = 0
            ds, gs = self._S(dash), self._S(gap)
            while d < seg:
                aa = (x0+ux*d, y0+uy*d)
                bb = (x0+ux*min(d+ds, seg), y0+uy*min(d+ds, seg))
                self.d.line([aa, bb], fill=(*LINE, 255), width=wln)
                d += ds+gs

    def _arrow(self, frm, to, wln, size=16):
        import math
        ang = math.atan2(to[1]-frm[1], to[0]-frm[0])
        L = self._S(size)
        a1 = (to[0]-L*math.cos(ang-math.pi/7), to[1]-L*math.sin(ang-math.pi/7))
        a2 = (to[0]-L*math.cos(ang+math.pi/7), to[1]-L*math.sin(ang+math.pi/7))
        self.d.polygon([to, a1, a2], fill=(*LINE, 255))

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        out = self.img.convert("RGB").resize((self.w, self.h), Image.LANCZOS)
        out.save(path)
        return path
