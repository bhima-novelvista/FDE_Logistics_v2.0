# -*- coding: utf-8 -*-
"""
Premium-deck engine — coral-on-charcoal .pptx builder.
  - 13.333 x 7.5 widescreen (EMU 12192000 x 6858000)
  - Cambria titles, Calibri body
  - Palette: paper FBFAF8, dark 1A1A18, ink 21201E, coral D97757, muted 6E6A64
  - fade-in-on-click entrance per animated shape (raw <p:timing> injected)
  - speaker notes: intro para, then blank / (click) / blank / spoken-line per click
Requires: python-pptx, lxml, Pillow.
"""
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from lxml import etree
from PIL import Image

EMU_W = 12192000
EMU_H = 6858000

PAPER = "FBFAF8"
DARK  = "1A1A18"
INK   = "21201E"
CORAL = "D97757"
MUTED = "6E6A64"
WHITE = "FBFAF8"

LEFT   = 777240
CWIDTH = 10637520

def _rgb(h): return RGBColor.from_string(h)

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _set_spc(run, spc):
    rPr = run._r.get_or_add_rPr()
    rPr.set("spc", str(spc))


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Emu(EMU_W)
        self.prs.slide_height = Emu(EMU_H)
        self.blank = self.prs.slide_layouts[6]

    def _slide(self):
        return self.prs.slides.add_slide(self.blank)

    def _bg(self, slide, color):
        sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Emu(EMU_W), Emu(EMU_H))
        sp.fill.solid(); sp.fill.fore_color.rgb = _rgb(color)
        sp.line.fill.background()
        sp.shadow.inherit = False
        spTree = slide.shapes._spTree
        spTree.remove(sp._element)
        spTree.insert(2, sp._element)
        return sp

    def _textbox(self, slide, x, y, w, h, anchor=None):
        tb = slide.shapes.add_textbox(Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = 0; tf.margin_right = 0
        tf.margin_top = 0; tf.margin_bottom = 0
        if anchor is not None:
            tf.vertical_anchor = anchor
        return tb, tf

    def _run(self, para, text, size, color, bold=False, italic=False,
             font="Calibri", spc=None):
        r = para.add_run(); r.text = text
        f = r.font
        f.size = Pt(size); f.bold = bold; f.italic = italic
        f.name = font; f.color.rgb = _rgb(color)
        if spc is not None:
            _set_spc(r, spc)
        return r

    def _eyebrow(self, slide, text, color=CORAL, y=548640):
        tb, tf = self._textbox(slide, LEFT, y, CWIDTH, 365760)
        self._run(tf.paragraphs[0], text.upper(), 13, color, bold=True, font="Calibri", spc=240)
        return tb

    def _title(self, slide, text, y=932688, size=31, color=INK, w=CWIDTH, font="Cambria"):
        tb, tf = self._textbox(slide, LEFT, y, w, 1188720)
        p = tf.paragraphs[0]; p.line_spacing = 1.02
        first = True
        for line in text.split("\n"):
            if not first:
                p.add_line_break()
            self._run(p, line, size, color, bold=True, font=font)
            first = False
        return tb

    def _add_timing(self, slide, spids):
        if not spids:
            return
        blocks = []
        for i, s in enumerate(spids):
            n = 3 + 5 * i
            blocks.append(
                f'<p:par><p:cTn id="{n}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
                f'<p:par><p:cTn id="{n+1}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'<p:par><p:cTn id="{n+2}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" nodeType="clickEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'<p:set><p:cBhvr><p:cTn id="{n+3}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{s}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
                f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{n+4}" dur="500"/><p:tgtEl><p:spTgt spid="{s}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                f'</p:childTnLst></p:cTn></p:par>'
                f'</p:childTnLst></p:cTn></p:par>'
                f'</p:childTnLst></p:cTn></p:par>'
            )
        bld = "".join(f'<p:bldP spid="{s}" grpId="0" animBg="1"/>' for s in spids)
        xml = (
            f'<p:timing xmlns:p="{P_NS}" xmlns:a="{A_NS}"><p:tnLst><p:par>'
            f'<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            f'{"".join(blocks)}'
            f'</p:childTnLst></p:cTn>'
            f'<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            f'<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
            f'</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
            f'<p:bldLst>{bld}</p:bldLst></p:timing>'
        )
        slide._element.append(etree.fromstring(xml))

    def _notes(self, slide, intro, clicks):
        notes = slide.notes_slide
        tf = notes.notes_text_frame
        tf.text = intro or ""
        for line in clicks:
            tf.add_paragraph()
            tf.add_paragraph().text = "(click)"
            tf.add_paragraph()
            tf.add_paragraph().text = line

    # ---------- slide builders ----------
    def title_slide(self, eyebrow, title_lines, subtitle, img=None, notes_intro="", notes_clicks=None):
        s = self._slide(); self._bg(s, DARK)
        if img:
            self._pic(s, img, 7350000, 1500000, 4000000, 4000000)
        self._eyebrow(s, eyebrow, color=CORAL, y=1500000)
        title_y = 1950000
        # wide box so long lines never wrap; narrower when an image occupies the right
        tw = (7050000 - LEFT) if img else (EMU_W - LEFT - 300000)
        tb, tf = self._textbox(s, LEFT, title_y, tw, 3400000)
        for i, ln in enumerate(title_lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = 1.0
            self._run(p, ln, 54, WHITE if i < len(title_lines)-1 else CORAL, bold=True, font="Cambria")
        # subtitle sits below the actual title height (never overlaps, any line count)
        sub_y = max(4750000, title_y + len(title_lines) * 840000 + 220000)
        tb2, tf2 = self._textbox(s, LEFT, sub_y, tw, 1200000)
        self._run(tf2.paragraphs[0], subtitle, 17, "C9C5BD", font="Calibri")
        self._notes(s, notes_intro, notes_clicks or [])
        return s

    def divider(self, eyebrow, title_lines, img=None, kicker=None, notes_intro="", notes_clicks=None):
        s = self._slide(); self._bg(s, DARK)
        if img:
            self._pic(s, img, 7500000, 1850000, 3850000, 3850000)
        self._eyebrow(s, eyebrow, color=CORAL, y=2350000)
        title_y = 2750000
        tw = (7050000 - LEFT) if img else 8600000
        tb, tf = self._textbox(s, LEFT, title_y, tw, 2600000)
        for i, ln in enumerate(title_lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = 1.0
            self._run(p, ln, 40, WHITE if i < len(title_lines)-1 else CORAL, bold=True, font="Cambria")
        if kicker:
            # kicker sits below the actual title height (never overlaps a 3-line title)
            kick_y = max(4500000, title_y + len(title_lines) * 620000 + 240000)
            tbk, tfk = self._textbox(s, LEFT, kick_y, tw, 900000)
            self._run(tfk.paragraphs[0], kicker, 15, "C9C5BD", font="Calibri")
        self._notes(s, notes_intro, notes_clicks or [])
        return s

    def content(self, eyebrow, title, bullets, img=None, notes_intro="", img_size=3749039,
                bullet_w=None, start_y=2148840, gap=720000, title_size=31):
        s = self._slide(); self._bg(s, PAPER)
        self._eyebrow(s, eyebrow)
        self._title(s, title, size=title_size)
        if img:
            ix = EMU_W - img_size - 600000
            self._pic(s, img, ix, 2240280, img_size, img_size)
            bw = bullet_w or (ix - LEFT - 300000)
        else:
            bw = bullet_w or CWIDTH
        spids = []; clicks = []
        y = start_y
        for b in bullets:
            label, rest = b[0], b[1]
            note = b[2] if len(b) > 2 else ""
            tb, tf = self._textbox(s, LEFT, y, bw, 760000, anchor=MSO_ANCHOR.TOP)
            p = tf.paragraphs[0]; p.line_spacing = 1.06
            self._run(p, "▪   ", 18, CORAL, bold=True)
            if label:
                self._run(p, label, 18, INK, bold=True)
            self._run(p, rest, 18, INK, bold=False)
            spids.append(tb.shape_id); clicks.append(note)
            y += gap
        self._add_timing(s, spids)
        self._notes(s, notes_intro, clicks)
        return s

    def statement(self, lines, eyebrow=None, notes_intro="", notes_clicks=None, anim=True):
        s = self._slide(); self._bg(s, DARK)
        if eyebrow:
            self._eyebrow(s, eyebrow, color=CORAL, y=1150000)
        spids = []
        total = len(lines)
        y = 2550000 - (total-1)*380000//2
        for ln in lines:
            tb, tf = self._textbox(s, 1100000, y, 10000000, 900000, anchor=MSO_ANCHOR.TOP)
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; p.line_spacing = 1.05
            self._run(p, ln, 33, WHITE, bold=True, font="Cambria")
            if anim:
                spids.append(tb.shape_id)
            y += 760000
        if anim:
            self._add_timing(s, spids)
            self._notes(s, notes_intro, notes_clicks or [""]*len(lines))
        else:
            self._notes(s, notes_intro, notes_clicks or [])
        return s

    def compare(self, eyebrow, title, left_head, left_items, right_head, right_items,
                notes_intro="", notes_clicks=None):
        s = self._slide(); self._bg(s, PAPER)
        self._eyebrow(s, eyebrow)
        self._title(s, title, size=29)
        spids = []
        colw = 4950000
        lx = LEFT; rx = LEFT + colw + 500000
        for (cx, head, items, hcolor) in [(lx, left_head, left_items, MUTED), (rx, right_head, right_items, CORAL)]:
            tbh, tfh = self._textbox(s, cx, 2300000, colw, 560000)
            self._run(tfh.paragraphs[0], head, 18, hcolor, bold=True, font="Calibri")
            spids.append(tbh.shape_id)
            tbi, tfi = self._textbox(s, cx, 2900000, colw, 3200000, anchor=MSO_ANCHOR.TOP)
            first = True
            for it in items:
                p = tfi.paragraphs[0] if first else tfi.add_paragraph()
                p.line_spacing = 1.12; p.space_after = Pt(8)
                self._run(p, "–  ", 15, hcolor, bold=True)
                self._run(p, it, 15, INK)
                first = False
            spids.append(tbi.shape_id)
        self._add_timing(s, spids)
        self._notes(s, notes_intro, notes_clicks or [""]*len(spids))
        return s

    def meme(self, img, caption, credit=None, eyebrow=None, notes_intro="", notes_clicks=None):
        s = self._slide(); self._bg(s, DARK)
        if eyebrow:
            self._eyebrow(s, eyebrow, color=CORAL, y=520000)
        if caption:
            tb, tf = self._textbox(s, 900000, 900000, 10400000, 900000)
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            self._run(p, caption, 22, WHITE, bold=True, font="Cambria")
        iw, ih = Image.open(img).size
        maxh = 4300000; maxw = 7000000
        scale = min(maxw/iw, maxh/ih)
        w = int(iw*scale); h = int(ih*scale)
        x = (EMU_W - w)//2; y = 1900000
        self._pic(s, img, x, y, w, h)
        if credit:
            tbc, tfc = self._textbox(s, 900000, 6380000, 10400000, 380000)
            p = tfc.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            self._run(p, credit, 11, "8C887F", italic=True)
        self._notes(s, notes_intro, notes_clicks or [])
        return s

    def diagram(self, eyebrow, title, img, caption=None, notes_intro="", notes_clicks=None):
        s = self._slide(); self._bg(s, PAPER)
        self._eyebrow(s, eyebrow)
        self._title(s, title, size=27)
        iw, ih = Image.open(img).size
        maxw = 11200000; maxh = 3820000; top = 2160000
        scale = min(maxw/iw, maxh/ih)
        w = int(iw*scale); h = int(ih*scale)
        x = (EMU_W - w)//2; y = top + (maxh - h)//2
        self._pic(s, img, x, y, w, h)
        if caption:
            tbc, tfc = self._textbox(s, LEFT, 6250000, CWIDTH, 500000)
            p = tfc.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            self._run(p, caption, 14, MUTED, italic=True)
        self._notes(s, notes_intro, notes_clicks or [])
        return s

    def _pic(self, slide, path, x, y, w, h):
        return slide.shapes.add_picture(path, Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))

    def save(self, path):
        for sl in self.prs.slides:
            _ = sl.notes_slide
        self.prs.save(path)
