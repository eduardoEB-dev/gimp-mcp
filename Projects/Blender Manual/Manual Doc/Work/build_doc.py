"""Writes manual.json (doc blocks) for the Blender learning manual, builds the .docx with the Manual Creation builder, runs the Word check.
usage: python -I build_doc.py"""
import json, os, subprocess

OUT = r"G:\gimp-mcp\Projects\Blender Manual\Manual Doc"
MC = r"G:\gimp-mcp\Projects\Workflow\Manual Creation"
JPG = os.path.join(OUT, "Renders", "jpg")
NAME = "Blender Modeling Field Guide"
B = []
h1 = lambda s, **k: B.append({"h1": s, **k})
h2 = lambda s, **k: B.append({"h2": s, **k})
p = lambda s: B.append({"p": s})
img = lambda n, w=6.3, cap=None: B.append({"img": n, "width": w, **({"caption": cap} if cap else {})})
steps = lambda *a: B.append({"steps": list(a)})
bul = lambda *a: B.append({"bullets": list(a)})
tip = lambda title, *lines, style="tip": B.append({"callout": {"title": title, "lines": list(lines), "style": style}})
table = lambda head, rows, widths: B.append({"table": {"head": head, "rows": rows, "widths": widths}})

def term(name, what, use=None, fig=None, w=6.3, how=None, prompt=None, pb=False):
    h2(name, **({"page_break": True} if pb else {}))
    p(what)
    if use: p(f"**Use when:** {use}")
    if fig: img(fig, w)
    if how: B.append({"bullets": [f"**Try it:** {how[0]}"] + list(how[1:])})
    if prompt: B.append({"note": f"Say it in a prompt: “{prompt}”"})

KEYS = [6000 * 0 + 2300, 7060]  # key | what it does

# ------------------------------------------------------------------ intro
h1("How to Use This Guide")
p("This guide turns the Blender cheat sheet into pictures. Every picture is a real Blender render of the operation it describes, "
  "usually as numbered panels: **1** is the starting point, **2** (and **3**) show what the tool does.")
bul("**Part 1 – Getting Around:** mouse, numpad and keyboard shortcuts. Learn these first, everything else is faster with them.",
    "**Part 2 – Shaping:** bevels, insets, extrudes, lofts and other ways to build form.",
    "**Part 3 – Cutting & Separating:** booleans, bisect, seams, knife project.",
    "**Part 4 – Cleaning AI Meshes:** decimate, remesh, weld, normals, shading.",
    "**Part 5 – Topology, Modifiers & Symmetry:** what good geometry looks like and the modifiers you'll use most.",
    "**Part 6 – Printing & Prompting:** alignment features, multi-color printing terms, prompt phrases.",
    "**Quick Reference** at the end: every term on one or two pages.")
tip("HOW TO PRACTICE:", "Open Blender next to this guide. For each term, do the **Try it** line on the default cube (or Add → Mesh → Monkey). "
    "Ctrl Z undoes anything. F9 reopens the options of the last thing you did, so you can tweak it after the fact.")
tip("TWO MODES:", "**Object Mode** moves whole objects. **Edit Mode** (Tab) edits the vertices, edges and faces inside one. "
    "Most tools in Parts 2–3 live in Edit Mode; modifiers (Parts 4–5) are added in Object Mode from the wrench tab of the Properties panel.", style="info")

# ------------------------------------------------------------------ part 1
h1("Part 1 – Getting Around")
h2("Navigation: the mouse", page_break=False)
p("Almost all view movement uses the **middle mouse button** (press the wheel down and drag).")
img("dia_mouse", 5.0)
tip("NO MIDDLE BUTTON?", "Laptop users: Edit → Preferences → Input → **Emulate 3 Button Mouse**, then Alt + left-drag orbits.", style="muted")
h2("Navigation: the numpad")
p("The numpad snaps the view to exact angles. Front, right and top views are **orthographic** (no perspective), which makes lining things up easy.")
img("dia_numpad", 5.0)
img("views", 5.4)
tip("NO NUMPAD?", "Press the backtick key ( ` ) for the View pie menu, or Edit → Preferences → Input → **Emulate Numpad** to use the number row.", style="muted")

