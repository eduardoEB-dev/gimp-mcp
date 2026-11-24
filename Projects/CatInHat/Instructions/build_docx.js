// Builds "Cat in the Hat Hot Air Balloon - Assembly Instructions.docx" from the annotated renders.
// usage: node build_docx.js <img_dir> <cover.png|jpg> <out.docx> [png|jpg]   (needs the `docx` npm package on NODE_PATH)
const fs = require("fs"), path = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, LevelFormat, PageBreak, Footer, PageNumber, TableLayoutType } = require("docx");

const [IMG, COVER, OUT, IMGEXT = "png"] = process.argv.slice(2);
const ext = (f) => (f.endsWith(".jpg") ? "jpg" : "png");
const src = (f) => path.join(IMG, f.replace(/\.png$/, "." + IMGEXT));  // jpg = small file (Etsy 20 MB limit)
const RED = "C12E1F", INK = "1F2933", MUTED = "5B6670", GOLD = "B8892E", BLUE = "1C7ED6";
const FULL = 9360; // content width (DXA), Letter with 1.0" side margins... see page margins below (0.9")

const t = (text, o = {}) => new TextRun({ text, ...o });
const p = (runs, o = {}) => new Paragraph({ children: [].concat(runs).map(r => typeof r === "string" ? t(r) : r), spacing: { after: 100 }, ...o });
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(text)], pageBreakBefore: true });
const h2 = (text, o = {}) => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [t(text)], ...o });
const img = (file, inches, caption) => {
  const px = Math.round(inches * 96);
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: caption ? 40 : 160 },
    children: [new ImageRun({ type: ext(src(file)), data: fs.readFileSync(src(file)), transformation: { width: px, height: px } })] })];
  if (caption) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [t(caption, { italics: true, color: MUTED, size: 19 })] }));
  return out;
};
let listN = 0;
const steps = (items) => { const ref = "steps" + (listN++);
  NUMS.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 400, hanging: 300 } }, run: { bold: true, color: RED } } }] });
  return items.map(it => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 90 },
    children: [].concat(it).map(r => typeof r === "string" ? t(r) : r) })); };
const bullets = (items) => items.map(it => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60 },
  children: [].concat(it).map(r => typeof r === "string" ? t(r) : r) }));
const callout = (title, lines, color = RED, fill = "FDF0EE") => lines.map((l, i) => new Paragraph({
  shading: { type: ShadingType.CLEAR, color: "auto", fill }, border: { left: { style: BorderStyle.SINGLE, size: 24, color, space: 8 } },
  indent: { left: 160, right: 160 }, spacing: { before: i === 0 ? 160 : 0, after: i === lines.length - 1 ? 200 : 0, line: 300 },
  children: i === 0 ? [t(title + "  ", { bold: true, color }), ...[].concat(l).map(r => typeof r === "string" ? t(r) : r)]
                    : [].concat(l).map(r => typeof r === "string" ? t(r) : r) }));
const B = (s) => t(s, { bold: true });

const cellB = { style: BorderStyle.SINGLE, size: 4, color: "C9CED4" };
const table = (head, rows, widths) => {
  const total = widths.reduce((a, b) => a + b, 0);
  const mk = (cells, hdr, shade) => new TableRow({ tableHeader: hdr, cantSplit: true, children: cells.map((c, i) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders: { top: cellB, bottom: cellB, left: cellB, right: cellB },
    shading: hdr ? { type: ShadingType.CLEAR, color: "auto", fill: RED } : shade ? { type: ShadingType.CLEAR, color: "auto", fill: "F4F5F7" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ keepNext: true, children: [t(String(c), hdr ? { bold: true, color: "FFFFFF", size: 19 } : { size: 19 })] })] })) });
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    rows: [mk(head, true), ...rows.map((r, i) => mk(r, false, i % 2))] });
};
const gap = () => new Paragraph({ spacing: { after: 120 }, children: [] });
const NUMS = [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
  style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] }];

// side-by-side images (option A / B)
const pair = (a, ca, b, cb, c1 = BLUE, c2 = MUTED) => { const W = FULL / 2, px = Math.round(3.05 * 96);
  const cell = (f, cap, color) => new TableCell({ width: { size: W, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: ext(src(f)), data: fs.readFileSync(src(f)), transformation: { width: px, height: px } })] }),
               new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 120 }, children: [t(cap, { bold: true, color, size: 20 })] })] });
  return new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [W, W], layout: TableLayoutType.FIXED, rows: [new TableRow({ children: [cell(a, ca, c1), cell(b, cb, c2)] })] }); };

