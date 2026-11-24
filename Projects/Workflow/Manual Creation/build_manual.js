// Builds the Word manual from a manual.json "doc" section and the JPEGs from run_manual.py (blocks: see Manual_Workflow.md).
// usage: node build_manual.js <manual.json> <jpg_dir> <out.docx>
const fs = require("fs"), path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, LevelFormat, Footer, PageNumber, TableLayoutType } = require("docx");

const [MANUAL, JPG, OUT] = process.argv.slice(2);
const cfg = JSON.parse(fs.readFileSync(MANUAL, "utf8")), D = cfg.doc;
const SIZES = JSON.parse(fs.readFileSync(path.join(JPG, "sizes.json"), "utf8"));
const ACCENT = D.accent || "C12E1F", INK = "1F2933", MUTED = "5B6670", GOLD = "B8892E", BLUE = "1C7ED6";
const BRAND = "TryCatch Designs", TAGLINE = "From Code to 3D Models";
const C = D.cover;
const FULL = 9360; // content width (DXA): Letter with 1" side margins
const CALLOUTS = { warn: [ACCENT, "FDF0EE"], info: [BLUE, "EEF5FC"], tip: [GOLD, "FBF5E8"], muted: [MUTED, "F4F5F7"] };

const t = (text, o = {}) => new TextRun({ text, ...o });
// inline markup in manual.json strings: **bold**, ~~muted~~
const rich = (s) => String(s).split(/(\*\*.+?\*\*|~~.+?~~)/).filter(Boolean).map(x =>
  x.startsWith("**") ? t(x.slice(2, -2), { bold: true }) : x.startsWith("~~") ? t(x.slice(2, -2), { color: MUTED }) : t(x));
const image = (name, wIn) => { const [w, h] = SIZES[name], px = Math.round(wIn * 96);
  return new ImageRun({ type: "jpg", data: fs.readFileSync(path.join(JPG, name + ".jpg")), transformation: { width: px, height: Math.round(px * h / w) } }); };

const NUMS = [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
  style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] }];
let listN = 0;
const steps = (items) => { const ref = "steps" + listN++;
  NUMS.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 400, hanging: 300 } }, run: { bold: true, color: ACCENT } } }] });
  return items.map(it => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 90 }, children: rich(it) })); };
const bullets = (items) => items.map(it => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60 }, children: rich(it) }));
const callout = ({ title, lines, style = "warn" }) => { const [color, fill] = CALLOUTS[style];
  return lines.map((l, i) => new Paragraph({ shading: { type: ShadingType.CLEAR, color: "auto", fill },
    border: { left: { style: BorderStyle.SINGLE, size: 24, color, space: 8 } }, indent: { left: 160, right: 160 },
    spacing: { before: i === 0 ? 160 : 0, after: i === lines.length - 1 ? 200 : 0, line: 300 },
    children: i === 0 ? [t(title + "  ", { bold: true, color }), ...rich(l)] : rich(l) })); };
const img = (b) => { const out = [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: b.caption ? 40 : 160 },
    keepNext: !!b.caption, children: [image(b.img, b.width || 3.6)] })];
  if (b.caption) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [t(b.caption, { italics: true, color: MUTED, size: 19 })] }));
  return out; };

const cellB = { style: BorderStyle.SINGLE, size: 4, color: "C9CED4" };
const table = ({ head, rows, widths }) => {
  const mk = (cells, hdr, shade, keep) => new TableRow({ tableHeader: hdr, cantSplit: true, children: cells.map((c, i) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders: { top: cellB, bottom: cellB, left: cellB, right: cellB },
    shading: hdr ? { type: ShadingType.CLEAR, color: "auto", fill: ACCENT } : shade ? { type: ShadingType.CLEAR, color: "auto", fill: "F4F5F7" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ keepNext: keep, children: [t(String(c), hdr ? { bold: true, color: "FFFFFF", size: 19 } : { size: 19 })] })] })) });
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    rows: [mk(head, true, false, true), ...rows.map((r, i) => mk(r, false, i % 2, i < rows.length - 1))] });  // table stays on one page, doesn't drag the next block with it
};
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const pair = (cells) => { const W = FULL / 2;
  const cell = (c) => new TableCell({ width: { size: W, type: WidthType.DXA }, borders: { top: none, bottom: none, left: none, right: none },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [image(c.shot, 3.05)] }),
               new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 120 }, children: [t(c.caption || "", { bold: true, color: c.accent ? BLUE : MUTED, size: 20 })] })] });
  return new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [W, W], layout: TableLayoutType.FIXED, rows: [new TableRow({ cantSplit: true, children: cells.map(cell) })] }); };

const block = (b) => {
  if (b.h1) return [new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(b.h1)], pageBreakBefore: b.page_break !== false })];
  if (b.h2) return [new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [t(b.h2)], pageBreakBefore: !!b.page_break })];
  if (b.p) return [new Paragraph({ children: rich(b.p), spacing: { after: 100 } })];
  if (b.note) return [new Paragraph({ children: [t(b.note, { color: MUTED })], spacing: { before: 80, after: 160 } })];
  if (b.steps) return steps(b.steps);
  if (b.bullets) return bullets(b.bullets);
  if (b.callout) return callout(b.callout);
  if (b.img) return img(b);
  if (b.pair) return [pair(b.pair)];
  if (b.table) return [table(b.table)];
  if (b.gap) return [new Paragraph({ spacing: { after: 120 }, children: [] })];
  if (b.end) return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 }, children: [t(b.end, { bold: true, size: 36, color: ACCENT })] })];
  throw new Error("unknown block: " + JSON.stringify(b));
};

const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 60 }, children: [t(C.title, { bold: true, size: 56, color: ACCENT, characterSpacing: 40 })] }),
  ...(C.subtitle ? [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [t(C.subtitle, { size: 40, color: INK })] })] : []),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [t(C.kicker || "Assembly Instructions", { size: 26, color: MUTED })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [image("cover", C.width || 3.75)] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 }, children: [t(`${BRAND}  ·  ${TAGLINE}`, { color: MUTED, size: 20 })] }),
  ...D.blocks.flatMap(block),
];

const doc = new Document({
  creator: BRAND, title: `${cfg.name} - ${C.kicker || "Assembly Instructions"}`,
  styles: {
    default: { document: { run: { font: "Calibri", size: 22, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, color: ACCENT }, paragraph: { spacing: { before: 0, after: 160 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 27, bold: true, color: INK }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: NUMS },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [t(`${cfg.name} · ${BRAND} · `, { size: 16, color: MUTED }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: MUTED })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("WROTE", OUT); });