h1("Transform")
p("Transform = move, rotate, scale. Press the key, move the mouse, click to confirm (right-click or Esc cancels). "
  "Type a number while transforming for an exact value, e.g. **G X 2 Enter** moves 2 units along X.")
img("transform", 6.3)
table(["Key", "What it does"], [
    ["G", "Grab (move)"], ["R", "Rotate"], ["S", "Scale"],
    ["X, Y or Z after G/R/S", "Lock to that axis (press twice for the object's own axis)"],
    ["Shift + X / Y / Z", "Exclude that axis (e.g. S Shift Z = scale flat, not taller)"],
    ["Shift D", "Duplicate (a separate copy)"], ["Alt D", "Linked duplicate (shares the mesh: edit one, both change)"],
    ["Shift R", "Repeat last action"], ["F9", "Adjust last operation (reopen its options panel)"]], [2600, 6760])

h1("Editing (Edit Mode)")
p("Tab switches between Object Mode and Edit Mode. In Edit Mode you choose what you're selecting with **1, 2, 3** on the number row.")
img("select_modes", 6.3)
table(["Key", "What it does"], [
    ["Tab", "Toggle Edit Mode"], ["Ctrl Tab", "Mode pie menu"], ["1 / 2 / 3", "Vertex / Edge / Face select"],
    ["E", "Extrude"], ["I", "Inset"], ["Ctrl B", "Bevel"], ["Ctrl R", "Loop cut"],
    ["O", "Proportional editing on/off"], ["Alt Z", "X-ray"], ["Shift Z", "Wireframe"],
    ["H / Shift H / Alt H", "Hide selected / hide everything but the selection / unhide all"],
    ["L", "Select linked (everything connected to what's under the mouse)"], ["Shift G", "Select similar"],
    ["Alt click", "Depth selection menu (pick from objects under the mouse)"], ["Ctrl click", "Cycle by depth"]], [2600, 6760])
tip("NOTE:", "Inside Edit Mode, Alt click selects a whole **edge loop** and Ctrl click selects the **shortest path** to the clicked element. The two lines above apply to Object Mode.", style="muted")

h1("Interface & Visibility")
table(["Key", "What it does"], [
    ["F3", "Search any command by name"], ["Q", "Quick Favorites"], ["Z", "Shading pie (solid, wireframe, material, rendered)"],
    ["N", "Toggle the sidebar (exact location, rotation, scale)"], ["T", "Toggle the toolbar"], ["Ctrl Space", "Maximize the area under the mouse"],
    ["Shift drag from an area corner", "Pop an editor into its own window"], ["Right-click an area divider", "Split or join areas"],
    ["Ctrl Page Up / Page Down", "Cycle workspaces"]], [3400, 5960])
h2("Seeing through the model")
img("viewshade", 6.3)
bul("**Alt Z** toggles X-ray. The X-ray strength slider (0 to 1) is in the Viewport Shading options (the dropdown arrow at the top right of the 3D view).",
    "In the **Outliner**: the eye icon hides an object in the viewport, the arrow icon turns off selecting it.",
    "Over the Outliner, **V, S, R** shortcuts work for visibility, selectability and renderability.")
h2("Keyboard map", page_break=True)
p("The most used keys, colored by job. Shift, Ctrl and Alt change what most keys do, so check the tables above.")
img("dia_keyboard", 6.5)

# ------------------------------------------------------------------ part 2
h1("Part 2 – Shaping: Edges & Corners")
term("Bevel and Chamfer", "A **bevel** cuts a sharp edge at an angle so the corner becomes a transition instead of a hard line. "
     "With **1 segment** it's a flat angled cut, which is a **chamfer**. With more segments it becomes rounded.",
     "Geometry looks choppy where two surfaces meet and you want a softer transition (bevel), or a clean flat angled edge (chamfer).",
     "bevel", 6.3, ["Edit Mode, select edges, **Ctrl B**, move the mouse. Roll the wheel to add segments.", "Non-destructive: Bevel modifier (wrench tab → Add Modifier → Generate → Bevel)."],
     "Bevel the sharp edges and fillet the transitions between the panels.", pb=False)
