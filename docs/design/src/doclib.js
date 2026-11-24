// doclib.js - shared builder for the Legacy System v1.0 Word documents (docx-js).
// House look: Cambria headings, Calibri body, charcoal ink, one coral accent. A4 portrait.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, Header, Footer,
  AlignmentType, HeadingLevel, WidthType, ShadingType, BorderStyle, PageNumber, LevelFormat,
  PageBreak, TabStopType, VerticalAlign,
} = require("docx");

const INK = "21201E", MUTED = "6E6A64", CORAL = "D97757", DARK = "1A1A18";
const RULE = "DDD8CF", HEADFILL = "EFECE6", NOTEFILL = "FBF1EC", CODEFILL = "F4F2EE";
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1300;          // A4, ~0.9 in margins
const CONTENT_W = PAGE_W - 2 * MARGIN;                           // 9306 DXA = 6.46 in
const BODY = "Calibri", HEAD = "Cambria", MONO = "Consolas";

// ---------- inline markup: **bold**, `code`, _italic_ ----------
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|_[^_]+_)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: (base.size || 21) - 2, ...base, ...{ font: MONO } }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const p = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), spacing: { after: 120, line: 276 }, ...opts.para });

function bullets(items, ref = "bullets") {
  return items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60, line: 264 } }));
}

let tableNo = 0, figNo = 0;
function caption(kind, text) {
  const n = kind === "Table" ? ++tableNo : ++figNo;
  return new Paragraph({
    spacing: { before: kind === "Table" ? 160 : 80, after: kind === "Table" ? 80 : 200 },
    keepNext: kind === "Table",
    children: [new TextRun({ text: `${kind} ${n}. `, bold: true, color: CORAL, size: 18, font: BODY }),
               new TextRun({ text, italics: true, color: MUTED, size: 18, font: BODY })],
  });
}

const cellBorder = { style: BorderStyle.SINGLE, size: 4, color: RULE };
function table(headers, rows, widthsRel, opts = {}) {
  const total = widthsRel.reduce((a, b) => a + b, 0);
  const widths = widthsRel.map((w) => Math.floor((w / total) * CONTENT_W));
  widths[widths.length - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);
  const size = opts.size || 18;
  const mk = (text, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    borders: { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder },
    shading: head ? { fill: HEADFILL, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    verticalAlign: VerticalAlign.TOP,
    children: String(text).split("\n").map((line) => new Paragraph({ spacing: { after: 20, line: 252 },
      children: runs(line, { size, bold: head ? true : undefined, color: INK }) })),
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => mk(h, i, true)) }),
           ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => mk(c, i, false)) }))],
  });
}

function figure(file, capText, widthIn = 6.3) {
  const buf = fs.readFileSync(file);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);          // PNG IHDR
  const pxW = Math.round(widthIn * 96), pxH = Math.round(pxW * h / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 40 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: pxW, height: pxH },
        altText: { title: capText, description: capText, name: path.basename(file) } })] }),
    caption("Figure", capText),
  ];
}

function note(label, text) {
  return new Paragraph({
    spacing: { before: 80, after: 160, line: 264 },
    shading: { fill: NOTEFILL, type: ShadingType.CLEAR, color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: CORAL, space: 8 } },
    indent: { left: 160, right: 160 },
    children: [new TextRun({ text: label + " ", bold: true, color: CORAL, size: 20 }), ...runs(text, { size: 20 })],
  });
}

function code(text) {
  const lines = text.replace(/\n$/, "").split("\n");
  return lines.map((ln, i) => new Paragraph({
    spacing: { before: i === 0 ? 80 : 0, after: i === lines.length - 1 ? 140 : 0, line: 240 },
    shading: { fill: CODEFILL, type: ShadingType.CLEAR, color: "auto" },
    indent: { left: 120, right: 120 },
    keepLines: true, keepNext: i < lines.length - 1,
    children: [new TextRun({ text: ln.length ? ln : " ", font: MONO, size: 16, color: INK })],
  }));
}

