import bpy, bmesh, math, os
from mathutils import Vector

print("=== FLAT HEX PLATES — WALLS + INNER SENSOR PLATFORM ===")
print("=" * 60)

# ---- CONFIGURABLE PARAMETERS --------------------
HEX_FLAT_WIDTH = 84.0
HOLE_RADIUS = 28.0
PLATE_H = 2.0

# ---- PERIMETER CONTOUR PARAMETERS --------------------
PERIMETER_THICKNESS = 3.0
TOTAL_WIDTH = HEX_FLAT_WIDTH + 2 * PERIMETER_THICKNESS

# ---- INVISIBLE TILE GAP --------------------
JOIN_PLATES = False   # switch: True/1 = butt the RIGHT plate flush against
                        # the LEFT plate (zero gap, ignores INVISIBLE_TILE_GAP
                        # below) so they form one continuous surface along
                        # the split line. False/0 = keep the plates apart by
                        # INVISIBLE_TILE_GAP (old/default behavior).
INVISIBLE_TILE_GAP = 1.0
TILE_SPACING = 1.5 * HEX_FLAT_WIDTH
GAP_BETWEEN_PLATES = 0.0 if JOIN_PLATES else INVISIBLE_TILE_GAP * TILE_SPACING

# ---- ROW SPLIT (4-WAY QUARTER PRINTING) --------------------
ROW_SPLIT_MARGIN = 3.0   # mm pushback on each side of the row-split zigzag
                          # boundary (between the two middle rows), so the
                          # TOP and BOTTOM quadrants sit 2*ROW_SPLIT_MARGIN
                          # apart. Same idea as GAP_BETWEEN_PLATES but for
                          # the new split axis -- a small fixed print-bed
                          # clearance rather than the invisible-tile gap.

# ---- WALL PARAMETERS --------------------
WALL_WIDTH = 6.0    # extra width beyond PERIMETER_THICKNESS -> total offset from hex edge = PERIMETER_THICKNESS + WALL_WIDTH
WALL_HEIGHT = 26.0  # extrusion in Z+, starting at the top of the plate (z = PLATE_H)

# ---- INNER SENSOR TILE PARAMETERS --------------------
INNER_TILE_WIDTH = 78.0   # flat-to-flat width of the raised sensor platform —
                            # the space each sensor hexagon occupies
INNER_TILE_HEIGHT = 5.0   # ADJUST if needed — height wasn't respecified, this
                            # matches the earlier version's value
# Isolated per-tile platform, same center as its base hex tile. Since tile
# centers are spaced HEX_FLAT_WIDTH (84mm) apart and this platform is only
# 78mm wide, neighboring platforms are 84-78 = 6mm apart at their closest
# edges -- that's the gap for the vibration-damping textile/rug strip.

# ---- WIRE HOLE CONFIGURATION --------------------
WIRE_HOLE_DIAMETER = 12.0
WIRE_HOLE_RADIUS = WIRE_HOLE_DIAMETER / 2.0
WIRE_HOLE_ANGLE = 180

# ---- Direction mapping --------------------
DIRECTION_NAMES = {
    0: "Right", 60: "Upper-Right", 120: "Upper-Left",
    180: "Left", 240: "Lower-Left", 300: "Lower-Right"
}

# ---- Derived geometry --------------------
S  = HEX_FLAT_WIDTH / math.sqrt(3)
H  = S * math.sqrt(3)
V  = S * 1.5
APOTHEM = HEX_FLAT_WIDTH / 2.0
TOTAL_S = TOTAL_WIDTH / math.sqrt(3)

print(f"Tile geometry:")
print(f"  HEX_FLAT_WIDTH: {HEX_FLAT_WIDTH:.3f}mm")
print(f"  APOTHEM: {APOTHEM:.3f}mm")
print(f"  HOLE_RADIUS: {HOLE_RADIUS:.3f}mm")
print(f"  PLATE_H: {PLATE_H:.1f}mm")
print(f"")
print(f"Perimeter contour: {PERIMETER_THICKNESS:.1f}mm")
print(f"Wall: {WALL_WIDTH:.1f}mm wide (total offset from hex edge: {PERIMETER_THICKNESS + WALL_WIDTH:.1f}mm), "
      f"{WALL_HEIGHT:.1f}mm tall (z={PLATE_H:.1f}..{PLATE_H + WALL_HEIGHT:.1f}mm)")