term("Fillet", "A rounded, curved transition between two surfaces. Always smooth and circular, unlike a flat chamfer. "
     "Blender has no separate fillet tool: a bevel with several segments and Profile 0.5 is a fillet.",
     "You want a soft, blended curve between surfaces rather than a hard or flat edge, especially inside corners.",
     "fillet", 5.6, ["Select the inside corner edge, **Ctrl B**, wheel up to 6+ segments."])
term("Inset", "Pushes a selected loop of edges inward, making a border and a smaller face inside it. "
     "Follow it with an extrude down and you have a recess.", "Creating a recessed region for something to sit into (like an emblem or lace detail).",
     "inset", 6.3, ["Edit Mode, face select (3), pick a face, **I**, move the mouse. Press I again for each face separately."],
     "Inset the X outline, planarize it, then boolean a matching recess into the glove.", pb=True)
term("Outset", "The opposite of inset: the new border grows **outward** around the selection instead of inside it.", None,
     "outset", 5.6, ["While insetting, press **O** to switch to outset."])

h1("Pointy, Blended & Extruded Forms")
term("Taper and Apex", "**Taper:** the shape narrows gradually toward a tip, like a cone or pencil point. "
     "**Apex:** the very tip or highest, pointiest point of a shape.",
     "Describing a pointy end that gets thinner along its length (taper), or the sharp end itself, “sharpen to an apex”.",
     "taper", 5.0, ["Select the top face, **E** to extrude, then **S 0** to scale it to a point. Merge the tip: **M → At Center**."],
     "Taper the end to a sharp apex.", pb=False)
term("Loft", "Creates a shape by stretching or blending between two or more cross-section profiles, e.g. turning a circle and a square into one continuous form.",
     "Making organic transitions or morphing one outline into another.", "loft", 5.6,
     ["Make both outlines part of one object with the same number of vertices. Edit Mode, select both loops, **Edge → Bridge Edge Loops**. Raise Number of Cuts in F9 for a smoother blend."])
term("Extrude", "Pushes selected faces or edges outward (or inward) along their normals to add thickness or depth.",
     "Creating raised or sunken details from an existing outline.", "extrude", 5.6,
     ["Select a face, **E**, move the mouse. Type a number for an exact depth. **Alt E** shows more extrude types."], pb=True)
term("Planarize", "Flattens geometry so it lies on a single flat plane.", "You need a cutout piece (or a surface) to sit perfectly flat.",
     "planarize", 5.6, ["Quickest: select the area and **S Z 0** (scale to zero on Z). Or **Mesh → Clean Up → Make Planar Faces**."])

h1("Extrusion Options & Thickness")
p("Different ways to turn a profile into a 3D shape:")
img("extrude_opts", 6.5)
table(["Option", "What it does", "Where in Blender"], [
    ["Taper", "Narrows or widens the profile along the extrusion length", "Scale the extruded end (S), or Simple Deform → Taper"],
    ["Twist", "Rotates the profile as it extrudes (spiral effect)", "Simple Deform modifier → Twist (needs loop cuts along its length)"],
    ["Screw", "Spins the profile around an axis (springs, threads)", "Screw modifier; Screw value = rise per turn"],
    ["Extrude along curve", "Mesh follows a defined path (cables, hoses, curved laces)", "Curve object → Geometry → Bevel depth, or Curve modifier"],
    ["Bevel", "Rounds or chamfers the extrusion edges", "Bevel modifier / Ctrl B"],
    ["Inset", "Pushes selected faces inward rather than outward; borders, recesses", "I in Edit Mode"]], [1900, 3700, 3760])
term("Solidify", "Gives a flat face thickness from both sides; turns a plane into a printable object. A surface with zero thickness can't be sliced for printing.",
     "A shape was modeled as a single sheet (cloth, shell, lace) and needs real walls.", "solidify", 6.0,
     ["Add Modifier → Generate → **Solidify**, set Thickness in mm (with Apply Scale done first)."])

h1("Surface Details & Recesses")
img("recess", 6.5)
bul("**Recess:** a sunken region below the surrounding surface. Use it for an indented area where an emblem or lace will sit.",
    "**Pocket:** like a recess, but usually deeper and more enclosed.",
    "**Relief:** any raised or lowered detail sculpted into a surface.")