function quote(text, who) {
  return [
    new Paragraph({ spacing: { before: 80, after: 20, line: 276 }, indent: { left: 360, right: 360 },
      border: { left: { style: BorderStyle.SINGLE, size: 12, color: MUTED, space: 10 } },
      children: [new TextRun({ text: "“" + text + "”", italics: true, color: INK, size: 21 })] }),
    new Paragraph({ spacing: { after: 140 }, indent: { left: 360 },
      children: [new TextRun({ text: "— " + who, color: MUTED, size: 18 })] }),
  ];
}

const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: false });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const h3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// ---------- cover + document control + contents ----------
function cover(meta) {
  const kv = (k, v) => new Paragraph({ spacing: { after: 60 }, indent: { left: 2600, hanging: 2600 }, tabStops: [{ type: TabStopType.LEFT, position: 2600 }],
    children: [new TextRun({ text: k, bold: true, color: MUTED, size: 20 }), new TextRun({ text: "\t" + v, color: INK, size: 20 })] });
  return [
    new Paragraph({ spacing: { before: 1800, after: 120 }, children: [new TextRun({ text: meta.client.toUpperCase(), color: CORAL, bold: true, size: 22, characterSpacing: 40 })] }),
    new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: meta.system, font: HEAD, bold: true, size: 56, color: INK })] }),
    new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: meta.title, font: HEAD, bold: true, size: 44, color: CORAL })] }),
    new Paragraph({ spacing: { after: 900 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: CORAL, space: 10 } },
      children: [new TextRun({ text: meta.tagline, color: MUTED, size: 24, italics: true })] }),
    ...meta.fields.map(([k, v]) => kv(k, v)),
    pageBreak(),
  ];
}

function docControl(history) {
  return [
    new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Document control")] }),
    table(["Version", "Date", "Status", "Change"], history, [1, 1.3, 1.4, 5]),
  ];
}

function contents(items) {
  return [
    new Paragraph({ spacing: { before: 280, after: 120 }, children: [new TextRun({ text: "Contents", font: HEAD, bold: true, size: 28, color: INK })] }),
    ...items.map((t) => new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: t, size: 21, color: INK })] })),
    pageBreak(),
  ];
}

// ---------- document assembly ----------
function build(outFile, meta, body) {
  const doc = new Document({
    creator: "Forward Deployed Engineer (FDE)", title: `${meta.system} - ${meta.title}`,
    description: meta.tagline,
    styles: {
      default: { document: { run: { font: BODY, size: 21, color: INK } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: HEAD, size: 32, bold: true, color: INK },
          paragraph: { spacing: { before: 360, after: 140 }, keepNext: true, keepLines: true, outlineLevel: 0,
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: CORAL, space: 4 } } } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: HEAD, size: 26, bold: true, color: INK },
          paragraph: { spacing: { before: 260, after: 100 }, keepNext: true, keepLines: true, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: BODY, size: 22, bold: true, color: CORAL },
          paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, keepLines: true, outlineLevel: 2 } },
      ],
    },
    numbering: { config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "▪", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 400, hanging: 260 } }, run: { color: CORAL } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 400, hanging: 300 } } } }] },
    ] },
    sections: [{
      properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: 1300, bottom: 1200, left: MARGIN, right: MARGIN, header: 600, footer: 600 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: `${meta.client}  |  ${meta.system}  |  ${meta.short}`, color: MUTED, size: 16 })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "Page ", color: MUTED, size: 16 }), new TextRun({ children: [PageNumber.CURRENT], color: MUTED, size: 16 }),
                   new TextRun({ text: " of ", color: MUTED, size: 16 }), new TextRun({ children: [PageNumber.TOTAL_PAGES], color: MUTED, size: 16 })] })] }) },
      children: body,
    }],
  });
  return Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outFile, buf); console.log("wrote", outFile); });
}

module.exports = { p, bullets, table, figure, note, code, quote, h1, h2, h3, pageBreak, cover, docControl, contents, build,
  caption, numbered: (items) => bullets(items, "numbers"), CONTENT_W };