print(f"Inner sensor tile: {INNER_TILE_WIDTH:.1f}mm wide, {INNER_TILE_HEIGHT:.1f}mm tall "
      f"(z={PLATE_H:.1f}..{PLATE_H + INNER_TILE_HEIGHT:.1f}mm), "
      f"{HEX_FLAT_WIDTH - INNER_TILE_WIDTH:.1f}mm gap between neighboring platforms")
print(f"Gap between plates: {GAP_BETWEEN_PLATES:.1f}mm"
      + (" (JOIN_PLATES on -- flush fit)" if JOIN_PLATES else ""))
print("=" * 60)

# ---- Grid ------------------------
y3=1.5*V; y2=0.5*V; y1=-0.5*V; y0=-1.5*V
grid_orig = [
    (-1.5*H,y3),(-0.5*H,y3),(0.5*H,y3),(1.5*H,y3),
    (-2.0*H,y2),(-1.0*H,y2),(0.0,y2),(1.0*H,y2),(2.0*H,y2),
    (-1.5*H,y1),(-0.5*H,y1),(0.5*H,y1),(1.5*H,y1),
    (-1.0*H,y0),(0.0,y0),(1.0*H,y0),
]

# Find split position
col_xs=sorted(set(round(cx,2) for cx,cy in grid_orig))
best_gap=0; best_split=0
for i in range(len(col_xs)-1):
    re=col_xs[i]+S
    le=col_xs[i+1]-S
    gap=le-re
    if gap>best_gap:
        best_gap=gap
        if col_xs[i] < 0 and col_xs[i+1] >= 0:
            best_split = (col_xs[i] + col_xs[i+1]) / 2.0

if best_split == 0:
    for i in range(len(col_xs)-1):
        re=col_xs[i]+S
        le=col_xs[i+1]-S
        gap=le-re
        if gap>best_gap:
            best_gap=gap
            best_split=(col_xs[i] + col_xs[i+1]) / 2.0

SPLIT_X = best_split

# Row split: the boundary between the two middle rows (the zigzag gap
# where hex tiles from adjacent, column-offset rows meet). With exactly 4
# rows present, that's always between the 2nd and 3rd row.
row_ys = sorted(set(round(cy, 2) for cx, cy in grid_orig), reverse=True)
SPLIT_Y = (row_ys[1] + row_ys[2]) / 2.0

left_grid = []
right_grid = []
for cx, cy in grid_orig:
    if cx < SPLIT_X:
        left_grid.append((cx, cy))
    else:
        right_grid.append((cx + GAP_BETWEEN_PLATES, cy))

print(f"Split at X = {SPLIT_X:.3f}")
print(f"Left: {len(left_grid)} tiles, Right: {len(right_grid)} tiles")
print(f"Split at Y = {SPLIT_Y:.3f}")
print("=" * 60)

# ---- Quadrants (for 1/4-plate printing) ------------------------
# Labels (L00.. / R00..) are assigned from the ORIGINAL left_grid/
# right_grid order above, so a tile keeps the same tag whether it's
# exported as part of a half-plate or a quarter-plate. Quadrant
# assignment and the ROW_SPLIT_MARGIN shift are then applied on top,
# independent of that labeling.
def split_into_quadrants(half_grid, label_prefix):
    top, bottom = [], []
    for i, (cx, cy) in enumerate(half_grid):
        tag = f"{label_prefix}{i:02d}"
        if cy >= SPLIT_Y:
            top.append((tag, cx, cy + ROW_SPLIT_MARGIN))
        else:
            bottom.append((tag, cx, cy - ROW_SPLIT_MARGIN))
    return top, bottom

tl_tiles, bl_tiles = split_into_quadrants(left_grid, 'L')
tr_tiles, br_tiles = split_into_quadrants(right_grid, 'R')

print(f"Top-Left: {len(tl_tiles)} tiles, Top-Right: {len(tr_tiles)} tiles, "
      f"Bottom-Left: {len(bl_tiles)} tiles, Bottom-Right: {len(br_tiles)} tiles")
print("=" * 60)

# ---- Cleanup -------------------------------
def cleanup_objects():
    to_remove = []
    for obj in bpy.data.objects:
        if obj.name.startswith(("SensorBase", "Hole_", "Wire_", "TileNum_", "Cut_")):
            to_remove.append(obj)
    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)
    print(f"Cleaned up {len(to_remove)} objects")

cleanup_objects()
print("=" * 60)

# ---- Builders -------------------------
def get_hole_position(cx, cy, angle_deg):
    angle_rad = math.radians(angle_deg)
    return cx + HOLE_RADIUS * math.cos(angle_rad), cy + HOLE_RADIUS * math.sin(angle_rad)