const body = [
  // ---------- cover ----------
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 60 }, children: [t("CAT IN THE HAT", { bold: true, size: 56, color: RED, characterSpacing: 40 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [t("Hot Air Balloon", { size: 40, color: INK })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [t("Assembly Instructions", { size: 26, color: MUTED })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: ext(COVER), data: fs.readFileSync(COVER), transformation: { width: 360, height: Math.round(360 * 4 / 3) } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 }, children: [t("TryCatch Designs  ·  From Code to 3D Models", { color: MUTED, size: 20 })] }),

  // ---------- overview ----------
  h1("Before You Start"),
  p("A striped-hat hot air balloon with the red flying couch hanging below it, held up by three clouds behind it. Every part prints separately and is glued together. The clouds carry all the weight. The strings are only for looks."),
  ...callout("Left / right", ["in these instructions = as seen from the FRONT of the couch."], BLUE, "EEF5FC"),
  ...callout("Before you glue:", ["Dry fit every joint first. Super glue grabs fast, so make sure each part goes in the right way before any glue goes on."], BLUE, "EEF5FC"),
  h2("What you need"),
  ...bullets([
    "The printed parts (see Printing below)",
    ["Gold PLA filament, 1.75 mm (the same gold used for the levers and bracket), for the strings and control shafts. ",
     t("Optional: 1/16 in brass rod instead of filament for the control shafts (Hobby Lobby carries it). Brass is NOT required. Gold filament looks great and is what the parts are designed around.", { color: MUTED })],
    "Super glue (CA glue)",
    "Flush cutters or a hobby knife, a ruler with mm markings",
    "Hair dryer or heat gun on low (to bend the steering column)",
  ]),
  h2("Printing"),
  p("Plates in the 3MF (Bambu PLA Basic, 0.4 nozzle unless noted):"),
  table(["Plate", "Part", "Color"], [
    [1, "06 Ring 5 (bottom stripe)", "Red"], [2, "07 Ring 4", "White"], [3, "08 Ring 3", "Red"], [4, "09 Ring 2", "White"],
    [5, "10 Top Cap (prints upside down)", "Red"], [6, "05 Brim (prints upside down)", "White"], [7, "02 Couch", "Red"],
    [8, "11 Bracket", "Gold"], [9, "01 Base Cloud", "White"], [10, "03 Mid Cloud + 04 Top Cloud", "White"],
    [11, "Wheel, levers, pedals, knobs", "Gold + Silver"], [12, "2 dark knobs", "Dark brown"]], [1100, 5560, 2700]),
  ...callout("IMPORTANT:", ["Plates 11 and 12 are labeled “Print with .2 Nozzle”. These parts are tiny. Switch to a 0.2 mm nozzle in Bambu Studio (and on the printer) before slicing those two plates, or they will not print cleanly."]),
  p("All settings (seams, layer heights, supports, brims) are already saved per part in the 3MF. Just slice and print."),

  // ---------- step 1 ----------
  h1("Step 1 – Build the Hat"),
  ...steps([
    [B("Brim + Ring 5: "), "The brim has a groove on top with a solid key block at the back. Ring 5 has a bead on its bottom with a gap in it. Line the gap up with the key block and press Ring 5 into the groove. It is a press fit; glue is optional."],
    [B("Stack the rings in order: "), "Ring 5 → Ring 4 → Ring 3 → Ring 2 → Top Cap. Each lower ring has a lip that slides up inside the ring above it. A key rib at the back fits a notch, so each ring only goes on one way. Ring 4 has a small nub on the outside. It must face the ", B("BACK"), " (it lines up with the top cloud later)."],
    [B("Glue "), "each ring joint once the stack fits. Keep the key ribs lined up so the stripes stay straight."],
  ]),
  gap(),
  pair("s1a_brim_ring5.png", "Ring 5 into the brim (gap over key block)", "s1b_ring_stack.png", "Stacking order; Ring 4 nub faces BACK", MUTED, MUTED),

  // ---------- step 2 ----------
  h1("Step 2 – Couch onto the Base Cloud"),
  ...img("s2_couch.png", 3.1),
  ...steps([
    "Set the couch into the pocket in the base cloud (couch facing the front, away from the tall part of the cloud).",
    "Glue it in place.",
  ]),

  // ---------- step 3 ----------
  h2("Step 3 – Levers on the Front of the Couch"),
  ...img("s3_levers.png", 3.1),
  ...steps([
    "The couch has a thin slit in the crease between the seat cushion and the base, on each side of the front.",
    ["Slide the flat tongue of the ", B("RIGHT"), " lever (16, three sockets) into the right slit, and the ", B("LEFT"), " lever (17, one socket) into the left slit. Glue."],
  ]),

  // ---------- step 4 ----------
  h1("Step 4 – Control Shafts"),
  p("Wheel, shifter, pedals and lever knobs. Cut these from 1.75 mm gold filament (or 1/16 in brass rod). Cut length includes the part that goes into each hole. Cut about 0.5 mm long and trim on the dry fit if unsure. All holes are 2.4 mm, so a little glue fills the gap."),
  ...img("s4a_controls.png", 3.6, "Finished controls."),
  table(["Shaft", "From → To", "Visible", "Cut"], [
    ["Steering column", "base cloud center hole → steering wheel (15), bent 60°", "29.7", "37.3 mm"],
    ["Shifter", "base cloud hole far left → silver ball knob", "23.7", "30.7 mm"],
    ["Pedal, square", "base cloud hole left of column → square pedal", "3.0", "11.6 mm"],
    ["Pedal, round", "base cloud hole right of column → round pedal", "3.7", "12.2 mm"],
    ["Lever R1", "right lever, left (inner) socket → silver ball", "7.9", "12.1 mm"],
    ["Lever R2", "right lever, middle socket → dark ball", "10.9", "15.1 mm"],
    ["Lever R3", "right lever, right (outer) socket → silver cap", "14.0", "18.2 mm"],
    ["Lever L", "left lever socket → dark ball", "6.4", "10.6 mm"]], [1700, 5160, 1100, 1400]),
  gap(),
  h2("How deep each end goes in"),
  ...bullets(["Base cloud holes: 6.0 mm", "Lever sockets: 3.2 mm", "Knobs and cap: 1.0 mm", "Steering wheel hub: 1.6 mm", "Pedals: 2.6 mm"]),
  ...img("s4b_controls_exploded.png", 3.6, "Shafts glue into the holes first, then the knobs, pedals and wheel glue on top."),
  h2("Steering column bend"),
  ...bullets([
    "Mark the column 33.3 mm from the bottom end (6.0 mm goes into the cloud, 27.3 mm stands above it).",
    "Bend it 60° at the mark, toward the couch (toward the driver).",
    "About 4 mm is left past the bend: that end goes into the wheel hub.",
  ]),
  ...callout("Tip:", ["Filament (especially silk) snaps if bent cold. Warm the bend with a hair dryer or heat gun on low first. Brass bends cold."], GOLD, "FBF5E8"),
  h2("Knob colors"),
  ...bullets([
    "Shifter: silver ball (18)",
    "Right lever: R1 silver ball (19), R2 dark ball (21), R3 silver cap (20)",
    "Left lever: dark ball (22)",
    "Pedals: square pad (23) left, round pad (24) right. Each pad has a socket underneath that slips onto its short shaft; the slanted top faces up toward the driver’s feet.",
  ]),
  p("Glue each shaft into its hole, then glue the knob, pad, or wheel on top."),

  // ---------- step 5 ----------
  h1("Step 5 – Stack the Clouds"),
  ...img("s5a_clouds.png", 2.9),
  ...steps([
    "Mid cloud drops straight down onto the round nub on top of the base cloud’s tall back mound. The flat side of the nub only lets it go on one way.",
    "Top cloud drops straight down onto the nub on top of the mid cloud.",
    "Glue both joints.",
  ]),
  ...callout("IMPORTANT – lay it on its back while the glue sets.", [
    "Glue the clouds together with the whole piece lying on its BACK (clouds toward the table) and let the glue cure that way. The couch can already be on.",
    "If you glue the clouds standing up, the stack slowly leans forward once you sit it up. Cured lying down, it stays set slightly toward the back, so when the hat goes on its weight doesn’t push the clouds forward or tip it. The whole thing stays straight.",
  ]),
  ...img("s5b_lay_back.png", 2.7, "Lying on its back while the cloud joints cure."),

  // ---------- step 6 ----------
  h1("Step 6 – Attach the Hat"),
  ...img("s6_hat.png", 4.6),
  ...steps([
    ["Hold the finished hat level and slide it straight ", B("BACK"), " toward the clouds:"],
    "The back edge of the brim slides into the curved groove in the mid cloud, and the nub on Ring 4 drops into the small dimple on the top cloud pad.",
    "Dry fit first, then glue at the brim groove and at the top cloud pad.",
    ["Again, lay it on its ", B("BACK"), " (clouds toward the table) while the glue sets."],
  ]),

  // ---------- step 7 ----------
  h1("Step 7 – Strings (Couch → Bracket → Balloon)"),
  p("The strings are 1.75 mm gold filament, cut by hand and glued into 2.4 mm holes. They are decoration only and do not hold any weight."),
  p([B("Hole depths: "), "couch and bracket 4.5 mm (insert 4.0), brim underside 1.6 mm (insert 1.1)."]),
  h2("Lower strings: couch → bracket (cut 4)"),
  ...img("s7a_lower_strings.png", 3.8),
  table(["String", "From → To", "Visible", "Cut"], [
    ["L1", "left arm roll top → bracket front bar (left)", "46.7", "54.7 mm"],
    ["L2", "left backrest top → bracket back bar (left)", "38.0", "46.0 mm"],
    ["L3", "right arm roll top → bracket front bar (right)", "46.7", "54.7 mm"],
    ["L4", "right backrest top → bracket back bar (right)", "38.0", "46.0 mm"]], [1100, 5760, 1100, 1400]),
  p([t("→ Cut 2 at 54.7 mm (front) and 2 at 46.0 mm (back).", { color: MUTED })], { spacing: { before: 80, after: 160 } }),
  p("Glue the 4 lower strings into the couch, then hang the bracket on them and glue (bracket level, centered over the couch)."),

  h2("Upper strings: bracket → balloon (cut 6)", { pageBreakBefore: true }),
  table(["String", "From → To", "Visible", "Cut"], [
    ["U1", "bracket left bar, front → brim left-front", "45.0", "50.1 mm"],
    ["U2", "bracket left bar, middle → brim left", "45.7", "50.8 mm"],
    ["U3", "bracket left bar, back → brim left-back", "45.0", "50.1 mm"],
    ["U4", "bracket right bar, front → brim right-front", "45.1", "50.2 mm"],
    ["U5", "bracket right bar, middle → brim right", "45.8", "50.9 mm"],
    ["U6", "bracket right bar, back → brim right-back", "45.1", "50.2 mm"]], [1100, 5760, 1100, 1400]),
  p([t("→ Easiest: cut all 6 at 50.9 mm, then trim U1, U3, U4, U6 about 0.8 mm on the dry fit.", { color: MUTED })], { spacing: { before: 80, after: 160 } }),
  p("With the hat already on the clouds, glue the 6 upper strings into the bracket. For the top ends you have two choices:"),
  pair("s7b_upper_tuck.png", "Option A – Easy (recommended)", "s7c_upper_holes.png", "Option B – Optional"),
  ...callout("Option A – Easy:", [
    "No glue at the top. Because the strings are glued firmly into the bracket, they hold their position on their own. Just guide each top end up into the open center of the brim, so it rests against the inside edge of the opening. It still looks great, and you skip the fiddly part of gluing each string into the tiny brim holes.",
  ], BLUE, "EEF5FC"),
  ...callout("Option B – Optional:", [
    "Glue each top end into its small hole under the brim (insert 1.1 mm). It looks the same but is more complex, since you have to line up and glue six strings overhead. Totally optional.",
  ], MUTED, "F4F5F7"),
  p([B("Total gold filament: "), "about 51 cm for strings, plus about 15 cm for the control shafts."]),

  // ---------- finished ----------
  h1("All Done"),
  ...img("s8_final.png", 5.4),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 }, children: [t("Enjoy!", { bold: true, size: 36, color: RED })] }),
];

const doc = new Document({
  creator: "TryCatch Designs", title: "Cat in the Hat Hot Air Balloon - Assembly Instructions",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, color: RED }, paragraph: { spacing: { before: 0, after: 160 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: RED, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 27, bold: true, color: INK }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: NUMS },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [t("Cat in the Hat Hot Air Balloon · TryCatch Designs · ", { size: 16, color: MUTED }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: MUTED })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("WROTE", OUT); });