p("**Try it:** inset a face then extrude it down (recess) or up (relief), or Boolean a shape into the surface (see Part 3).")
term("Displacement & Bump maps", "Both use a texture to add surface detail. **Displacement** really moves the geometry (needs dense mesh, prints). "
     "**Bump** only changes the shading; the surface is still flat, so it **won't** show up in a 3D print.",
     "Displacement for printable texture; bump for render-only detail.", "displace", 6.3,
     ["Subdivide a plane a lot, Add Modifier → Deform → **Displace**, pick a New texture (Clouds)."])

# ------------------------------------------------------------------ part 3
h1("Part 3 – Cutting & Separating")
term("Boolean", "Uses one mesh to cut, combine, or subtract from another. **Difference** subtracts the cutter (most common for cutting), "
     "**Union** merges them, **Intersect** keeps only the overlap.", "You need a clean cut using another object as the cutting tool.",
     "boolean", 6.5, ["Select the main object, Add Modifier → Generate → **Boolean**, pick the cutter as Object, Solver: Exact. Hide the cutter (H) to see the result."],
     None, pb=False)
tip("BEFORE ANY BOOLEAN:", "Apply scale on both objects (**Ctrl A → Scale**) and make sure both are closed (manifold). Otherwise results distort or fail.", style="warn")
term("Slice and Bisect", "**Slice:** a clean plane cut through the mesh (like a knife through butter); the preferred word over “cut”. "
     "**Bisect:** Blender's straight planar cut with a visible dividing plane; it can **Fill** the hole and **Clear Inner/Outer** to drop one side.",
     "You want a straight or simple planar separation.", "bisect", 6.5,
     ["Edit Mode, **A** to select all, **Mesh → Bisect**, drag a line across the view. In F9 tick Fill and Clear Inner or Outer."], pb=True)
term("Separate", "Detaches selected geometry into its own object. Options: **Selection**, **By Material**, **By Loose Parts**.",
     "You've marked the area and just need to split it off.", "separate", 5.8, ["Edit Mode, select the part (L over it), **P → Selection**."])
term("Mark Seam", "Marks an edge loop so Blender treats it as a boundary (used for UV unwrapping, or to guide cuts).",
     "Defining a clean cut path before separating or unwrapping.", "seam", 5.6,
     ["Edge select (2), Alt click a loop, **Ctrl E → Mark Seam**. Select L with Delimit: Seam to grab one side."],
     "Mark a seam around the circular diameter, slice, and separate by selection.", pb=True)
term("Knife Project", "Projects the outline of one object onto another and cuts along that projected line.",
     "You want to cut a complex shape into a surface using another object as a template.", "knife", 5.8,
     ["Place the template (e.g. a curve or flat shape) in front of the surface. Look straight at it (numpad 7). Select the template, then Shift-select the target, Tab into Edit Mode, **Mesh → Knife Project**."])
term("Loop cut and slide", "Adds a ring of edges around the mesh to control subdivision or bevel placement.", None, "loopcut", 3.6,
     ["**Ctrl R**, hover an edge to preview the ring, click, then slide and click again. Wheel = more cuts."], pb=True)
term("Fill holes & non-manifold", "**Non-manifold** geometry can't exist in reality: holes, internal faces, edges shared by 3+ faces. Slicers often fail on it. "
     "**Fill Holes** closes the gaps.", "A print fails to slice, or Bambu Studio reports errors.", "holes", 5.8,
     ["**Select → Select All by Trait → Non Manifold** shows the problems. Fix: **Mesh → Clean Up → Fill Holes**, or select a boundary and press F."])

# ------------------------------------------------------------------ part 4
h1("Part 4 – Cleaning Up AI-Generated Meshes")
p("AI-generated models are usually far too dense, noisy and full of tiny errors. The tools below, roughly in the order you'd use them:")
steps("**Weld / Merge by Distance** – fuse duplicate vertices.", "**Recalculate normals** – fix black or inside-out patches.",
      "**Decimate** or **Remesh** – bring the face count down / rebuild clean surface.", "**Shade Smooth / Auto Smooth** – make it look clean.",
      "**Fill holes**, check non-manifold, then export.")