def get_hex_corners(cx, cy, flat_width):
    s = flat_width / math.sqrt(3)
    angles = [math.radians(30 + 60*i) for i in range(6)]
    return [(cx + s*math.cos(a), cy + s*math.sin(a)) for a in angles]

def _vkey(p):
    return (round(p[0], 3), round(p[1], 3))

# Edge counts over the FULL, unsplit 16-tile grid (grid_orig, un-shifted —
# before the Left/Right split and before the invisible-tile-gap shift is
# applied to the right side). An edge that's exterior here (count 1) is a
# true outer-contour edge and gets the full perimeter+wall treatment on
# whichever plate it ends up on. An edge that's INTERIOR here (count 2)
# but ends up exterior to a single plate — because its two tiles landed on
# opposite sides of the split — is "gap-facing": it only looks exterior
# because the other plate's matching tile isn't part of this mesh, not
# because it's really an outer edge. Those get a plain flat closing wall
# instead of the 9mm perimeter+wall bulge, so the two plates' contours in
# the gap still read as the two halves of one continuous shape, matching
# the (wall-less) base script's plates.
FULL_EDGE_COUNT = {}
for (cx, cy) in grid_orig:
    corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH)
    for i in range(6):
        j = (i + 1) % 6
        ek = tuple(sorted([_vkey(corners[i]), _vkey(corners[j])]))
        FULL_EDGE_COUNT[ek] = FULL_EDGE_COUNT.get(ek, 0) + 1

def compute_boundary_offset_map(grid_tiles, offset_distance, shift_x=0.0, shift_y=0.0):
    """Computes ONE offset point per boundary vertex of the union of all
    tiles' flat hexagons, offset outward by `offset_distance` — computed
    ONCE per shared vertex (not once per tile), which is the fix for the
    confirmed root cause of every previous attempt: two different tiles
    independently scaling "the same" shared vertex outward from their own
    separate centers land at two DIFFERENT points. Here there is only ever
    one answer per point, by construction."""
    tile_corner_lists = [get_hex_corners(cx, cy, HEX_FLAT_WIDTH) for (cx, cy) in grid_tiles]

    edge_count = {}
    for corners in tile_corner_lists:
        for i in range(6):
            j = (i + 1) % 6
            ek = tuple(sorted([_vkey(corners[i]), _vkey(corners[j])]))
            edge_count[ek] = edge_count.get(ek, 0) + 1

    bad_edges = {ek: c for ek, c in edge_count.items() if c > 2}
    if bad_edges:
        print(f"  ⚠ offset[{offset_distance:.1f}mm]: {len(bad_edges)} edges shared by >2 tiles: {list(bad_edges.items())[:5]}")

    nxt, prv = {}, {}
    for corners in tile_corner_lists:
        for i in range(6):
            j = (i + 1) % 6
            p0, p1 = corners[i], corners[j]
            p0_full = (p0[0] - shift_x, p0[1] - shift_y)
            p1_full = (p1[0] - shift_x, p1[1] - shift_y)
            fek = tuple(sorted([_vkey(p0_full), _vkey(p1_full)]))
            if FULL_EDGE_COUNT.get(fek, 0) != 1:
                continue  # interior in the full grid, or gap-facing
            k0, k1 = _vkey(p0), _vkey(p1)
            nxt.setdefault(k0, []).append(k1)
            prv.setdefault(k1, []).append(k0)

    def outward_normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        return (dy / L, -dx / L)  # CCW boundary -> rotate -90 deg = outward

    offset_map = {}
    fallback_verts = []
    clamped_verts = []
    all_verts = set(nxt.keys()) | set(prv.keys())
    for v in all_verts:
        outs = nxt.get(v, [])
        ins = prv.get(v, [])
        if len(outs) == 1 and len(ins) == 1:
            n_in = outward_normal(ins[0], v)
            n_out = outward_normal(v, outs[0])
            mx, my = n_in[0] + n_out[0], n_in[1] + n_out[1]
            mlen = math.hypot(mx, my)
            if mlen < 1e-9:
                mx, my = n_in
            else:
                mx, my = mx / mlen, my / mlen
            raw_cos_half = mx * n_in[0] + my * n_in[1]
            cos_half = max(raw_cos_half, 0.35)  # clamp: miter <= ~3x offset
            if raw_cos_half < 0.35:
                clamped_verts.append((v, raw_cos_half))
            miter_len = offset_distance / cos_half
            offset_map[v] = (v[0] + mx * miter_len, v[1] + my * miter_len)
        else:
            fallback_verts.append((v, len(ins), len(outs)))
            normals = [outward_normal(a, v) for a in ins] + [outward_normal(v, b) for b in outs]
            if normals:
                ax = sum(n[0] for n in normals) / len(normals)
                ay = sum(n[1] for n in normals) / len(normals)
                al = math.hypot(ax, ay) or 1.0
                offset_map[v] = (v[0] + (ax / al) * offset_distance, v[1] + (ay / al) * offset_distance)
            else:
                offset_map[v] = v

    print(f"  offset[{offset_distance:.1f}mm]: {len(all_verts)} boundary verts, "
          f"{len(fallback_verts)} fallback (branch/dangling), "
          f"{len(clamped_verts)} miter-clamped")
    if fallback_verts:
        print(f"    fallback verts (pos, in-count, out-count): {fallback_verts[:10]}")
    if clamped_verts:
        print(f"    clamped verts (pos, raw_cos_half): {clamped_verts[:10]}")
    dangling_verts = {v for (v, _, _) in fallback_verts}
    return offset_map, dangling_verts

