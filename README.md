# Jaiba Drum — Hex Trays

Blender Python scripts that generate the flat hexagonal sensor plates for the Jaiba electronic hand drum, split into printable left/right halves. Two versions are included: a stable base plate, and a newer version that adds a containment wall around the tray. If the wall version gives you trouble, the base plate is the one to fall back on — it's the simpler, proven calculation everything else builds on.

## What's in this repo

| File | Description |
|---|---|
| `jaiva-hexa-drum-trays-script.py` | **Base plate script.** Generates the flat hex tile plate (left + right halves) with wire holes and connector pin holes. This is the core geometry — start here. |
| `jaiva-hexa-drum-trays-walls-script.py` | **Tray + wall script.** Same base plate, plus a containment wall traced around the true outer boundary of each half (for holding cast silicone sensor cups in place). Newer and less battle-tested than the base script. |
| `flat_hex_plate_LEFT.stl` / `flat_hex_plate_RIGHT.stl` | Exported STLs from the base plate script. |
| `flat_hex_plate-Walls_LEFT.stl` / `flat_hex_plate-Walls_RIGHT.stl` | Exported STLs from the tray + wall script. |
| `jaiba-drum-hexa-trays-1.blend` | Blender project file for the base plate. |
| `jaiba-drum-hexa-tray-walls-2.blend` | Blender project file for the tray + wall version. |

## Geometry overview

- **16 hex tiles total**, split into a 7-tile left half and a 9-tile right half (split point picked automatically at the widest natural gap in the tile grid, so the cut falls in a sensible spot rather than through a tile).
- Each tile is **84mm flat-to-flat**, with a 3mm perimeter ridge built only on tiles' true exterior edges (interior tile-to-tile boundaries are left flat).
- Each tile has a **12mm wire hole** on its own face, and (base script only) a **15mm connector pin hole** on tiles that pair up across the seam between neighboring tiles.
- The two halves are pushed apart by a configurable gap (`INVISIBLE_TILE_GAP`) so they don't overlap once split.
- The wall version adds a **6mm-wide, 26mm-tall** wall traced along the *real* outer boundary of each half — not a bounding box or convex hull, since the tile array is a non-convex "flower" shape and either of those would cut across the concave notches between lobes.

## Requirements

- Blender 4.x (uses `bpy`, `bmesh`, and the `wm.stl_export` operator)
- No external Python packages — everything is built from Blender's own modules

## Usage

1. Open Blender's **Scripting** workspace.
2. Load either script (`jaiva-hexa-drum-trays-script.py` for the base plate, or `jaiva-hexa-drum-trays-walls-script.py` for the version with the wall).
3. Adjust the parameters at the top of the file if needed (tile size, hole diameters, wall dimensions, etc. — see the script's own printed summary at the top of the console output for a full readout of the computed geometry).
4. Run the script. It builds both halves, prints a manifold-cleanliness report for each (non-manifold edge / zero-area face counts — should be at or near zero), and exports STLs next to the `.blend` file.

## Status

- **Base plate script** — stable. Tile geometry, wire holes, and pin holes are the proven calculation the rest of this project is built on.
- **Tray + wall script** — actively being refined. The wall-tracing logic has gone through several iterations to correctly follow the array's concave boundary and close every corner/end cleanly; check the console's manifold report after each run before trusting the exported STL.

## Background

Part of the Jaiba hexagonal electronic drum project — each hex tile hosts a silicone-isolated piezo/Velostat sensor cup, cast using a separate mold-core system, intended to reduce vibration cross-talk between adjacent pads.