term("Decimation", "Reduces the number of polygons while trying to preserve the overall shape. Blender tool: **Decimate modifier**.",
     "The mesh is too heavy to edit or slice, or has more detail than a print can show.", "decimate", 6.0,
     ["Add Modifier → Generate → **Decimate**, lower Ratio until the shape starts to suffer, then back off."], pb=False)
table(["Mode", "What it does"], [["Collapse", "Merges vertices together (most common general-purpose option)"],
                                 ["Un-Subdivide", "Best on meshes that were previously subdivided"],
                                 ["Planar", "Flattens areas that are already roughly flat (excellent for removing wrinkly noise)"]], [2200, 7160])
img("decimate_planar", 6.0)
B.append({"note": "Say it in a prompt: “Decimate the mesh using planar mode to remove the wrinkly noise, then remesh with voxels for clean topology.”"})
term("Remesh", "Throws away the original messy topology and rebuilds the surface with fresh, evenly distributed geometry. Blender tool: **Remesh modifier**.",
     None, "remesh", 6.5, ["Add Modifier → Generate → **Remesh**, Voxel mode, lower Voxel Size for more detail. Quad remesh: Object Data tab (green triangle) → Remesh → **QuadriFlow Remesh**."], pb=True)
table(["Mode", "What it does"], [["Voxel", "Great for organic / noisy shapes; voxelizes then rebuilds cleanly"],
                                 ["Quad", "Tries to produce clean four-sided faces (better for further sculpting/editing)"]], [2200, 7160])
tip("WATCH OUT:", "Remesh may lose fine detail (thin edges, small text). Check close-ups before applying it.", style="warn")
term("Weld / Merge by Distance", "Fuses duplicate vertices that are sitting on top of each other (very common in AI exports). "
     "You can't see them, but they cause seams, shading lines and booleans that fail.",
     "Shading shows odd lines, or a mesh that looks closed reports holes.", None, None,
     ["Edit Mode, A, **M → By Distance**, or add the **Weld** modifier. The status bar reports how many vertices were removed."], pb=True)
term("Normals", "The direction each face is “pointing”. Flipped or inconsistent normals often make faces appear black, dark or invisible.",
     None, "normals", 5.8, ["Overlays dropdown → **Face Orientation** (blue = outside, red = flipped). Fix: Edit Mode, A, **Shift N** (Recalculate Outside)."])
term("Shade Smooth + Auto Smooth", "Makes the surface look smooth without adding geometry. Auto Smooth keeps edges above a set angle sharp.",
     "The model looks dark or faceted when zoomed out, but the actual geometry density is fine.", "shading", 6.5,
     ["Object Mode, right-click → **Shade Smooth** or **Shade Auto Smooth** (in current Blender this adds a “Smooth by Angle” modifier)."])

# ------------------------------------------------------------------ part 5
h1("Part 5 – Mesh Topology")
p("Topology is how the faces are laid out on a surface. Good topology bends, subdivides and bevels cleanly.")
img("topology", 6.5)
bul("**Quads:** four-sided faces; deform and subdivide smoothly.", "**Tris:** triangles; can cause shading artifacts on curved surfaces.",
    "**Ngons:** faces with more than four sides; can cause shading issues. Convert: Ctrl T (triangulate) then **Alt J** (tris to quads).",
    "**Edge flow:** how loops of edges travel across a surface; should follow curvature.",
    "**Retopology:** rebuilding clean topology over an existing mesh (by hand, or QuadriFlow).")
term("Subdivision surface", "Smooths a mesh by adding geometry between faces. Each level multiplies the face count by 4.", None, "subsurf", 6.3,
     ["Object Mode, **Ctrl 1 / 2 / 3** adds a Subdivision Surface modifier at that level."], pb=True)
p("Subdivision rounds everything. To keep an edge crisp, add **support loops** (loop cuts close to the edge) or raise its **crease** (Shift E).")
img("support", 5.8)