# GLOBAL (unsplit, all 16 tiles) boundary offsets, computed once. At a
# vertex right at the split line, a per-half offset map only ever sees ONE
# of the two true-exterior edges that actually meet there (the other one
# belongs to a tile that lives in the OTHER plate's mesh) -- it falls back
# to a single-edge normal instead of a proper two-edge miter. The LEFT and
# RIGHT plates then each compute a different, independently-wrong offset
# at what should be the exact same point, which is what shows up as a
# mismatched notch/sliver where the two plates' walls meet once joined
# (see JOIN_PLATES). Using the full, unsplit grid here means both edges
# at that vertex are visible to the SAME miter calculation, so both
# plates end up using the identical, correctly-mitered point.
print("\nComputing GLOBAL (unsplit) boundary offsets for continuous wall miters across the split line...")
GLOBAL_PERIM_OFFSET, _ = compute_boundary_offset_map(grid_orig, PERIMETER_THICKNESS, shift_x=0.0)
GLOBAL_WALL_OFFSET, _ = compute_boundary_offset_map(grid_orig, PERIMETER_THICKNESS + WALL_WIDTH, shift_x=0.0)
print("=" * 60)

def globalize_offset_map(local_map, global_map, shift_x, shift_y=0.0):
    """Overrides each local (per-quadrant) offset value with its globally-
    mitered equivalent where one exists, shifted into this quadrant's
    local coordinate space. See the comment above GLOBAL_PERIM_OFFSET."""
    out = dict(local_map)
    for k in local_map:
        gk = (round(k[0] - shift_x, 3), round(k[1] - shift_y, 3))
        if gk in global_map:
            gx, gy = global_map[gk]
            out[k] = (gx + shift_x, gy + shift_y)
    return out

def build_plate_body(grid_tiles, solid_name, shift_x=0.0, shift_y=0.0):
    """Builds the flat hex tiles, the PERIMETER_THICKNESS contour, the
    WALL_WIDTH wall, and the raised inner sensor platform, via bmesh face
    construction, using a shared boundary offset computed ONCE per vertex
    (see compute_boundary_offset_map) instead of per tile."""
    print(f"\nBuilding {solid_name} with {len(grid_tiles)} tiles")

    mesh = bpy.data.meshes.new(solid_name+"_mesh")
    obj = bpy.data.objects.new(solid_name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    vmap = {}

    def gv(x, y, z):
        k=(round(x,3), round(y,3), round(z,3))
        if k not in vmap:
            vmap[k] = bm.verts.new((x, y, z))
        return vmap[k]

    z0, z1, z2 = 0.0, PLATE_H, PLATE_H + WALL_HEIGHT

    tile_corners = {}
    edge_count = {}
    for (cx, cy) in grid_tiles:
        corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH)
        tile_corners[(cx, cy)] = corners
        for i in range(6):
            j = (i + 1) % 6
            ek = tuple(sorted([_vkey(corners[i]), _vkey(corners[j])]))
            edge_count[ek] = edge_count.get(ek, 0) + 1

    perim_offset, dangling_verts = compute_boundary_offset_map(grid_tiles, PERIMETER_THICKNESS, shift_x, shift_y)
    wall_outer_offset, _ = compute_boundary_offset_map(grid_tiles, PERIMETER_THICKNESS + WALL_WIDTH, shift_x, shift_y)
    perim_offset = globalize_offset_map(perim_offset, GLOBAL_PERIM_OFFSET, shift_x, shift_y)
    wall_outer_offset = globalize_offset_map(wall_outer_offset, GLOBAL_WALL_OFFSET, shift_x, shift_y)

    # Tile top (Z1): only the RING between the 84mm outer boundary and the
    # 78mm platform boundary — not a solid hex. A solid top face here would
    # sit exactly coincident with the platform's own bottom face (built
    # below) across the platform's entire footprint, since both are at the
    # same z1 height. That duplicate, overlapping geometry is what was
    # actually breaking almost every wire-hole cut — the holes sit at
    # radius 28mm, well inside the 78mm platform's 39mm apothem, so every
    # cut had to pass straight through this overlap. Bottom (Z0) stays a
    # solid hex — nothing else occupies that level, so no overlap there.
    for (cx, cy) in grid_tiles:
        corners = tile_corners[(cx, cy)]
        inner_platform_corners = get_hex_corners(cx, cy, INNER_TILE_WIDTH)
        outer_top = [gv(x, y, z1) for x, y in corners]
        inner_top = [gv(x, y, z1) for x, y in inner_platform_corners]
        for i in range(6):
            j = (i + 1) % 6
            try: bm.faces.new([outer_top[i], outer_top[j], inner_top[j], inner_top[i]])
            except ValueError: pass
        bot = [gv(x, y, z0) for x, y in corners]
        try: bm.faces.new(list(reversed(bot)))
        except ValueError: pass

    # ---- Inner sensor platform ------------------------------------------
    # A separate, isolated INNER_TILE_WIDTH (78mm) hex prism per tile,
    # sitting on top of the base plate (z1 to z1+INNER_TILE_HEIGHT), same
    # center as the base tile. It's smaller than the 84mm base hex and
    # deliberately doesn't touch its neighbors — that 84-78=6mm gap is
    # where the vibration-damping rug/textile goes — so it's built as its
    # own small watertight prism, independent of the boundary/wall logic.
    z_inner = z1 + INNER_TILE_HEIGHT
    platform_count = 0
    for (cx, cy) in grid_tiles:
        inner_corners = get_hex_corners(cx, cy, INNER_TILE_WIDTH)
        itop = [gv(x, y, z_inner) for x, y in inner_corners]
        try: bm.faces.new(itop)
        except ValueError as e: print(f"  ⚠ inner top FAILED at ({cx:.1f},{cy:.1f}): {e}")
        ibot = [gv(x, y, z1) for x, y in inner_corners]
        try: bm.faces.new(list(reversed(ibot)))
        except ValueError as e: print(f"  ⚠ inner bottom FAILED at ({cx:.1f},{cy:.1f}): {e}")
        for i in range(6):
            j = (i + 1) % 6
            ib0 = gv(inner_corners[i][0], inner_corners[i][1], z1)
            ib1 = gv(inner_corners[j][0], inner_corners[j][1], z1)
            it0 = gv(inner_corners[i][0], inner_corners[i][1], z_inner)
            it1 = gv(inner_corners[j][0], inner_corners[j][1], z_inner)
            try: bm.faces.new([ib0, ib1, it1, it0])
            except ValueError as e: print(f"  ⚠ inner side FAILED at ({cx:.1f},{cy:.1f}) edge {i}: {e}")
        platform_count += 1
    print(f"  Built {platform_count} inner sensor platforms "
          f"({INNER_TILE_WIDTH:.1f}mm wide, z={z1:.1f}..{z_inner:.1f}mm)")

    exterior_edge_count = 0
    for (cx, cy) in grid_tiles:
        corners = tile_corners[(cx, cy)]
        for i in range(6):
            j = (i + 1) % 6
            p0, p1 = corners[i], corners[j]

            ek = tuple(sorted([_vkey(p0), _vkey(p1)]))
            if edge_count[ek] != 1:
                continue  # interior edge, shared with a neighbor tile
            exterior_edge_count += 1

            b0 = gv(p0[0], p0[1], z0); b1 = gv(p1[0], p1[1], z0)
            t0 = gv(p0[0], p0[1], z1); t1 = gv(p1[0], p1[1], z1)

            p0_full = (p0[0] - shift_x, p0[1] - shift_y)
            p1_full = (p1[0] - shift_x, p1[1] - shift_y)
            fek = tuple(sorted([_vkey(p0_full), _vkey(p1_full)]))
            if FULL_EDGE_COUNT.get(fek, 0) != 1:
                try: bm.faces.new([b0, b1, t1, t0])
                except ValueError: pass
                continue

            k0, k1 = _vkey(p0), _vkey(p1)
            po0, po1 = perim_offset[k0], perim_offset[k1]
            wo0, wo1 = wall_outer_offset[k0], wall_outer_offset[k1]

            pt0 = gv(po0[0], po0[1], z1); pt1 = gv(po1[0], po1[1], z1)
            pb0 = gv(po0[0], po0[1], z0); pb1 = gv(po1[0], po1[1], z0)
            wo0_z0 = gv(wo0[0], wo0[1], z0); wo1_z0 = gv(wo1[0], wo1[1], z0)
            wt0 = gv(wo0[0], wo0[1], z2); wt1 = gv(wo1[0], wo1[1], z2)
            pt0_z2 = gv(po0[0], po0[1], z2); pt1_z2 = gv(po1[0], po1[1], z2)

            try: bm.faces.new([t0, t1, pt1, pt0])
            except ValueError: pass
            try: bm.faces.new([b0, b1, pb1, pb0])
            except ValueError: pass
            try: bm.faces.new([pt0, pt1, pt1_z2, pt0_z2])
            except ValueError: pass
            try: bm.faces.new([wo0_z0, wo1_z0, wt1, wt0])
            except ValueError: pass
            try: bm.faces.new([pt0_z2, pt1_z2, wt1, wt0])
            except ValueError: pass
            try: bm.faces.new([pb0, pb1, wo1_z0, wo0_z0])
            except ValueError: pass

    end_caps_added = 0
    for v in dangling_verts:
        po = perim_offset[v]
        wo = wall_outer_offset[v]
        rv0 = gv(v[0], v[1], z0); rv1 = gv(v[0], v[1], z1)
        pov0 = gv(po[0], po[1], z0); pov1 = gv(po[0], po[1], z1); pov2 = gv(po[0], po[1], z2)
        wov0 = gv(wo[0], wo[1], z0); wov2 = gv(wo[0], wo[1], z2)
        try:
            bm.faces.new([rv0, pov0, wov0, wov2, pov2, pov1, rv1])
            end_caps_added += 1
        except ValueError: pass

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    mesh.update()   # forces the viewport's draw/tessellation buffers to
                      # actually refresh — without this, low-level bmesh
                      # writes can leave stale render data even though the
                      # underlying vertex/polygon arrays are already correct
                      # (which is exactly what the console/Python-check
                      # mismatch pointed to)

    nm, za = report_manifold_stats(obj)
    print(f"  {solid_name}: {exterior_edge_count} true exterior edges, "
          f"{end_caps_added} end caps, {platform_count} inner platforms, "
          f"{nm} non-manifold edges, {za} zero-area faces")
    return obj