h1("Symmetry & Modifiers")
term("Mirror modifier", "Mirrors the mesh across an axis (X, Y or Z), so you only model one half.", None, "mirror", 5.8,
     ["Add Modifier → Generate → **Mirror**. Model on one side of the origin."], pb=False)
bul("**Bisect:** cuts the mesh down the middle, keeping only half.", "**Clipping:** prevents vertices from crossing the mirror plane (keeps the center seam closed).",
    "Can be limited to a **vertex group** for partial symmetry (e.g. individual glove fingers).",
    "**Modifier stack order matters:** keep Mirror above Subdivision and other modifiers so it runs first.")
term("Shrinkwrap", "Snaps one mesh onto another, like conforming a lace onto a glove.", None, "shrinkwrap", 5.8,
     ["On the patch: Add Modifier → Deform → **Shrinkwrap**, Target = the surface. Add Solidify after it for thickness."], pb=True)
term("Array", "Duplicates an object in a pattern (e.g. repeating stitching).", None, "array", 5.8,
     ["Add Modifier → Generate → **Array**, set Count and Relative Offset. Add a Curve modifier after it to bend the row along a path."])
term("Proportional editing", "Moves surrounding vertices with a falloff, for organic deformation.", None, "proportional", 5.8,
     ["Press **O**, then G to move; roll the wheel during the move to change the circle of influence."], pb=True)
term("Origin", "The pivot point of an object: everything rotates, scales and mirrors around it.", None, "origin", 5.8,
     ["Right-click → **Set Origin** (e.g. Origin to Geometry, Origin to 3D Cursor)."])

h2("More modifiers & tools", page_break=True)
table(["Term", "What it is"], [
    ["Data Transfer", "Copies attributes like normals or UVs from one mesh to another"],
    ["Geometry Nodes", "Node-based procedural modeling"],
    ["Snap to grid / vertex", "Precise placement (magnet icon at top of 3D view, or hold Ctrl while moving)"],
    ["Bevel weight & crease", "Mark specific edges to control bevel or subdivision intensity"],
    ["Auto smooth", "Automatically sharpens edges based on face angle"],
    ["Apply scale", "Ctrl A → Scale. Must be done before exporting or booleaning, or results distort"],
    ["Face orientation check", "Color overlay to spot flipped normals (blue good, red flipped)"],
    ["Vertex groups & weight painting", "Tag vertices for selective modifier influence"],
    ["Boolean union / difference / intersect", "Core cutting and combining operations (Part 3)"],
    ["UV unwrapping", "Flattens a 3D surface into a 2D texture map; seams are where the unwrap gets cut"]], [3200, 6160])

# ------------------------------------------------------------------ part 6
h1("Part 6 – Printing & Prompting")
term("Alignment & registration", "**Locating features / datum features:** matching geometry on two surfaces (pin + socket, or biscuit + recess) so parts only mate in one orientation.",
     None, "align", 6.3, None, pb=False)
bul("**Dowel joinery:** a pin on one piece, matching hole on the other.", "**Biscuits:** flat oval shapes slotted into both faces; can be printed separately.")
tip("TIP:", "Make biscuits slightly oversized in thickness for a snug friction fit, or add a tiny taper. Print in a contrasting color to see the joint line.")
h2("Multi-color printing (Bambu Studio / AMS)")
table(["Term", "Meaning"], [
    ["AMS", "Automatic Material System; typically five colors at a time on an X1/P1 series"],
    ["Mid-print filament swap", "Pause the print and swap a color that's no longer used on that layer"],
    ["Color consolidation / palette optimization", "Merging color regions so one filament slot covers multiple areas"],
    ["Reorienting / repositioning a sub-object", "Nudging geometry (e.g. rotating a head) to align color zones"],
    ["Partial pose / isolated transform", "Posing just one part of a mesh"],
    ["Skewing", "Image-side term for the same alignment idea"]], [3600, 5760])