def make_wire_hole_cutter(name, cx, cy):
    """Wire hole - goes through the full height (unchanged from the walls script)"""
    hx, hy = get_hole_position(cx, cy, WIRE_HOLE_ANGLE)
    print(f"    Wire hole at ({hx:.3f}, {hy:.3f}) (angle: {WIRE_HOLE_ANGLE}°, ⌀{WIRE_HOLE_DIAMETER:.1f}mm)")

    total_height = PLATE_H + WALL_HEIGHT
    bottom=-2.0
    top=total_height+2.0
    height=top-bottom
    center_z=(top+bottom)/2.0

    mesh=bpy.data.meshes.new(name+"_mesh")
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bm=bmesh.new()
    segs=32
    half=height/2.0
    bv,tv=[],[]

    for i in range(segs):
        a=2*math.pi*i/segs
        xo=WIRE_HOLE_RADIUS*math.cos(a)
        yo=WIRE_HOLE_RADIUS*math.sin(a)
        bv.append(bm.verts.new((xo,yo,-half)))
        tv.append(bm.verts.new((xo,yo,half)))

    for i in range(segs):
        j=(i+1)%segs
        bm.faces.new([bv[i],bv[j],tv[j],tv[i]])
    bm.faces.new(list(reversed(bv)))
    bm.faces.new(tv)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    obj.location=Vector((hx, hy, center_z))
    return obj

def apply_transforms(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)

def report_manifold_stats(obj):
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold)
    zero_area = sum(1 for f in bm.faces if f.calc_area() < 1e-5)
    bm.free()
    return nonmanifold, zero_area

def duplicate_obj(obj, name):
    new_data = obj.data.copy()
    new_obj = bpy.data.objects.new(name, new_data)
    new_obj.matrix_world = obj.matrix_world.copy()
    bpy.context.collection.objects.link(new_obj)
    return new_obj

def do_diff(target, cutter, solver='EXACT'):
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active=target
    mod=target.modifiers.new("Diff",'BOOLEAN')
    mod.operation='DIFFERENCE'
    mod.object=cutter
    mod.solver=solver
    try:
        bpy.ops.object.modifier_apply(modifier="Diff")
        return True
    except Exception as e:
        print(f"      failed ({solver}): {e}")
        try: target.modifiers.remove(mod)
        except: pass
        return False

def cutter_leaked_into_result(cutter, result_obj):
    """True if any of the cutter's own vertex positions survive
    unchanged in the result — a sign the boolean fused the cutter's
    shell in rather than actually subtracting it. A genuine subtraction
    always creates a NEW intersection boundary between the two shapes;
    it should never reproduce one input's exact, unmodified surface.
    This is what catches the case safe_cut's manifold-delta check
    alone could miss: a boolean that reports success and comes back
    fully manifold-clean, but never actually carved the hole — the
    cutter's own geometry just got fused in as leftover material."""
    cutter_positions = {(round(v.co.x,3), round(v.co.y,3), round(v.co.z,3))
                         for v in cutter.data.vertices}
    result_positions = {(round(v.co.x,3), round(v.co.y,3), round(v.co.z,3))
                         for v in result_obj.data.vertices}
    leaked = cutter_positions & result_positions
    return len(leaked) > 0, len(leaked)

def try_cut_on_copy(target, cutter, solver):
    nm0, za0 = report_manifold_stats(target)
    dup = duplicate_obj(target, target.name + "_TRY")
    ok = do_diff(dup, cutter, solver=solver)
    if not ok:
        bpy.data.objects.remove(dup, do_unlink=True)
        return False, None, None, None
    nm1, za1 = report_manifold_stats(dup)
    leaked, leak_count = cutter_leaked_into_result(cutter, dup)
    if leaked:
        print(f"      {solver}: boolean reported success but {leak_count} cutter "
              f"vertices leaked into the result — treating as failed")
        # Force a bad score so safe_cut's comparison will always prefer
        # the alternative solver (or report outright failure) instead of
        # silently accepting a cut that didn't actually remove material.
        nm1 = nm0 + 1000
    print(f"      {solver}: non-manifold edges: {nm1-nm0}, zero-area faces: {za1-za0}")
    return True, nm1 - nm0, za1 - za0, dup

def safe_cut(label, target, cutter, primary='EXACT'):
    print(f"    Cutting {label}...")
    alt = 'FLOAT' if primary == 'EXACT' else 'EXACT'
    ok1, dn1, dz1, dup1 = try_cut_on_copy(target, cutter, primary)
    if ok1 and dn1 == 0 and dz1 == 0:
        target.data = dup1.data
        bpy.data.objects.remove(dup1, do_unlink=True)
        print(f"    ✓ {label} cut cleanly with {primary}")
        return True
    ok2, dn2, dz2, dup2 = try_cut_on_copy(target, cutter, alt)
    candidates = []
    if ok1: candidates.append((dn1 + dz1, primary, dup1))
    if ok2: candidates.append((dn2 + dz2, alt, dup2))
    if not candidates:
        print(f"    ⚠ {label}: both solvers failed — material NOT removed")
        return False
    candidates.sort(key=lambda c: c[0])
    best_score, best_solver, best_dup = candidates[0]
    target.data = best_dup.data
    for _, _, d in candidates:
        if d is not best_dup:
            bpy.data.objects.remove(d, do_unlink=True)
    bpy.data.objects.remove(best_dup, do_unlink=True)
    if best_score > 0:
        print(f"    ⚠ {label}: cleanest available ({best_solver}) still has {best_score} issue(s)")
    return True

def add_tile_label(label, cx, cy):
    bpy.ops.object.text_add(location=(cx, cy, PLATE_H + WALL_HEIGHT + 1.0))
    txt = bpy.context.active_object
    txt.name = f"TileNum_{label}"
    txt.data.body = label
    txt.data.size = 8.0
    txt.data.align_x = 'CENTER'
    txt.data.align_y = 'CENTER'
    return txt