B.append({"note": "Prompt example: “Rotate the head five degrees clockwise so the inner ear pink overlaps the tongue red area, minimizing unique colors per layer.”"})
h2("Prompt phrases that work", page_break=True)
bul("“Bevel the sharp edges and fillet the transitions between the panels.”", "“Taper the end to a sharp apex.”",
    "“Inset the X outline, planarize it, then boolean a matching recess into the glove.”",
    "“Decimate the mesh using planar mode to remove the wrinkly noise, then remesh with voxels for clean topology.”",
    "“Mark a seam around the circular diameter, slice, and separate by selection.”",
    "“Add a locating pin and matching socket to both surfaces so they register in the same position every time.”",
    "“Retopologize this section with even quad topology and consistent edge flow.”", "“Slice along the natural contour of the surface.”",
    "“Cut following the existing edge flow around the head.”", "“Use the curvature of the mesh as the cutting guide rather than a straight plane.”",
    "“Project the cut onto the surface topology.”", "“Cut perpendicular to the attachment surface.”",
    "“Retopologize the cut boundary with even spacing.”", "“Keep quad topology along the seam and avoid ngons.”")

# ------------------------------------------------------------------ quick ref
h1("Quick Reference")
table(["Term", "One line", "Blender"], [
    ["Bevel", "Angled/rounded edge instead of a hard corner", "Ctrl B / Bevel mod"], ["Chamfer", "Flat angled cut (bevel, 1 segment)", "Ctrl B"],
    ["Fillet", "Rounded blend between surfaces", "Ctrl B, many segments"], ["Inset / Outset", "Border inward / outward", "I (O to outset)"],
    ["Taper / Apex", "Narrows to a tip / the tip itself", "E, then S 0"], ["Loft", "Blend between profiles", "Bridge Edge Loops"],
    ["Extrude", "Push faces out to add depth", "E"], ["Planarize", "Flatten onto one plane", "S Z 0"],
    ["Solidify", "Give a sheet thickness", "Solidify mod"], ["Screw / Twist", "Spin profile / rotate along length", "Screw / Simple Deform"],
    ["Boolean", "Cut / merge / overlap with another mesh", "Boolean mod"], ["Slice / Bisect", "Straight plane cut", "Mesh → Bisect"],
    ["Separate", "Split selection into its own object", "P"], ["Mark Seam", "Boundary edge for cuts / UVs", "Ctrl E"],
    ["Knife Project", "Cut a template's outline into a surface", "Mesh → Knife Project"], ["Loop cut", "Ring of new edges", "Ctrl R"],
    ["Non-manifold", "Holes / impossible geometry", "Select All by Trait"], ["Decimate", "Fewer polygons, same shape", "Decimate mod"],
    ["Remesh", "Rebuild clean, even surface", "Remesh mod / QuadriFlow"], ["Weld", "Fuse duplicate verts", "M → By Distance"],
    ["Normals", "Face direction; flipped = dark", "Shift N"], ["Auto Smooth", "Smooth look, crisp edges", "Shade Auto Smooth"],
    ["Subdivision", "Smooth by adding geometry", "Ctrl 1–3"], ["Mirror", "Model half, mirror the rest", "Mirror mod"],
    ["Shrinkwrap", "Snap a mesh onto another", "Shrinkwrap mod"], ["Array", "Repeat in a pattern", "Array mod"],
    ["Proportional", "Neighbors follow with falloff", "O"], ["Origin", "Pivot point", "Set Origin"],
    ["Apply scale", "Do before booleans / export", "Ctrl A → Scale"], ["Displace / Bump", "Real vs fake surface detail", "Displace mod / material"]],
    [2100, 4460, 2800])
B.append({"end": "Happy modeling!"})

cfg = {"name": NAME, "render": {"shots": []},
       "doc": {"accent": "E87D0D", "cover": {"image": os.path.join(JPG, "cover.jpg"), "title": "BLENDER", "subtitle": "Modeling Field Guide",
                                             "kicker": "A picture-by-picture guide to the cheat sheet", "width": 5.6}, "blocks": B}}
man = os.path.join(OUT, "manual.json"); json.dump(cfg, open(man, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
docx = os.path.join(OUT, NAME + ".docx")
subprocess.run(["node", os.path.join(MC, "build_manual.js"), man, JPG, docx], check=True)
subprocess.run([os.path.join(MC, ".venv", "Scripts", "python.exe"), "-I", os.path.join(MC, "check_doc.py"), docx, os.path.join(OUT, "Renders")], check=True)