# ---- Build -------------------------
def build_side(tiles, solid_name, shift_x=0.0, shift_y=0.0):
    """tiles: list of (tag, cx, cy) -- tag is the tile's stable label
    (e.g. "L04"), assigned once from the original left/right split, kept
    unchanged regardless of which quadrant the tile ends up exported in."""
    grid_tiles = [(cx, cy) for (tag, cx, cy) in tiles]
    print(f"\n{'='*60}")
    print(f"Building {solid_name} with {len(grid_tiles)} tiles")
    print(f"{'='*60}")

    obj = build_plate_body(grid_tiles, solid_name, shift_x, shift_y)

    for i, (tag, cx, cy) in enumerate(tiles):
        print(f"\n  [{i+1}/{len(tiles)}] Processing {tag} at ({cx:.3f}, {cy:.3f})...")

        wire = make_wire_hole_cutter(f"Wire_{tag}", cx, cy)
        apply_transforms(wire)
        safe_cut(f"{tag} wire hole", obj, wire, primary='EXACT')
        bpy.data.objects.remove(wire, do_unlink=True)

        add_tile_label(tag, cx, cy)

    nm, za = report_manifold_stats(obj)
    print(f"\n  Final stats for {solid_name}:")
    print(f"    Non-manifold edges: {nm}")
    print(f"    Zero-area faces: {za}")

    return obj

# ---- Build all four quadrant plates ----
tl_obj = build_side(tl_tiles, "SensorBase_TL", shift_x=0.0, shift_y=ROW_SPLIT_MARGIN)
tr_obj = build_side(tr_tiles, "SensorBase_TR", shift_x=GAP_BETWEEN_PLATES, shift_y=ROW_SPLIT_MARGIN)
bl_obj = build_side(bl_tiles, "SensorBase_BL", shift_x=0.0, shift_y=-ROW_SPLIT_MARGIN)
br_obj = build_side(br_tiles, "SensorBase_BR", shift_x=GAP_BETWEEN_PLATES, shift_y=-ROW_SPLIT_MARGIN)

quadrant_objs = [tl_obj, tr_obj, bl_obj, br_obj]

# Force a full dependency-graph/viewport refresh — belt-and-suspenders
# alongside the per-mesh mesh.update() calls above, in case the viewport
# was still showing stale draw data for any other reason.
for obj in quadrant_objs:
    obj.data.update()
bpy.context.view_layer.update()
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.tag_redraw()

# ---- Export -------------------------
blend_path = bpy.data.filepath
export_dir = os.path.dirname(blend_path) if blend_path else os.path.expanduser("~")

def export_obj(obj, filename):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(export_dir, filename)
    try:
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)
        print(f"✅ Exported: {path}")
    except Exception as e:
        try:
            bpy.ops.export_mesh.stl(filepath=path, use_selection=True)
            print(f"✅ Exported: {path}")
        except Exception as e2:
            print(f"❌ Export failed: {e2}")

export_obj(tl_obj, "flat_hex_plate-Walls2_TOP_LEFT.stl")
export_obj(tr_obj, "flat_hex_plate-Walls2_TOP_RIGHT.stl")
export_obj(bl_obj, "flat_hex_plate-Walls2_BOTTOM_LEFT.stl")
export_obj(br_obj, "flat_hex_plate-Walls2_BOTTOM_RIGHT.stl")

print("\n" + "="*60)
print("=== DONE ===")
print(f"Top-Left plate: {len(tl_tiles)} tiles")
print(f"Top-Right plate: {len(tr_tiles)} tiles")
print(f"Bottom-Left plate: {len(bl_tiles)} tiles")
print(f"Bottom-Right plate: {len(br_tiles)} tiles")
print(f"Total tiles: {len(tl_tiles) + len(tr_tiles) + len(bl_tiles) + len(br_tiles)}")
print(f"Tile size: {HEX_FLAT_WIDTH:.1f}mm flat-to-flat")
print(f"Perimeter thickness: {PERIMETER_THICKNESS:.1f}mm")
print(f"Wall: {WALL_WIDTH:.1f}mm wide (total offset from hex edge: {PERIMETER_THICKNESS + WALL_WIDTH:.1f}mm), "
      f"{WALL_HEIGHT:.1f}mm tall")
print(f"Inner sensor tile: {INNER_TILE_WIDTH:.1f}mm wide, {INNER_TILE_HEIGHT:.1f}mm tall, "
      f"{HEX_FLAT_WIDTH - INNER_TILE_WIDTH:.1f}mm gap between neighbors")
print(f"Join plates (flush fit): {'ON' if JOIN_PLATES else 'OFF'}")
print(f"Invisible tile gap: {INVISIBLE_TILE_GAP:.1f} tiles = {GAP_BETWEEN_PLATES:.1f}mm")
print(f"Row split margin: {ROW_SPLIT_MARGIN:.1f}mm each side ({2*ROW_SPLIT_MARGIN:.1f}mm total gap)")
print(f"Wire hole diameter: {WIRE_HOLE_DIAMETER:.1f}mm")
print("="*60)