import bpy, bmesh, math, os
from mathutils import Vector

print("=== FLAT HEX PLATES — WALLS + INNER SENSOR PLATFORM ===")
print("=" * 60)

# ---- CONFIGURABLE PARAMETERS --------------------
HEX_FLAT_WIDTH = 84.0
HOLE_RADIUS = 28.0
PLATE_H = 20.0

# ---- PERIMETER CONTOUR PARAMETERS --------------------
PERIMETER_THICKNESS = 3.0
TOTAL_WIDTH = HEX_FLAT_WIDTH + 2 * PERIMETER_THICKNESS

# ---- INVISIBLE TILE GAP --------------------
JOIN_PLATES = True
INVISIBLE_TILE_GAP = 1.0
TILE_SPACING = 1.5 * HEX_FLAT_WIDTH
GAP_BETWEEN_PLATES = 0.0 if JOIN_PLATES else INVISIBLE_TILE_GAP * TILE_SPACING

# ---- ROW SPLIT (4-WAY QUARTER PRINTING) --------------------
ROW_SPLIT_MARGIN = 3.0

# ---- WALL PARAMETERS --------------------
WALL_WIDTH = 6.0
WALL_HEIGHT = 26.0

# ---- TOP/BOTTOM REINFORCEMENT RAILS --------------------
# Per your corrected spec: 15mm TOTAL from the raw hex tip to the outer
# edge of the new reinforcement — NOT a filled rectangle, NOT 50mm. The
# existing wall already reaches PERIMETER_THICKNESS+WALL_WIDTH=9mm from
# the tip, so the genuinely NEW material is only 15-9=6mm thick at a
# peak (deeper at the valleys, where the wall's own zigzag surface
# falls back well short of 9mm). Each rail is merged directly into its
# quadrant's own mesh (not built as a separate solid and boolean-
# unioned in) -- see merge_rail_into_wall below. Built as the LAST
# step in the whole script, after every existing rod hole and canal —
# so those all run against completely unchanged geometry, exactly as
# before.
RAIL_TOTAL_FROM_TIP = 15.0
RAIL_ROD_OFFSET_FROM_OUTER = 7.3   # rod sits this far IN from the rail's
                                    # true outer edge (y_outer). Was 4.3,
                                    # then 8.3 (+4mm in), then backed off
                                    # 1mm to here -- at 8.3 the rod center
                                    # sat only 6.7mm from a peak's tip
                                    # (15-8.3), and the hex wedge there is
                                    # only ~7.7mm wide (2*6.7*tan(30 deg)),
                                    # barely wider than the rod's own 7mm
                                    # diameter -- confirmed in-engine as
                                    # the rod grazing/cutting through the
                                    # tip's own side walls. At 7.3, rod
                                    # center sits 7.7mm from the tip where
                                    # the wedge is ~8.9mm wide, giving
                                    # ~0.9mm clearance each side. Z
                                    # (RAIL_ROD_Z) and X untouched.
RAIL_ROD_Z = (PLATE_H + WALL_HEIGHT) - 10.0   # the rail's own rod moves up
                                                # toward the TOP of the rail
                                                # (Z+) instead of sharing the
                                                # base plate's rod Z (see
                                                # ROD_HOLE_Z_X_AXIS below) --
                                                # both TopRail and BottomRail
                                                # rod centers sit 10mm below
                                                # the rail's top surface
                                                # (Z=PLATE_H+WALL_HEIGHT),
                                                # leaving ~6.5mm margin to
                                                # that top face.

# ---- INNER SENSOR TILE PARAMETERS --------------------
INNER_TILE_WIDTH = 78.0
INNER_TILE_HEIGHT = 5.0

# ---- WIRE HOLE CONFIGURATION --------------------
WIRE_HOLE_DIAMETER = 12.0
WIRE_HOLE_RADIUS = WIRE_HOLE_DIAMETER / 2.0
WIRE_HOLE_ANGLE = 180

# ---- THREADED ROD HOLES (unite the 4 quadrant plates) --------------
ROD_HOLE_DIAMETER = 7.0
ROD_HOLE_RADIUS = ROD_HOLE_DIAMETER / 2.0
ROD_HOLE_Y_OFFSET = 20.0
ROD_HOLE_Y_OFFSET_L04_R06 = -20.0
ROD_HOLE_Z_Y_AXIS = 3.0 * PLATE_H / 4.0   # 15.0mm -- unchanged, the fixed
                                            # reference the X-axis rod Z
                                            # below is measured against.
# The X-axis and Y-axis rod centerlines are perpendicular, horizontal
# skew lines (directions (1,0,0) and (0,1,0)) at different Z -- for that
# specific geometry the minimum distance between the two lines is
# ALWAYS exactly |ROD_HOLE_Z_Y_AXIS - ROD_HOLE_Z_X_AXIS| regardless of
# their X/Y offsets (the cross product of the two directions is purely
# vertical, so the offset terms drop out of the distance formula). The
# two 7mm-diameter rods become tangent (their outer surfaces touch) when
# that Z gap equals the sum of their radii, i.e. one full diameter:
# ROD_HOLE_Z_Y_AXIS - ROD_HOLE_DIAMETER. Backing off 1mm further from
# that tangent point (per your ask) gives a real 1mm surface gap instead
# of a knife-edge touch, and moving the X-axis rod up to reach it also
# fixes it sitting only 1.5mm clear of Z=0 at the old PLATE_H/4 -- the
# new position clears Z=0 by 3.5mm instead.
ROD_HOLE_Z_X_AXIS = ROD_HOLE_Z_Y_AXIS - ROD_HOLE_DIAMETER - 1.0   # 7.0mm
ROD_HOLE_X_LEFT = -HEX_FLAT_WIDTH
ROD_HOLE_X_RIGHT = HEX_FLAT_WIDTH

# ---- WIRE-ROUTING CANALS (rear/bottom face) — UNCHANGED --------------
CANAL_WIDTH = 15.0
CANAL_DEPTH = 10.0
CANAL_Z_START = -2.0
CANAL_Z_END = CANAL_DEPTH
CANAL_LEFT_X = -1000.0
CANAL_RIGHT_MARGIN = WIRE_HOLE_RADIUS + 2.0

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
print(f"Rail: {RAIL_TOTAL_FROM_TIP:.1f}mm total from tip "
      f"({RAIL_TOTAL_FROM_TIP - (PERIMETER_THICKNESS+WALL_WIDTH):.1f}mm new beyond the existing wall)")
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

def cleanup_objects():
    to_remove = []
    for obj in bpy.data.objects:
        if obj.name.startswith(("SensorBase", "Hole_", "Wire_", "TileNum_", "Cut_", "WallSeg_",
                                "W23", "CornerStrip")):
            to_remove.append(obj)
    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)
    # Purge the red-line material if no longer referenced.
    mat = bpy.data.materials.get("W23RedLine")
    if mat is not None and mat.users == 0:
        bpy.data.materials.remove(mat)
    print(f"Cleaned up {len(to_remove)} objects")

cleanup_objects()
print("=" * 60)

def get_hole_position(cx, cy, angle_deg):
    angle_rad = math.radians(angle_deg)
    return cx + HOLE_RADIUS * math.cos(angle_rad), cy + HOLE_RADIUS * math.sin(angle_rad)

def get_hex_corners(cx, cy, flat_width):
    s = flat_width / math.sqrt(3)
    angles = [math.radians(30 + 60*i) for i in range(6)]
    return [(cx + s*math.cos(a), cy + s*math.sin(a)) for a in angles]

def _vkey(p):
    return (round(p[0], 3), round(p[1], 3))

FULL_EDGE_COUNT = {}
for (cx, cy) in grid_orig:
    corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH)
    for i in range(6):
        j = (i + 1) % 6
        ek = tuple(sorted([_vkey(corners[i]), _vkey(corners[j])]))
        FULL_EDGE_COUNT[ek] = FULL_EDGE_COUNT.get(ek, 0) + 1

def compute_boundary_offset_map(grid_tiles, offset_distance, shift_x=0.0, shift_y=0.0):
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
                continue
            k0, k1 = _vkey(p0), _vkey(p1)
            nxt.setdefault(k0, []).append(k1)
            prv.setdefault(k1, []).append(k0)

    def outward_normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        return (dy / L, -dx / L)

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
            cos_half = max(raw_cos_half, 0.35)
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

print("\nComputing GLOBAL (unsplit) boundary offsets for continuous wall miters across the split line...")
GLOBAL_PERIM_OFFSET, _ = compute_boundary_offset_map(grid_orig, PERIMETER_THICKNESS, shift_x=0.0)
GLOBAL_WALL_OFFSET, _ = compute_boundary_offset_map(grid_orig, PERIMETER_THICKNESS + WALL_WIDTH, shift_x=0.0)
print("=" * 60)

def globalize_offset_map(local_map, global_map, shift_x, shift_y=0.0):
    out = dict(local_map)
    for k in local_map:
        gk = (round(k[0] - shift_x, 3), round(k[1] - shift_y, 3))
        if gk in global_map:
            gx, gy = global_map[gk]
            out[k] = (gx + shift_x, gy + shift_y)
    return out

def build_plate_body(grid_tiles, solid_name, shift_x=0.0, shift_y=0.0):
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

    z_inner = z1 + INNER_TILE_HEIGHT
    platform_count = 0
    for (cx, cy) in grid_tiles:
        inner_corners = get_hex_corners(cx, cy, INNER_TILE_WIDTH)
        itop = [gv(x, y, z_inner) for x, y in inner_corners]
        try: bm.faces.new(itop)
        except ValueError as e: print(f"  ⚠ inner top FAILED at ({cx:.1f},{cy:.1f}): {e}")
        # No cap at z1 (INNER_TILE_WIDTH boundary) here on purpose: the
        # platform sits directly on top of solid base-plate material
        # (the base plate's own z1 surface is already fully closed by
        # the outer-hex-to-inner-platform "shelf" faces below), so this
        # boundary is a place where material continues upward through
        # inner_side, not a real surface needing its own cap. Building
        # one anyway created a genuine 3-faces-per-edge non-manifold
        # ring around every single platform, in every quadrant, since
        # the very first build -- confirmed by the fact that every
        # quadrant's very first "N non-manifold edges" report (right
        # after build_plate_body, before any cuts) exactly equals
        # tile_count * 6 (the six inner-platform edges per tile).
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
                continue
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
    # verbose=True prints exactly what mesh.validate() finds/fixes (duplicate
    # faces, invalid loops, etc) to the console -- silently swallowing that
    # info (the previous bare mesh.validate()) meant a genuinely broken
    # build could get "corrected" here without ever showing up in the log,
    # which is exactly the kind of thing that could explain TR/BR-only
    # boolean failures further downstream while TL/BL's log looks identical.
    was_invalid = mesh.validate(verbose=True)
    if was_invalid:
        print(f"  ⚠ {solid_name}: mesh.validate() found and corrected invalid geometry (see warnings above)")
    mesh.update()

    nm, za = report_manifold_stats(obj)
    print(f"  {solid_name}: {exterior_edge_count} true exterior edges, "
          f"{end_caps_added} end caps, {platform_count} inner platforms, "
          f"{nm} non-manifold edges, {za} zero-area faces")
    return obj

def make_wire_hole_cutter(name, cx, cy):
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

def make_rod_hole_cutter(name, y_center, z_center, length=2000.0, radius=None):
    radius = ROD_HOLE_RADIUS if radius is None else radius
    print(f"    Rod hole at Y={y_center:.3f}, Z={z_center:.3f} (⌀{2*radius:.1f}mm, along X)")

    mesh=bpy.data.meshes.new(name+"_mesh")
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bm=bmesh.new()
    segs=32
    half=length/2.0
    bv,tv=[],[]

    for i in range(segs):
        a=2*math.pi*i/segs
        yo=radius*math.cos(a)
        zo=radius*math.sin(a)
        bv.append(bm.verts.new((-half,yo,zo)))
        tv.append(bm.verts.new((half,yo,zo)))

    for i in range(segs):
        j=(i+1)%segs
        bm.faces.new([bv[i],bv[j],tv[j],tv[i]])
    bm.faces.new(list(reversed(bv)))
    bm.faces.new(tv)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    obj.location=Vector((0.0, y_center, z_center))
    return obj

def make_hex_pocket_cutter(name, y_center, z_center, across_flats, length=2000.0):
    """Same shape/coordinate convention as make_rod_hole_cutter (local X
    spans -half..+half, cross-section in Y-Z, obj.location places it in
    world space) but a regular hexagon instead of a circle -- for a nut
    trap that keys against the nut's own flats (so it can't spin) rather
    than a round bore. Corner angles follow the same 30+60*i convention
    get_hex_corners uses elsewhere in this file.

    Each end cap is built as a triangle fan from a center vertex, not a
    single 6-gon: the W3 nut-seat pocket's inner cap lands inside solid
    material (a blind cut, not a through-hole), and a lone N-gon cap
    landing inside solid is exactly what the EXACT solver couldn't
    resolve for the earlier round nut-seat cutter (25/32 cutter verts
    leaking into the result) until triangulated after the fact -- doing
    it as a fan from the start avoids needing that post-hoc pass.
    recalc_face_normals is still run explicitly (not just normal_update,
    which only recomputes vectors from whatever winding already exists):
    for a convex solid like this prism there's no ambiguous concave
    region to trip up the flood-fill, so it reliably finds the true
    outward orientation, same reasoning as the corner-fill wedge."""
    circumradius = across_flats / math.sqrt(3)
    print(f"    Hex pocket at Y={y_center:.3f}, Z={z_center:.3f} "
          f"({across_flats:.1f}mm across flats, along X)")

    mesh=bpy.data.meshes.new(name+"_mesh")
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bm=bmesh.new()
    segs=6
    half=length/2.0
    bv,tv=[],[]

    for i in range(segs):
        a=math.radians(30 + 60*i)
        yo=circumradius*math.cos(a)
        zo=circumradius*math.sin(a)
        bv.append(bm.verts.new((-half,yo,zo)))
        tv.append(bm.verts.new((half,yo,zo)))

    for i in range(segs):
        j=(i+1)%segs
        bm.faces.new([bv[i],bv[j],tv[j],tv[i]])

    bc = bm.verts.new((-half, 0.0, 0.0))
    tc = bm.verts.new((half, 0.0, 0.0))
    for i in range(segs):
        j=(i+1)%segs
        bm.faces.new([bc, bv[j], bv[i]])
        bm.faces.new([tc, tv[i], tv[j]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    obj.location=Vector((0.0, y_center, z_center))
    return obj

def _extrude_profile_along_z(bm, profile_xy, z0, z1):
    """Extrudes a closed 2D profile (list of (x,y) points, in order) along
    Z from z0 to z1 into a closed solid prism. Unlike
    _extrude_profile_along_y (defined further below, for the L/R rail
    tabs), winding here doesn't need to be hand-verified per face: the
    W2/W3 fit-boss profile this builds is convex, so recalc_face_normals'
    flood-fill reliably finds the true outward orientation regardless of
    which way these faces wind -- same reasoning make_hex_pocket_cutter
    above already relies on for its own convex prism."""
    bottom = [bm.verts.new((x, y, z0)) for x, y in profile_xy]
    top = [bm.verts.new((x, y, z1)) for x, y in profile_xy]
    n = len(profile_xy)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bottom[i], bottom[j], top[j], top[i]])
    bm.faces.new(bottom)
    bm.faces.new(list(reversed(top)))

def make_profile_cutter_z(name, profile_xy, z0, z1):
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    _extrude_profile_along_z(bm, profile_xy, z0, z1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    return obj

def make_rod_hole_cutter_y(name, x_center, z_center, length=2000.0):
    print(f"    Rod hole at X={x_center:.3f}, Z={z_center:.3f} (⌀{ROD_HOLE_DIAMETER:.1f}mm, along Y)")

    mesh=bpy.data.meshes.new(name+"_mesh")
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bm=bmesh.new()
    segs=32
    half=length/2.0
    bv,tv=[],[]

    for i in range(segs):
        a=2*math.pi*i/segs
        xo=ROD_HOLE_RADIUS*math.cos(a)
        zo=ROD_HOLE_RADIUS*math.sin(a)
        bv.append(bm.verts.new((xo,-half,zo)))
        tv.append(bm.verts.new((xo,half,zo)))

    for i in range(segs):
        j=(i+1)%segs
        bm.faces.new([bv[i],bv[j],tv[j],tv[i]])
    bm.faces.new(list(reversed(bv)))
    bm.faces.new(tv)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    obj.location=Vector((x_center, 0.0, z_center))
    return obj

def make_canal_cutter(name, x_start, x_end, y_center, z_start, z_end):
    print(f"    Canal X={x_start:.3f}..{x_end:.3f}, Y={y_center:.3f} (width {CANAL_WIDTH:.1f}mm), "
          f"Z={z_start:.1f}..{z_end:.1f}mm")
    half_w = CANAL_WIDTH / 2.0
    corners = [
        (x_start, y_center - half_w),
        (x_end,   y_center - half_w),
        (x_end,   y_center + half_w),
        (x_start, y_center + half_w),
    ]

    mesh=bpy.data.meshes.new(name+"_mesh")
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bm=bmesh.new()
    bv=[bm.verts.new((x,y,z_start)) for x,y in corners]
    tv=[bm.verts.new((x,y,z_end)) for x,y in corners]
    n=len(corners)
    for i in range(n):
        j=(i+1)%n
        bm.faces.new([bv[i],bv[j],tv[j],tv[i]])
    bm.faces.new(list(reversed(bv)))
    bm.faces.new(tv)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
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

def report_self_intersections(obj):
    """Finds pairs of faces that geometrically overlap in 3D space
    without sharing a vertex -- i.e. the mesh crosses through itself.
    A solid can be individually 'clean' by every check above (0
    non-manifold edges, 0 zero-area faces, validate() finds nothing)
    and STILL be self-intersecting, since none of those checks look at
    whether two unrelated faces occupy the same space. A boolean
    solver's inside/outside classification can go wrong specifically
    near a self-intersection -- which would explain a DIFFERENCE cut
    reporting "success" while actually leaving cutter geometry fused
    into the result, exactly the TR/BR-only symptom seen so far. Only
    non-adjacent face pairs (no shared vertex) count -- faces that
    share an edge or corner always technically 'touch' there, that's
    normal mesh connectivity, not a self-intersection."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm, epsilon=0.0)
    overlaps = bvh.overlap(bvh)
    bad = set()
    for i, j in overlaps:
        if i == j:
            continue
        fi, fj = bm.faces[i], bm.faces[j]
        shared = {v.index for v in fi.verts} & {v.index for v in fj.verts}
        if shared:
            continue
        bad.add(tuple(sorted((i, j))))
    if bad:
        print(f"  ⚠ {obj.name}: {len(bad)} self-intersecting face pair(s) found")
        for i, j in list(bad)[:10]:
            ci = bm.faces[i].calc_center_median()
            cj = bm.faces[j].calc_center_median()
            print(f"      face {i} (center {ci.x:.1f},{ci.y:.1f},{ci.z:.1f}) "
                  f"x face {j} (center {cj.x:.1f},{cj.y:.1f},{cj.z:.1f})")
    else:
        print(f"  {obj.name}: no self-intersecting faces found")
    bm.free()
    return len(bad)

def mesh_volume(obj):
    """Actual enclosed volume (mm^3) -- unlike vertex/face counts or the
    non-manifold check, this can't be fooled by a topologically 'clean'
    result that didn't remove the material it was supposed to. A real
    full-length rod tunnel removes pi*r^2*(length through solid); two
    disconnected surface notches remove only a sliver of that."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    vol = bm.calc_volume(signed=False)
    bm.free()
    return vol

def duplicate_obj(obj, name):
    new_data = obj.data.copy()
    new_obj = bpy.data.objects.new(name, new_data)
    new_obj.matrix_world = obj.matrix_world.copy()
    bpy.context.collection.objects.link(new_obj)
    return new_obj

def do_diff(target, cutter, solver='EXACT', operation='DIFFERENCE'):
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active=target
    mod=target.modifiers.new("Diff",'BOOLEAN')
    mod.operation=operation
    mod.object=cutter
    mod.solver=solver
    try:
        bpy.ops.object.modifier_apply(modifier="Diff")
        return True
    except Exception as e:
        print(f"      failed ({solver} {operation}): {e}")
        try: target.modifiers.remove(mod)
        except: pass
        return False

def cutter_leaked_into_result(cutter, result_obj):
    cutter_positions = {(round(v.co.x,3), round(v.co.y,3), round(v.co.z,3))
                         for v in cutter.data.vertices}
    result_positions = {(round(v.co.x,3), round(v.co.y,3), round(v.co.z,3))
                         for v in result_obj.data.vertices}
    leaked = cutter_positions & result_positions
    return len(leaked) > 0, len(leaked), leaked

def try_cut_on_copy(target, cutter, solver, operation='DIFFERENCE'):
    """Returns (ok, delta_nm, delta_za, dup, abs_nm, abs_za) -- the delta
    is relative to `target`'s own state going in, but abs_nm/abs_za are
    the FINAL non-manifold/zero-area counts on the result itself. A
    delta of 0 only means this particular operation didn't make things
    WORSE than whatever `target` already was -- it says nothing about
    whether `target` was already broken. safe_cut below picks/reports
    based on the absolute counts for that reason.

    The cutter_leaked_into_result check only applies to DIFFERENCE: for
    a UNION, part of the cutter's own geometry legitimately surviving
    unchanged in the result (whatever portion didn't overlap the
    target) is the expected, correct outcome, not a sign of failure --
    so that check is skipped for any other operation."""
    nm0, za0 = report_manifold_stats(target)
    dup = duplicate_obj(target, target.name + "_TRY")
    ok = do_diff(dup, cutter, solver=solver, operation=operation)
    if not ok:
        bpy.data.objects.remove(dup, do_unlink=True)
        return False, None, None, None, None, None
    nm1, za1 = report_manifold_stats(dup)
    if operation == 'DIFFERENCE':
        leaked, leak_count, leaked_positions = cutter_leaked_into_result(cutter, dup)
        # A leaked-position match by itself is NOT proof of corruption: a
        # cutter corner landing deep inside uniform material legitimately
        # becomes the new cavity's own corner at that exact coordinate --
        # confirmed on the fit-tab slot cut (SensorBase_TR/BR): after
        # fixing _extrude_profile_along_y's inward-normal bug, the result
        # there is genuinely clean (0 non-manifold edges, 0 zero-area
        # faces, mesh.validate() clean, removed volume matching the
        # cutter's own volume) yet this check still flagged the exact
        # same corner as "leaked", because it only compares raw
        # coordinates. Only escalate to the corruption penalty when the
        # leak is ACCOMPANIED by a real regression (more non-manifold
        # edges or zero-area faces than the target already had) -- that
        # combination is what actually distinguishes a genuinely fused-in
        # cutter (e.g. the still-unresolved TR/BR canal cuts) from a
        # clean cut that merely shares a coordinate with the cutter.
        if leaked and (nm1 > nm0 or za1 > za0):
            all_cutter_verts = sorted({(round(v.co.x,3), round(v.co.y,3), round(v.co.z,3))
                                        for v in cutter.data.vertices})
            print(f"      {solver}: boolean reported success but {leak_count} cutter "
                  f"vertices leaked into the result — treating as failed")
            print(f"        leaked positions: {sorted(leaked_positions)}")
            print(f"        full cutter vertex set (all {len(all_cutter_verts)}): {all_cutter_verts}")
            nm1 = nm0 + 1000
        elif leaked:
            print(f"      {solver}: {leak_count} cutter vertex position(s) coincide with the "
                  f"result but non-manifold/zero-area counts show no regression — treating as a "
                  f"clean cut, not corruption")
            print(f"        coincident positions: {sorted(leaked_positions)}")
    print(f"      {solver}: non-manifold edges: {nm1-nm0} (total now {nm1}), "
          f"zero-area faces: {za1-za0} (total now {za1})")
    return True, nm1 - nm0, za1 - za0, dup, nm1, za1

def safe_cut(label, target, cutter, primary='EXACT', operation='DIFFERENCE'):
    verb = "Cutting" if operation == 'DIFFERENCE' else "Unioning"
    past = "cut" if operation == 'DIFFERENCE' else "unioned"
    print(f"    {verb} {label}...")
    alt = 'FLOAT' if primary == 'EXACT' else 'EXACT'
    ok1, _, _, dup1, nm1, za1 = try_cut_on_copy(target, cutter, primary, operation=operation)
    if ok1 and nm1 == 0 and za1 == 0:
        target.data = dup1.data
        bpy.data.objects.remove(dup1, do_unlink=True)
        print(f"    ✓ {label} {past} cleanly with {primary}")
        return True
    ok2, _, _, dup2, nm2, za2 = try_cut_on_copy(target, cutter, alt, operation=operation)
    candidates = []
    if ok1: candidates.append((nm1 + za1, primary, dup1, nm1, za1))
    if ok2: candidates.append((nm2 + za2, alt, dup2, nm2, za2))
    if not candidates:
        print(f"    ⚠ {label}: both solvers failed — material NOT modified")
        return False
    candidates.sort(key=lambda c: c[0])
    best_score, best_solver, best_dup, best_nm, best_za = candidates[0]
    # A score >=1000 means every candidate hit the leaked-vertex penalty
    # (see try_cut_on_copy) -- i.e. every solver produced a result that's
    # definitionally corrupt (the cutter's own geometry partially fused
    # in instead of being subtracted/merged), not just "a bit messy".
    # Previously this still got applied as the "least-bad" option,
    # which is how a target could end up silently carrying broken
    # geometry -- visible as something odd in the viewport, but not a
    # real, sliceable cavity/tab once exported. Refusing to apply here
    # leaves target exactly as it was (missing this one feature) rather
    # than corrupting an otherwise-good mesh.
    if best_score >= 1000:
        print(f"    ⚠ {label}: every solver produced corrupted geometry "
              f"(cutter vertices leaked) — material NOT modified")
        for _, _, d, _, _ in candidates:
            bpy.data.objects.remove(d, do_unlink=True)
        return False
    target.data = best_dup.data
    for _, _, d, _, _ in candidates:
        if d is not best_dup:
            bpy.data.objects.remove(d, do_unlink=True)
    bpy.data.objects.remove(best_dup, do_unlink=True)
    if best_score > 0:
        print(f"    ⚠ {label}: cleanest available ({best_solver}) still has "
              f"{best_nm} non-manifold edges, {best_za} zero-area faces")
    else:
        print(f"    ✓ {label} {past} cleanly with {best_solver}")
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
def ensure_consistent_normals(obj):
    """Runs Blender's own edit-mode 'Recalculate Normals Outside' on
    obj. build_plate_body already calls bmesh.ops.recalc_face_normals,
    but that's a flood-fill from one seed face with no guaranteed
    "outward" reference -- it only makes normals mutually CONSISTENT,
    not necessarily all pointing out of the solid. Investigating why
    canal/slot cuts have reported "boolean succeeded but cutter
    vertices leaked into the result" on SensorBase_TR/BR specifically
    -- and only there, never TL/BL, even using the literal same cutter
    object against both in the same cut -- ruled out the cutter's own
    geometry entirely (same object, different result depending only on
    which target it's applied to). TR/BR's mesh is a genuinely
    different, partly-mirrored topology from TL/BL (confirmed
    separately: R02/R07, each centered exactly on the quadrant split,
    end up with some of their own edges using a simplified flat-wall
    fallback that reaches into the neighboring quadrant's territory) --
    a plausible way for a same-mesh-consistent-but-inward flood fill
    to happen is exactly this kind of topology, and inverted normals
    are a well-known cause of a boolean solver's inside/outside test
    going wrong in precisely this "reports success, partially fuses
    the cutter in" way. The operator-based normals_make_consistent
    (what "Recalculate Normals Outside" in the Mesh menu runs) uses a
    more robust outward test than the bmesh.ops flood fill, so this is
    cheap, safe insurance to run right after every quadrant is built,
    before any cuts touch it."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def build_side(tiles, solid_name, shift_x=0.0, shift_y=0.0):
    grid_tiles = [(cx, cy) for (tag, cx, cy) in tiles]
    print(f"\n{'='*60}")
    print(f"Building {solid_name} with {len(grid_tiles)} tiles")
    print(f"{'='*60}")

    obj = build_plate_body(grid_tiles, solid_name, shift_x, shift_y)
    ensure_consistent_normals(obj)
    report_self_intersections(obj)

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
# (unchanged from before — this is the ORIGINAL build order, nothing
# reordered around it)
tl_obj = build_side(tl_tiles, "SensorBase_TL", shift_x=0.0, shift_y=ROW_SPLIT_MARGIN)
tr_obj = build_side(tr_tiles, "SensorBase_TR", shift_x=GAP_BETWEEN_PLATES, shift_y=ROW_SPLIT_MARGIN)
bl_obj = build_side(bl_tiles, "SensorBase_BL", shift_x=0.0, shift_y=-ROW_SPLIT_MARGIN)
br_obj = build_side(br_tiles, "SensorBase_BR", shift_x=GAP_BETWEEN_PLATES, shift_y=-ROW_SPLIT_MARGIN)

quadrant_objs = [tl_obj, tr_obj, bl_obj, br_obj]

# ============================================================
# W2/W3 corner-bridging panel (Option A -- seamless, mitered
# wall-outer footprint). Fills the exterior corner pocket bounded by
# wall segments W2 (TL, L02: A2->C), W3 (BL, L04: C->B3), and the new
# outer "green" diagonal A2->B3. Merged directly into the BL mesh (the
# shared corner C and W3 are BL territory), NO boolean -- the same
# direct-bmesh pattern merge_rail_into_wall uses. Built HERE, right
# after the four quadrants are assembled and BEFORE the rod-hole /
# canal / rail / tab cuts run, so every cutter that passes through
# this corner region (the X-axis L04-R06 rod tunnel at Y~-56, the
# L04-R06 canal) drills through the complete solid including the wedge,
# leaving no thread/canal blockages.
#
# Footprint = the wall-thickness wedge OUTWARD of the wall corner, with
# plan vertices A2_wo / C_wo / B3_wo (GLOBAL_WALL_OFFSET of the raw
# corners -- Option A). Extruded Z = 0 .. PLATE_H+WALL_HEIGHT (46mm).
# The C_wo->B3_wo edge coincides with BL's OWN existing W3 wall outer
# face -- that face is KEPT as the wedge's shared inner boundary and
# the prism welds onto those existing edge vertices via remove_doubles
# (no duplicate coincident face built, per the rail-merge lesson). The
# A2_wo->C_wo edge (W2, TL territory -- no face in BL) and the green
# A2_wo->B3_wo diagonal are purely new faces on the BL print.
# ============================================================
def merge_corner_fill(near_obj, near_shift_x, near_shift_y, a2_raw, c_raw, b3_raw):
    """Generic version of the original merge_corner_fill_into_bl --
    parameterized on which object receives the wedge (near_obj, the one
    owning the C/B3-side wall segment) and which raw corner triple
    defines the wedge, instead of hardcoding bl_obj and the W1/W2
    corner constants. Body is otherwise byte-for-byte the same logic,
    so calling this with the original W2/W3 constants on bl_obj
    reproduces the original geometry exactly."""
    print(f"\n{'='*60}")
    print(f"Adding corner-bridging panel (filled triangle wedge, {near_obj.name} mesh)")
    print(f"{'='*60}")

    # Option A: use GLOBAL_WALL_OFFSET (the wall's own mitered outer
    # surface) so the new faces merge flush with the surrounding wall.
    pa = GLOBAL_WALL_OFFSET.get(_vkey(a2_raw), a2_raw)
    pc = GLOBAL_WALL_OFFSET.get(_vkey(c_raw), c_raw)
    pb = GLOBAL_WALL_OFFSET.get(_vkey(b3_raw), b3_raw)
    print(f"  wall_outer A2={pa} C={pc} B3={pb}")

    # near_obj-local frame (the mesh was built with near_shift_x/near_shift_y).
    pa = (round(pa[0] + near_shift_x, 4), round(pa[1] + near_shift_y, 4))
    pc = (round(pc[0] + near_shift_x, 4), round(pc[1] + near_shift_y, 4))
    pb = (round(pb[0] + near_shift_x, 4), round(pb[1] + near_shift_y, 4))
    print(f"  {near_obj.name}-local  A2={pa} C={pc} B3={pb}")

    z0 = 0.0
    z2 = PLATE_H + WALL_HEIGHT   # 46.0

    bm = bmesh.new()
    bm.from_mesh(near_obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    vmap = {}
    def gv(x, y, z):
        k = (round(x, 3), round(y, 3), round(z, 3))
        if k not in vmap:
            vmap[k] = bm.verts.new((x, y, z))
        return vmap[k]

    # Vertices of the triangular prism (z0 bottom, z2 top).
    a0 = gv(pa[0], pa[1], z0); a2 = gv(pa[0], pa[1], z2)
    c0 = gv(pc[0], pc[1], z0); c2 = gv(pc[0], pc[1], z2)
    b0 = gv(pb[0], pb[1], z0); b2 = gv(pb[0], pb[1], z2)

    # Note: no new face on the C->B vertical plane -- near_obj's existing
    # wall-outer face already occupies it (shared inner boundary).
    candidates = [
        [a2, c2, b2],              # top face        (z=z2)
        [b0, c0, a0],              # bottom face     (z=z0)
        [a0, c0, c2, a2],          # A->C side       (toward the boss's own wall)
        [a2, b2, b0, a0],          # A->B green diagonal side
    ]
    built = 0
    for f in candidates:
        try:
            bm.faces.new(f)
            built += 1
        except ValueError as e:
            print(f"  ⚠ face skipped {e}")

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)

    # The old wall face (the quad at C->B3, X=pc[0]==pb[0]) is now
    # fully interior -- solid on both sides, since the wedge fills what
    # used to be void beyond it. Left in place it's a redundant internal
    # membrane: any later boolean cutter that crosses this region (a
    # rod tunnel, the nut-seat counterbore) also has to cut a hole
    # through this buried face, which the EXACT solver cannot resolve
    # cleanly -- confirmed empirically (a fresh boolean cut through here
    # produced dozens of new non-manifold edges, all exactly at this
    # face's X, even though the cut through the real exterior boundary
    # elsewhere was clean). Dissolve it so the old wall and the new
    # wedge become one seamless solid instead of two volumes sharing a
    # buried partition.
    bm.faces.ensure_lookup_table()
    _old_wall_key = frozenset([
        (round(pc[0], 3), round(pc[1], 3), round(z0, 3)),
        (round(pb[0], 3), round(pb[1], 3), round(z0, 3)),
        (round(pb[0], 3), round(pb[1], 3), round(z2, 3)),
        (round(pc[0], 3), round(pc[1], 3), round(z2, 3)),
    ])
    _old_wall_faces = []
    for f in bm.faces:
        if len(f.verts) == 4:
            fkey = frozenset((round(v.co.x, 3), round(v.co.y, 3), round(v.co.z, 3)) for v in f.verts)
            if fkey == _old_wall_key:
                _old_wall_faces.append(f)
    if _old_wall_faces:
        # dissolve_faces is for merging a face into an ADJACENT coplanar
        # neighbor across a shared edge -- this face has no such
        # neighbor (its "other side" is the wedge, added as a separate,
        # non-coplanar prism), so dissolve_faces silently no-ops on it.
        # delete(..., context='FACES') removes just the face itself
        # (keeping its edges/verts, still shared with the wedge and the
        # rest of the wall), which is what's actually needed here.
        bmesh.ops.delete(bm, geom=_old_wall_faces, context='FACES')
        print(f"  Deleted {len(_old_wall_faces)} old, now-buried wall face(s) -- wedge merged into one solid")
    else:
        print("  ⚠ old wall face not found to delete -- corner fill may leave a redundant internal wall")

    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(near_obj.data)
    bm.free()
    near_obj.data.update()

    ensure_consistent_normals(near_obj)
    nm, za = report_manifold_stats(near_obj)
    si = report_self_intersections(near_obj)
    print(f"  Corner fill merged into {near_obj.name}: "
          f"{built} new faces, {nm} non-manifold edges, {za} zero-area faces, "
          f"{si} self-intersections")
    return near_obj, pa, pc, pb

# ---- Nut-seat counterbore -- a rod hole along this row is only
# ROD_HOLE_DIAMETER wide, and the corner-fill wedge pushes the target's
# true outer surface out past the wedge's slanted A2->B3 diagonal face
# (non-perpendicular to the rod axis, and adjoining the non-manifold
# edges the corner-fill merge reports) -- in the viewport that thin rod
# bore visibly stops short at the old wall face instead of reaching
# this new outer face, leaving the rod tip buried. Rather than chase
# the exact boolean behavior on that slanted/non-manifold face with the
# 7mm bore, cut a wide, flat-bottomed nut-seat pocket from the wedge's
# real outer face straight down to (and past) where the rod tip will
# land -- big enough in diameter to swallow whatever sliver the thin
# bore would otherwise leave behind, giving a flat face to seat a nut
# on the threaded rod.
#
# Cut BEFORE the X-axis rod holes (not after): this pocket spans the
# same X range the thin rod-hole cutter will later travel through.
# Cutting the wide pocket into still-solid, unbroken material first
# keeps its inner end-cap a plain fan in uniform solid; the thin
# rod-hole cutter then just passes harmlessly through the already-
# hollow pocket afterward. Doing it in the other order (thin hole
# first) made the wide cutter's inner cap straddle the boundary of the
# thin hole's pre-existing bore -- a partial annulus the EXACT solver
# couldn't resolve (25-64 cutter vertices leaked into the result on
# both EXACT and FLOAT, non-manifold edges exploding to 1000+).
#
# Hex, not round: a plain cylindrical bore lets the nut spin freely
# when the rod is tightened, so this is a proper nut TRAP, keyed to the
# actual nut's own flats (11.5mm across flats) via make_hex_pocket_cutter
# -- see that function for why each end cap is built as a triangle fan
# rather than a single hexagon face.
NUT_SEAT_ACROSS_FLATS = 11.5   # the actual nut's wrench size
NUT_SEAT_DEPTH = 5.5           # the actual nut's thickness, measured from
                                 # the wedge's outer face at the pocket's
                                 # own center Y -- back to just the nut.
NUT_SEAT_CIRCUMRADIUS = NUT_SEAT_ACROSS_FLATS / math.sqrt(3)   # 6.64mm
NUT_SEAT_OUTSIDE_MARGIN = 4.0    # extra reach out past the wedge face, into
                                  # open air. This cutter is a hollow tube
                                  # (side wall + end caps), and the same
                                  # "carried" behavior noted on the X-axis
                                  # rod cutters applies here too -- the
                                  # portion of the cutter sitting in open
                                  # air isn't always a no-op; its own
                                  # surface can survive as a visible
                                  # floating stub past the real wall face.
                                  # 4.0mm clears the slanted wedge face's
                                  # own worst-case thickness across the hex
                                  # pocket's full footprint -- a bigger
                                  # reach than float-precision alone would
                                  # need, but still a small, deliberate
                                  # margin measured against real geometry.

def build_nut_trap(target_obj, tunnel_y, wedge_a2, wedge_b3):
    print(f"\n{'='*60}")
    print(f"Cutting nut-trap pocket on {target_obj.name} "
          f"({NUT_SEAT_ACROSS_FLATS:.1f}mm across flats x {NUT_SEAT_DEPTH:.1f}mm deep hex)")
    print(f"{'='*60}")

    tunnel_z = ROD_HOLE_Z_X_AXIS
    # Same A2->B3 diagonal the corner-fill wedge built, evaluated at the
    # rod tunnel's Y, to find the wedge's true outer face there.
    t = (tunnel_y - wedge_a2[1]) / (wedge_b3[1] - wedge_a2[1])
    face_x = wedge_a2[0] + t * (wedge_b3[0] - wedge_a2[0])
    print(f"  Wedge outer face at Y={tunnel_y:.3f}: X={face_x:.3f}")

    # Inward (into solid material) always points back toward the tray's
    # own center (X~=0); outward (into open air) points away from it,
    # toward whichever extreme X this wedge sits at. The original west
    # wedge always has a NEGATIVE face_x, so inward = +X (matches the
    # original fixed "+NUT_SEAT_DEPTH / -NUT_SEAT_OUTSIDE_MARGIN"
    # formula exactly). A mirrored EAST wedge has a POSITIVE face_x, so
    # inward = -X instead -- reusing the west's fixed sign unmodified
    # there would cut the pocket the wrong way (into open air instead
    # of into material). Deriving the sign from face_x itself keeps
    # this correct on whichever side calls it, with no extra parameter
    # needed.
    inward_sign = 1.0 if face_x < 0 else -1.0

    inner_x = face_x + inward_sign * NUT_SEAT_DEPTH        # deep, measured
                                                             # from the real wall face
    outer_x = face_x - inward_sign * NUT_SEAT_OUTSIDE_MARGIN  # into open air, harmless
    length = abs(inner_x - outer_x)
    center_x = (inner_x + outer_x) / 2.0
    print(f"  Pocket spans X={min(outer_x, inner_x):.3f} .. {max(outer_x, inner_x):.3f} "
          f"(cutter length={length:.3f}, center X={center_x:.3f})")

    cutter = make_hex_pocket_cutter(
        f"Hole_NutSeat_{target_obj.name}", tunnel_y, tunnel_z,
        across_flats=NUT_SEAT_ACROSS_FLATS, length=length)
    cutter.location.x = center_x
    apply_transforms(cutter)
    safe_cut(f"nut-trap pocket on {target_obj.name}", target_obj, cutter, primary='EXACT')
    bpy.data.objects.remove(cutter, do_unlink=True)

# ============================================================
# Vertical fit boss/socket -- a trapezoidal peg on the "boss" object,
# protruding from its own wall-outer face at the wall's midpoint, that
# plugs into a matching socket cut into the "socket" object's own
# corner-fill wedge (the "A->C side" face merge_corner_fill built
# directly across the print gap -- tagged "toward the boss's own wall"
# in that function's own face-candidate comment, and already fused
# into one solid with the wedge's own wall there). Registers the boss
# object against the socket object at this seam, same purpose the
# top/bottom rail fit-tabs serve for TL/TR and BL/BR.
#
# Protrusion direction is along world Y specifically, not the wall's
# own (diagonal) outward normal: Y is the ONLY real separation between
# the two prints (a rigid +-ROW_SPLIT_MARGIN shift, 6mm total, closed
# by the same-axis nudge at the very end of this script), so a straight
# Y push is exactly the physical assembly motion. The trapezoid's
# "width" axis runs along the wall's own tangent (A2->C direction)
# instead.
#
# Unlike the rail tabs (a horizontal cantilever off a FLAT rail,
# needing a 45-degree Z-ramp to print without support), this boss
# spans the wall's FULL height, Z=0..PLATE_H+WALL_HEIGHT (46mm) --
# constant cross-section the whole way, starting right at the print
# bed, so every layer is fully backed by the layer below it from the
# very first one. No ramp needed; the taper instead lives in the X-Y
# plan view (wide where it's rooted in the wall, narrower at the tip)
# for a keyed, self-centering fit as it's pushed straight in along Y.
# ============================================================
FIT_BOSS_WIDTH_BASE = 15.0    # trapezoid width (along the wall's own tangent), at
                                # the end rooted inside the boss object's existing
                                # wall -- per your ask (15mm wide x 6mm deep)
FIT_BOSS_WIDTH_TIP = 7.5      # trapezoid width at the tip (deepest into the
                                # socket object) -- kept at half the base width,
                                # same taper ratio as the original 14/7mm design
FIT_BOSS_DEPTH = 6.0          # protrusion depth from the boss object's own
                                # wall-outer face, along the wall's true normal
FIT_BOSS_ROOT_OVERLAP = 5.0   # the wide end extends this far the OTHER way
                                # (back into the boss object's existing wall)
                                # past the wall face -- a genuine volumetric
                                # overlap for the union to resolve, same
                                # reasoning as TAB_UNION_OVERLAP_X. Confirmed
                                # (standalone probe) a push of this size still
                                # lands inside the wall's own 6mm thickness
                                # here, not through its inner face. Raised
                                # from 3.0 to 5.0 to push the boss's wide
                                # root end further back into the wall so the
                                # union's material fully covers/flushes with
                                # the socket's mouth opening on the other
                                # side, closing a visible triangular sliver
                                # at the seam.
FIT_SOCKET_CLEARANCE = 0.15   # per-side clearance, ~0.3mm total gap -- 0.25
                                # (0.5mm total) measured correct per
                                # breakpoint diagnostic but read visually
                                # oversized; 0.15 is a tighter friction-fit
                                # starting point, tune printer-side if
                                # needed.
FIT_SOCKET_EXTRA_DEPTH = 0.2  # socket cut this much deeper than the boss's
                                # own travel, so the tip never bottoms out --
                                # lowered from 2.0: ruler-measured in Blender
                                # at ~2.06mm, confirming this margin (not a
                                # defect) was the visible gap past the boss's
                                # tip; 0.2 shrinks it while still leaving
                                # room so the tip doesn't bottom out.
FIT_SOCKET_OPEN_MARGIN = 0.0  # lowered from 0.15 -- the socket's mouth
                                 # should open exactly at the wall face,
                                 # not past it, so there's no visible
                                 # cavity edge beyond where the boss's
                                 # root actually sits.
FIT_Z_OVERSHOOT = 2.0   # the boss/socket cap faces would otherwise land
                          # EXACTLY on the wall's own existing Z=0/Z=46
                          # faces -- confirmed in-engine (isolated test
                          # against duplicates of TL/BL): that produced 10
                          # non-manifold edges on EACH side, every one of
                          # them sitting exactly at Z=0.000 or Z=46.000, the
                          # same duplicate-coincident-face problem
                          # merge_rail_into_wall's own comment describes.
                          # Overshooting past both ends instead (never
                          # landing exactly ON a real boundary) is the same
                          # fix already used everywhere else in this file
                          # (TAB_UNION_OVERLAP_X, NUT_SEAT_OUTSIDE_MARGIN).
                          # 0.5mm was enough for the original pure-Y-depth
                          # design; once the profile was rotated below (depth
                          # along the wall's true normal instead of Y), the
                          # boss's leg edges cross the wall's own Z=0/Z=46
                          # boundary at a shallower angle and 0.5mm started
                          # producing 23 non-manifold edges again (all at the
                          # overshoot planes) -- 2.0mm re-tested clean (0
                          # non-manifold, 0 zero-area, 0 self-intersections).
FIT_U_OFFSET = 10.0   # shifts the boss/socket feature 10mm along the
                        # wall's own tangent direction, toward each wall's
                        # own C-side corner (away from the A2-side corner)
                        # -- confirmed correct on the west seam (moved
                        # toward corner C, the intended side, after an
                        # earlier -10 attempt landed on the wrong side and
                        # was rolled back). This SAME +10.0 value produces
                        # the mirror-symmetric placement on the east seam
                        # too, with no sign flip needed: build_fit_boss_socket
                        # derives the tangent from EACH call's own
                        # (a2_raw, c_raw) pair, and the east pair's tangent
                        # is already the X-mirror of the west pair's (its
                        # own A2->C direction points the opposite way in X)
                        # -- so the same +10.0 offset naturally moves the
                        # east feature toward ITS OWN C-side corner too,
                        # exactly mirroring the west placement.

def _fit_trapezoid_profile(cx, cy, tx, ty, nx, ny, width_top, width_bottom, depth_top, depth_bottom):
    """(cx,cy) is the wall-face midpoint; (tx,ty) the wall's own unit
    tangent (width axis -- keeps the base/tip edges parallel to the wall);
    (nx,ny) the wall's own true outward normal (depth axis -- keeps the
    peg's own base->tip axis perpendicular to the wall)."""
    top_l = (cx - tx*width_top/2.0    + nx*depth_top,    cy - ty*width_top/2.0    + ny*depth_top)
    top_r = (cx + tx*width_top/2.0    + nx*depth_top,    cy + ty*width_top/2.0    + ny*depth_top)
    bot_r = (cx + tx*width_bottom/2.0 + nx*depth_bottom, cy + ty*width_bottom/2.0 + ny*depth_bottom)
    bot_l = (cx - tx*width_bottom/2.0 + nx*depth_bottom, cy - ty*width_bottom/2.0 + ny*depth_bottom)
    return [top_l, top_r, bot_r, bot_l]

def _fit_wall_frame(pa, pc, shift_y, interior_ref=(0.0, 0.0)):
    """A FIXED -90deg rotation of the tangent (the original formula)
    only picks the true outward direction for ONE chirality of
    (a2_raw, c_raw) winding. Mirroring a wall to the opposite side of
    the tile grid (e.g. the east seam, a reflection of the west one)
    reverses that chirality, so the same fixed rotation silently picks
    the INWARD direction instead -- confirmed numerically: west's
    normal has dot(normal, vector-to-origin) < 0 (correctly outward),
    east's has dot > 0 (points back toward material). Fixed by testing
    both perpendicular candidates against a known-interior reference
    point (the tile grid's own center, ~(0,0) for this symmetric grid)
    and picking whichever one points AWAY from it, instead of assuming
    a fixed rotation direction is always correct."""
    pa_s = (pa[0], pa[1] + shift_y)
    pc_s = (pc[0], pc[1] + shift_y)
    mx, my = (pa_s[0] + pc_s[0]) / 2.0, (pa_s[1] + pc_s[1]) / 2.0
    dx, dy = pc_s[0] - pa_s[0], pc_s[1] - pa_s[1]
    L = math.hypot(dx, dy)
    tx, ty = dx / L, dy / L
    cand_a = (ty, -tx)
    cand_b = (-ty, tx)
    to_interior = (interior_ref[0] - mx, interior_ref[1] - my)
    # outward = whichever candidate points AWAY from the interior
    # reference, i.e. has a NEGATIVE dot product with the vector
    # toward it.
    if cand_a[0] * to_interior[0] + cand_a[1] * to_interior[1] < 0:
        nx, ny = cand_a
    else:
        nx, ny = cand_b
    return mx, my, tx, ty, nx, ny

def _fit_profile_from_local(local_pts, cx, cy, tx, ty, nx, ny):
    """Transforms a list of (u,v) points -- u measured along the wall's own
    tangent, v along its true outward normal -- into world XY at the given
    wall-frame origin (cx,cy). Lets the exact same local shape be
    instantiated at either the boss's or the socket's own frame origin
    just by swapping which (cx,cy) is passed in."""
    return [(cx + tx*u + nx*v, cy + ty*u + ny*v) for (u, v) in local_pts]

def _offset_boss_profile(width_top, width_bottom, depth_top, depth_bottom,
                          new_depth_top, new_depth_bottom, clearance):
    """Builds the SOCKET's own local (u,v) profile from the boss's own
    defining taper -- replaces the old approach of independently sizing the
    socket trapezoid with WIDTH_TIP/WIDTH_BASE evaluated at unrelated depths
    (FIT_SOCKET_OPEN_MARGIN / FIT_BOSS_DEPTH+FIT_SOCKET_EXTRA_DEPTH), which
    reused the boss's own width LABELS at depths the boss's real taper never
    actually reaches those widths at.

    A single straight edge from new_depth_top to new_depth_bottom only
    tracks the boss's real (clamped) taper AT those two endpoints -- at any
    depth strictly between them it can be too wide or too narrow, unless
    the boss's own taper bend (depth_top/depth_bottom, wherever the flat
    clamp region starts) also gets its own vertex when it falls inside the
    socket's depth span. So this builds an N-gon from ALL relevant depth
    breakpoints (the socket's own start/end depths, plus any boss bend
    strictly between them), evaluating the boss's own linear taper at each
    one, before applying the same uniform mitered clearance offset as
    before (bisector of the two adjacent edge normals, scaled by 1/cos_half
    so the offset is a true perpendicular distance from each real edge, not
    just a per-vertex push) -- unchanged, just generalized from a fixed
    quad to however many points the breakpoints produce."""
    def width_at(v):
        v_clamped = max(min(v, depth_bottom), depth_top)
        t = (v_clamped - depth_top) / (depth_bottom - depth_top)
        return width_top + (width_bottom - width_top) * t

    # Breakpoints: the socket's own start/end depths, PLUS any boss-taper
    # bend (depth_top, depth_bottom) that falls strictly inside the
    # socket's own depth span. Needed because a single straight edge
    # from new_depth_top to new_depth_bottom doesn't track the boss's
    # real bent profile at any depth between them -- it can be too wide
    # or too narrow at every intermediate depth except the two ends,
    # regardless of clamping the endpoint values alone.
    ascending = new_depth_top <= new_depth_bottom
    lo, hi = (new_depth_top, new_depth_bottom) if ascending else (new_depth_bottom, new_depth_top)
    candidate_vs = {new_depth_top, new_depth_bottom}
    for bend_v in (depth_top, depth_bottom):
        if lo < bend_v < hi:
            candidate_vs.add(bend_v)
    ordered_vs = sorted(candidate_vs) if ascending else sorted(candidate_vs, reverse=True)

    right_pts = [(width_at(v) / 2.0, v) for v in ordered_vs]
    left_pts = [(-w, v) for (w, v) in reversed(right_pts)]
    raw = right_pts + left_pts

    n = len(raw)
    ccx = sum(p[0] for p in raw) / n
    ccy = sum(p[1] for p in raw) / n

    def outward_edge_normal(p0, p1):
        # Picks whichever of the two perpendiculars to edge p0->p1 points
        # away from the polygon's own centroid -- robust to winding order,
        # unlike a fixed-sign (dy/L,-dx/L) formula.
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            return (0.0, 1.0)
        cand = [(dy / L, -dx / L), (-dy / L, dx / L)]
        mid = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
        return max(cand, key=lambda c: (mid[0] + c[0] - ccx)**2 + (mid[1] + c[1] - ccy)**2)

    offset = []
    for i in range(n):
        prev_p, cur_p, next_p = raw[i - 1], raw[i], raw[(i + 1) % n]
        n_in = outward_edge_normal(prev_p, cur_p)
        n_out = outward_edge_normal(cur_p, next_p)
        mx, my = n_in[0] + n_out[0], n_in[1] + n_out[1]
        mlen = math.hypot(mx, my)
        if mlen < 1e-9:
            mx, my = n_in
        else:
            mx, my = mx / mlen, my / mlen
        cos_half = max(mx * n_in[0] + my * n_in[1], 0.35)
        d = clearance / cos_half
        offset.append((cur_p[0] + mx * d, cur_p[1] + my * d))
    return offset

def build_fit_boss_socket(boss_obj, boss_shift_y, socket_obj, socket_shift_y,
                           a2_raw, c_raw, fit_u_offset):
    print(f"\n{'='*60}")
    print(f"Adding vertical fit boss/socket ({boss_obj.name} boss / {socket_obj.name} socket)")
    print(f"{'='*60}")

    pa = GLOBAL_WALL_OFFSET.get(_vkey(a2_raw), a2_raw)
    pc = GLOBAL_WALL_OFFSET.get(_vkey(c_raw), c_raw)

    mx_boss, my_boss, tx, ty, nx, ny = _fit_wall_frame(pa, pc, boss_shift_y)
    mx_sock, my_sock, _, _, _, _ = _fit_wall_frame(pa, pc, socket_shift_y)
    mx_boss += tx * fit_u_offset
    my_boss += ty * fit_u_offset
    mx_sock += tx * fit_u_offset
    my_sock += ty * fit_u_offset
    print(f"  Wall midpoint ({boss_obj.name} frame): ({mx_boss:.3f},{my_boss:.3f}), "
          f"tangent=({tx:.3f},{ty:.3f}), normal=({nx:.3f},{ny:.3f})")
    print(f"  Matching wedge point ({socket_obj.name} frame): ({mx_sock:.3f},{my_sock:.3f})")

    # Taper reversed per your ask: width_top/width_bottom swapped so the
    # ROOT end (depth_top, embedded in the boss object's wall) is now the
    # NARROW (WIDTH_TIP) end and the outward TIP end (depth_bottom,
    # protruding into the socket object) is now the WIDE (WIDTH_BASE)
    # end -- names no longer match which end they size, but left as-is
    # rather than renaming the constants themselves.
    boss_profile = _fit_trapezoid_profile(
        mx_boss, my_boss, tx, ty, nx, ny,
        FIT_BOSS_WIDTH_TIP, FIT_BOSS_WIDTH_BASE,
        -FIT_BOSS_ROOT_OVERLAP, FIT_BOSS_DEPTH)

    print(f"  Boss root corners (world): {boss_profile[0]}, {boss_profile[1]}")
    wall_c = (pc[0], pc[1] + boss_shift_y)
    print(f"  Nearest wall corner C ({boss_obj.name} frame): {wall_c}")
    for root_corner in (boss_profile[0], boss_profile[1]):
        dist = math.hypot(root_corner[0] - wall_c[0], root_corner[1] - wall_c[1])
        print(f"    root corner {root_corner} -> wall corner C: distance = {dist:.3f}mm")

    boss_cutter = make_profile_cutter_z(f"Hole_FitBoss_{boss_obj.name}", boss_profile,
                                         -FIT_Z_OVERSHOOT, PLATE_H + WALL_HEIGHT + FIT_Z_OVERSHOOT)
    safe_cut(f"fit boss on {boss_obj.name}", boss_obj, boss_cutter, primary='EXACT', operation='UNION')
    bpy.data.objects.remove(boss_cutter, do_unlink=True)

    # ---- Trim the boss's Z-overshoot back off -- FIT_Z_OVERSHOOT was
    # only ever needed to avoid the duplicate-coincident-face problem AT
    # UNION TIME (see FIT_Z_OVERSHOOT's own comment above); now that the
    # union has fully merged the boss into one continuous solid with the
    # wall, that internal Z=0/Z=46 seam no longer exists within the
    # boss's own footprint, so a trim cutter confined to just that
    # footprint (not a huge global rectangle, which WOULD still coincide
    # with the surrounding wall's own real, still-separate Z=0/Z=46
    # floor/roof faces just outside the boss) can cut exactly at Z=0 and
    # Z=PLATE_H+WALL_HEIGHT cleanly.
    # obj.bound_box lags behind a mesh-datablock swap (safe_cut's own
    # `target.data = dup.data` on success) until the dependency graph is
    # refreshed -- confirmed in-engine: without this update() call, the
    # "before" print here showed the PRE-union bbox and the "after" print
    # (below) showed the PRE-trim bbox, each one full boolean op stale.
    boss_obj.data.update()
    bpy.context.view_layer.update()
    _bbox_before = [boss_obj.matrix_world @ Vector(c) for c in boss_obj.bound_box]
    _z_before = [v.z for v in _bbox_before]
    print(f"  {boss_obj.name} bbox Z BEFORE overshoot trim: {min(_z_before):.3f}..{max(_z_before):.3f}")

    _TRIM_MARGIN = 2.0   # local footprint margin beyond the boss's own widest
                           # extent, so the trim cutter fully covers the boss's
                           # footprint (including the mitered corners) without
                           # reaching out into the surrounding plain wall
    _trim_u_max = max(FIT_BOSS_WIDTH_TIP, FIT_BOSS_WIDTH_BASE) / 2.0 + _TRIM_MARGIN
    _trim_v_min = -FIT_BOSS_ROOT_OVERLAP - _TRIM_MARGIN
    _trim_v_max = FIT_BOSS_DEPTH + _TRIM_MARGIN
    _trim_local = [(-_trim_u_max, _trim_v_min), (_trim_u_max, _trim_v_min),
                   (_trim_u_max, _trim_v_max), (-_trim_u_max, _trim_v_max)]
    _trim_world = _fit_profile_from_local(_trim_local, mx_boss, my_boss, tx, ty, nx, ny)

    bottom_trim = make_profile_cutter_z(f"Hole_FitBossTrimBottom_{boss_obj.name}", _trim_world,
                                         -FIT_Z_OVERSHOOT - 1.0, 0.0)
    safe_cut(f"fit boss bottom overshoot trim on {boss_obj.name}", boss_obj, bottom_trim, primary='EXACT')
    bpy.data.objects.remove(bottom_trim, do_unlink=True)

    top_trim = make_profile_cutter_z(f"Hole_FitBossTrimTop_{boss_obj.name}", _trim_world,
                                      PLATE_H + WALL_HEIGHT, PLATE_H + WALL_HEIGHT + FIT_Z_OVERSHOOT + 1.0)
    safe_cut(f"fit boss top overshoot trim on {boss_obj.name}", boss_obj, top_trim, primary='EXACT')
    bpy.data.objects.remove(top_trim, do_unlink=True)

    boss_obj.data.update()
    bpy.context.view_layer.update()
    _bbox_after = [boss_obj.matrix_world @ Vector(c) for c in boss_obj.bound_box]
    _z_after = [v.z for v in _bbox_after]
    print(f"  {boss_obj.name} bbox Z AFTER overshoot trim: {min(_z_after):.3f}..{max(_z_after):.3f}")

    # Socket taper is derived from the boss's OWN taper (see
    # _offset_boss_profile's docstring) instead of independently
    # re-sizing a trapezoid with WIDTH_TIP/WIDTH_BASE evaluated at
    # unrelated depths.
    socket_local = _offset_boss_profile(
        FIT_BOSS_WIDTH_TIP, FIT_BOSS_WIDTH_BASE,
        -FIT_BOSS_ROOT_OVERLAP, FIT_BOSS_DEPTH,
        -FIT_SOCKET_OPEN_MARGIN, FIT_BOSS_DEPTH + FIT_SOCKET_EXTRA_DEPTH,
        FIT_SOCKET_CLEARANCE)
    print(f"  FIT_SOCKET_LOCAL has {len(socket_local)} points "
          f"(expect 6: boss taper bend at depth_bottom={FIT_BOSS_DEPTH} falls strictly "
          f"inside the socket's own -{FIT_SOCKET_OPEN_MARGIN}..{FIT_BOSS_DEPTH + FIT_SOCKET_EXTRA_DEPTH} span)")

    print("  Boss vs socket half-width comparison at each breakpoint:")
    for v in sorted({-FIT_BOSS_ROOT_OVERLAP, FIT_BOSS_DEPTH, -FIT_SOCKET_OPEN_MARGIN, FIT_BOSS_DEPTH + FIT_SOCKET_EXTRA_DEPTH}):
        v_clamped = max(min(v, FIT_BOSS_DEPTH), -FIT_BOSS_ROOT_OVERLAP)
        t = (v_clamped - (-FIT_BOSS_ROOT_OVERLAP)) / (FIT_BOSS_DEPTH - (-FIT_BOSS_ROOT_OVERLAP))
        boss_half_width = (FIT_BOSS_WIDTH_TIP + (FIT_BOSS_WIDTH_BASE - FIT_BOSS_WIDTH_TIP) * t) / 2.0
        # Find the socket's actual half-width at this same v by nearest
        # local point. 2.0 tolerance comfortably covers the mitered
        # offset's own shift away from the nominal breakpoint (~0.25mm)
        # while still narrow enough not to accidentally match an
        # unrelated point.
        socket_pts_at_v = [pt for pt in socket_local if abs(pt[1] - v) < 2.0]
        if socket_pts_at_v:
            socket_half_width = max(abs(pt[0]) for pt in socket_pts_at_v)
            gap = socket_half_width - boss_half_width
            print(f"    v={v:6.2f}: boss half-width={boss_half_width:.3f}mm, "
                  f"socket half-width={socket_half_width:.3f}mm, per-side gap={gap:.3f}mm")

    socket_profile = _fit_profile_from_local(socket_local, mx_sock, my_sock, tx, ty, nx, ny)

    print('FIT_BOSS_PROFILE (world):', boss_profile)
    print('FIT_SOCKET_PROFILE (world):', socket_profile)
    print(f'FIT_BOSS_ROOT_OVERLAP={FIT_BOSS_ROOT_OVERLAP}, FIT_SOCKET_OPEN_MARGIN={FIT_SOCKET_OPEN_MARGIN}')

    socket_cutter = make_profile_cutter_z(f"Hole_FitSocket_{socket_obj.name}", socket_profile,
                                           -FIT_Z_OVERSHOOT, PLATE_H + WALL_HEIGHT + FIT_Z_OVERSHOOT)
    safe_cut(f"fit socket on {socket_obj.name}", socket_obj, socket_cutter, primary='EXACT')
    bpy.data.objects.remove(socket_cutter, do_unlink=True)

    # Object-transform check -- confirms whether a viewport look/screenshot
    # taken right HERE (immediately after the boss/socket feature is built)
    # would show the real assembled fit or the still-separated, pre-nudge
    # print layout. cleanup_objects() deletes and recreates every quadrant
    # object fresh at the very start of THIS run, and nothing sets their
    # object.location until the "assembled view" nudge block runs, which is
    # near the very end of the script (after export) -- so at this point in
    # the pipeline both should still be at Blender's default (0,0,0).
    print(f"  {boss_obj.name}.location: {tuple(boss_obj.location)}")
    print(f"  {socket_obj.name}.location: {tuple(socket_obj.location)}")
    print(f"  Y difference ({boss_obj.name}.location.y - {socket_obj.name}.location.y): "
          f"{boss_obj.location.y - socket_obj.location.y:.3f}mm")
    print(f"  FIT_BOSS_DEPTH={FIT_BOSS_DEPTH}, 2*ROW_SPLIT_MARGIN={2*ROW_SPLIT_MARGIN}, "
          f"match={FIT_BOSS_DEPTH == 2*ROW_SPLIT_MARGIN}")

# West seam (W2/W3, TL/BL) -- identical raw corner constants to the
# original, single-use version, so this call reproduces bit-for-bit
# the same geometry as before the refactor.
_A2r = (-210.0, 12.124)     # W1/W2 raw corner
_Cr  = (-168.0, -12.124)    # W2/W3 raw shared corner
_B3r = (-168.0, -60.622)    # W3/W4 raw corner
bl_obj, _W_WEDGE_A2, _W_WEDGE_C, _W_WEDGE_B3 = merge_corner_fill(
    bl_obj, 0.0, -ROW_SPLIT_MARGIN, _A2r, _Cr, _B3r)
build_nut_trap(bl_obj, y1 + ROD_HOLE_Y_OFFSET_L04_R06, _W_WEDGE_A2, _W_WEDGE_B3)
build_fit_boss_socket(tl_obj, ROW_SPLIT_MARGIN, bl_obj, -ROW_SPLIT_MARGIN,
                       _A2r, _Cr, FIT_U_OFFSET)

# East seam (W10/W11, TR/BR) -- the mirror image of the west seam
# (reflected about X=0, per the tile grid's own symmetry): raw corner
# points read directly from the last full run's WALL_SEGMENT_INFO
# table -- W10 (168.0,-60.622)->(168.0,-12.124) tag R06 (owned by
# br_obj) mirrors W3 (BL); W11 (168.0,-12.124)->(210.0,12.124) tag R04
# (owned by tr_obj) mirrors W2 (TL); the shared corner (168.0,-12.124)
# mirrors corner C, and (210.0,12.124) -- W11's own far end, the
# W11/W12 boundary -- mirrors corner A2.
_A2r_E = (210.0, 12.124)    # W11/W12 raw corner (mirrors A2)
_Cr_E  = (168.0, -12.124)   # W10/W11 raw shared corner (mirrors C)
_B3r_E = (168.0, -60.622)   # W9/W10 raw corner (mirrors B3)
br_obj, _E_WEDGE_A2, _E_WEDGE_C, _E_WEDGE_B3 = merge_corner_fill(
    br_obj, GAP_BETWEEN_PLATES, -ROW_SPLIT_MARGIN, _A2r_E, _Cr_E, _B3r_E)
build_nut_trap(br_obj, y1 + ROD_HOLE_Y_OFFSET_L04_R06, _E_WEDGE_A2, _E_WEDGE_B3)
build_fit_boss_socket(tr_obj, ROW_SPLIT_MARGIN, br_obj, -ROW_SPLIT_MARGIN,
                       _A2r_E, _Cr_E, FIT_U_OFFSET)

# ---- X-axis threaded-rod holes (unite the 4 quadrants) — UNCHANGED,
# same positions, same order as before ----
print(f"\n{'='*60}")
print("Drilling X-axis threaded-rod holes")
print(f"{'='*60}")


ROD_HOLE_ROWS = [
    # (label, row_y, y_offset, [target_objs], cutter_length)
    # The two rows exit different outer walls so each gets its OWN
    # cutter length (see comment by the loop below).
    ("X_L02-R04", y2, ROD_HOLE_Y_OFFSET, [tl_obj, tr_obj], 480.0),
    ("X_L04-R06", y1, ROD_HOLE_Y_OFFSET_L04_R06, [bl_obj, br_obj], 372.0),
]
for label, row_cy, y_offset, objs, rod_len in ROD_HOLE_ROWS:
    print(f"\n  Rod hole {label} (row Y={row_cy:.3f}, hole Y={row_cy + y_offset:.3f}, Z={ROD_HOLE_Z_X_AXIS:.1f}, length={rod_len:.0f})...")
    # The X-axis rod cutter must reach WELL PAST the outer wall face(s)
    # that THIS row's rod exits, so every rod hole opens all the way
    # through -- a threaded rod has to slide in. In-engine the tunnel
    # opening lands either at the cutter's own end ("carried" case) or
    # at the wall face ("capped" case), so the cutter has to have
    # enough reach that BOTH outcomes give an insertable through-hole,
    # while staying as short as possible so the carried case doesn't
    # leave a huge floating tube stub.
    #
    # Top row (L02-R04): exits W1 (west) and W12 (east), whose flat-to-
    # corner faces reach out to ~X=+/-219. 480mm (X=-240..+240) clears
    # them by ~21mm -- verified it opens flush at exactly +/-219.
    #
                # Bottom row (L04-R06): exits W3 (west) and BR's mirrored east
    # face. W3's flat face was at X=-177 -- but the W2/W3 corner-fill
    # wedge (merge_corner_fill_into_bl, added above) now extends BL's
    # solid outward past that at this row's Y (ray-cast verified: true
    # outer boundary at Y=-56.373 is X=-182.453, not -177). The old
    # 360mm cutter (X=-180..+180) fell 2.45mm short of that, leaving a
    # thin uncut cap blocking the west opening. 372mm (X=-186..+186)
    # restores the same ~3mm "just past, capped flush" margin the old
    # 360mm value had over the old -177 face, now measured against the
    # wedge's actual -182.453 boundary. BR's east side is untouched by
    # the wedge (still flush at +177), so the extra 6mm there is a
    # small, harmless carried lip. Going much longer re-risks the
    # "carried" floating-lip look flagged before (13mm lip at 380mm
    # against the old -177 face; re-check against -182.453 if this
    # value ever needs revisiting).
    cutter = make_rod_hole_cutter(f"Hole_Rod_{label}", row_cy + y_offset, ROD_HOLE_Z_X_AXIS, length=rod_len)
    apply_transforms(cutter)
    for obj in objs:
        safe_cut(f"{label} rod hole on {obj.name}", obj, cutter, primary='EXACT')
    bpy.data.objects.remove(cutter, do_unlink=True)


# ---- Y-axis threaded-rod holes (unite the 4 quadrants, other axis) --
# positions unchanged from before, but the actual CUTTING now happens
# in a single pass AFTER the rails are merged in (see "Drilling
# Y-axis threaded-rod holes (through rails)" near the end), not here.
# Cutting this column twice -- once now against the bare wall, once
# again later once the rail exists -- put the second cut's cylindrical
# surface exactly coincident with a long stretch of the first cut's
# own tunnel-wall surface (same axis, same radius, just shorter). Confirmed
# in-engine: that's the same degenerate coincident-geometry situation
# behind the rail/wall duplicate-face bug found earlier this session --
# except here the EXACT solver resolved it into a result that stayed
# watertight (so safe_cut's own non-manifold check couldn't catch it)
# while actually re-sealing the passage instead of extending it, so the
# rod hole vanished even though every log line reported a clean cut.
# One cut, after the rail exists, never creates that coincident surface
# in the first place.
ROD_HOLE_COLUMNS = [
    ("Y_L00-L01_L06", ROD_HOLE_X_LEFT, [tl_obj, bl_obj]),
    ("Y_R00-R01_R08", ROD_HOLE_X_RIGHT + GAP_BETWEEN_PLATES, [tr_obj, br_obj]),
]

# ---- Wire-routing canals (rear/bottom face) — UNCHANGED ----
print(f"\n{'='*60}")
print("Cutting wire-routing canals")
print(f"{'='*60}")
print("\n  Self-intersection check just before the canal cuts (after wire "
      "holes + X-axis rod holes, still before the canal/rail/slot cuts):")
for obj in quadrant_objs:
    report_self_intersections(obj)

def _find_tile(tiles, tag):
    for t, cx, cy in tiles:
        if t == tag:
            return cx, cy
    raise KeyError(tag)

CANAL_ROWS = [
    ("Canal_L00-R01", tl_tiles, tr_tiles, 'L00', 'R01', [tl_obj, tr_obj]),
    ("Canal_L02-R04", tl_tiles, tr_tiles, 'L02', 'R04', [tl_obj, tr_obj]),
    ("Canal_L04-R06", bl_tiles, br_tiles, 'L04', 'R06', [bl_obj, br_obj]),
    ("Canal_L06-R08", bl_tiles, br_tiles, 'L06', 'R08', [bl_obj, br_obj]),
]
for label, left_tiles, right_tiles, left_tag, right_tag, objs in CANAL_ROWS:
    _, row_cy = _find_tile(left_tiles, left_tag)
    right_cx, _ = _find_tile(right_tiles, right_tag)
    right_wire_x = right_cx - HOLE_RADIUS
    canal_x_end = right_wire_x + CANAL_RIGHT_MARGIN
    print(f"\n  {label} (row Y={row_cy:.3f})...")
    cutter = make_canal_cutter(f"Hole_{label}", CANAL_LEFT_X, canal_x_end, row_cy,
                                CANAL_Z_START, CANAL_Z_END)
    for obj in objs:
        safe_cut(f"{label} on {obj.name}", obj, cutter, primary='EXACT')
    bpy.data.objects.remove(cutter, do_unlink=True)

# ============================================================
# NEW: top/bottom reinforcement rails — deliberately the LAST thing
# built, after every existing rod hole and canal above, so all of that
# runs against completely unchanged geometry, exactly as before this
# update. 15mm total from the raw hex tip (not 50mm), minimal overlap
# into the existing wall (not deep into the tile — nowhere near the
# 78mm sensor platform), split at the same X boundary the tiles use.
# ============================================================
print(f"\n{'='*60}")
print("Adding top/bottom reinforcement rails (15mm total from tip)")
print(f"{'='*60}")

_top_row_cy = max(cy for cx, cy in grid_orig)
_bottom_row_cy = min(cy for cx, cy in grid_orig)
TOP_ROW_TILES = [(cx, cy) for cx, cy in grid_orig if cy == _top_row_cy]
BOTTOM_ROW_TILES = [(cx, cy) for cx, cy in grid_orig if cy == _bottom_row_cy]

def _raw_tip_extent(row_tiles):
    """Min/max X and the topmost/bottommost Y among the RAW (un-offset)
    hex tile corners — the literal tips, per your spec. (X is only used
    as a fallback below; the real rail length comes from
    _wall_outer_extreme_x.)"""
    xs, ys = [], []
    for (cx, cy) in row_tiles:
        for x, y in get_hex_corners(cx, cy, HEX_FLAT_WIDTH):
            xs.append(x); ys.append(y)
    return min(xs), max(xs), min(ys), max(ys)

def _wall_outer_extreme_x(cx, cy, angles_deg, pick):
    """The rail's LENGTH should reach the wall's actual (mitered) outer
    surface at its outermost tile (L00/R01 for top, L06/R08 for
    bottom) -- not the underlying raw hex corner. The wall already
    bulges PERIMETER_THICKNESS+WALL_WIDTH out from the raw corner via
    the same miter that built it (GLOBAL_WALL_OFFSET); stopping the
    rail at the raw corner leaves the wall's own corner sticking out
    past the rail's edge. `angles_deg` are that tile's own corner
    angles on the outward-facing side; `pick` is min/max, whichever
    direction is "more extreme" for that side. (Checked numerically:
    L00's west corner sits at raw X=-168, wall_outer X=-177 -- the
    genuinely built wall reaches 9mm further than the raw hex.)"""
    xs = []
    for a_deg in angles_deg:
        a = math.radians(a_deg)
        raw = (cx + S*math.cos(a), cy + S*math.sin(a))
        xs.append(GLOBAL_WALL_OFFSET.get(_vkey(raw), raw)[0])
    return pick(xs)

_, _, _, TOP_TIP_Y = _raw_tip_extent(TOP_ROW_TILES)     # max Y (topmost tip)
_, _, BOTTOM_TIP_Y, _ = _raw_tip_extent(BOTTOM_ROW_TILES) # min Y (bottommost tip)

_top_left_tile = min(TOP_ROW_TILES, key=lambda t: t[0])       # L00
_top_right_tile = max(TOP_ROW_TILES, key=lambda t: t[0])      # R01
_bottom_left_tile = min(BOTTOM_ROW_TILES, key=lambda t: t[0])   # L06
_bottom_right_tile = max(BOTTOM_ROW_TILES, key=lambda t: t[0])  # R08

TOP_RAIL_X0 = _wall_outer_extreme_x(*_top_left_tile, [150, 210], min)
TOP_RAIL_X1 = _wall_outer_extreme_x(*_top_right_tile, [30, 330], max)
BOTTOM_RAIL_X0 = _wall_outer_extreme_x(*_bottom_left_tile, [150, 210], min)
BOTTOM_RAIL_X1 = _wall_outer_extreme_x(*_bottom_right_tile, [30, 330], max)

TOP_RAIL_Y_OUTER = TOP_TIP_Y + RAIL_TOTAL_FROM_TIP                                    # tip+15
BOTTOM_RAIL_Y_OUTER = BOTTOM_TIP_Y - RAIL_TOTAL_FROM_TIP                              # tip-15

RAIL_ROD_Y_TOP = TOP_RAIL_Y_OUTER - RAIL_ROD_OFFSET_FROM_OUTER
RAIL_ROD_Y_BOTTOM = BOTTOM_RAIL_Y_OUTER + RAIL_ROD_OFFSET_FROM_OUTER

print(f"Top rail: X {TOP_RAIL_X0:.1f}..{TOP_RAIL_X1:.1f}, tip Y={TOP_TIP_Y:.1f}, "
      f"y_outer={TOP_RAIL_Y_OUTER:.1f}, rod Y={RAIL_ROD_Y_TOP:.1f}")
print(f"Bottom rail: X {BOTTOM_RAIL_X0:.1f}..{BOTTOM_RAIL_X1:.1f}, tip Y={BOTTOM_TIP_Y:.1f}, "
      f"y_outer={BOTTOM_RAIL_Y_OUTER:.1f}, rod Y={RAIL_ROD_Y_BOTTOM:.1f}")

# ---- Attach each rail by merging its geometry DIRECTLY into the
# quadrant's own mesh -- no boolean union at all anymore. Found the
# real cause of the gap you saw in SuperSlicer (not a shading
# artifact): my rail's "floor" was built as NEW side-wall faces
# tracing the wall's own outer surface (Z0 to Z2, along the same
# GLOBAL_WALL_OFFSET points build_plate_body already used) -- but
# build_plate_body had ALREADY built those exact same faces when it
# built the wall in the first place. Two solids with a genuinely
# duplicate, exactly-coincident face along most of their shared
# boundary is a textbook case a boolean solver can resolve wrong,
# which is exactly what a slicer would then read as an open/unclear
# region rather than solid. Rather than tune the overlap depth again,
# the fix is to never build that duplicate face at all: merge only
# the rail's genuinely NEW geometry (the flat outer roof, the two end
# caps down to the wall's true surface, and the top/bottom caps) into
# the wall's EXISTING mesh, and let bmesh's own vertex welding
# (remove_doubles) stitch the new geometry to the wall's pre-existing
# side faces wherever they share a vertex position exactly -- which
# is everywhere along the chain now, since the whole chain is built
# straight from GLOBAL_WALL_OFFSET (the wall's own true surface) with
# no separate "overlap into the wall" offset needed any more (there's
# no boolean left for an epsilon to help).

def _row_offset_segments(row_tiles, tip_angle, left_angle, right_angle, offset_map):
    """Ordered (west-to-east) list of (p0, p1, owner_cx) segments
    tracing a row's top/bottom silhouette -- each segment is exactly
    ONE tile's own left-to-tip or tip-to-right edge, run through
    `offset_map`'s miter. Ownership is tracked per SEGMENT, not per
    point: a shared valley point genuinely belongs to two tiles at
    once, so tagging the POINT (and inheriting that tag for whichever
    segment starts there) is ambiguous -- the segment leaving a valley
    into the NEXT tile is that next tile's own edge, not the previous
    tile's, even though they share that one point. Verified this was
    a real bug: for BottomRail_L, the segment from L06's shared corner
    into R07's own tip inherited L06's tag and was wrongly treated as
    local to BL (should be foreign, R07 lives in BR), leaving a
    genuine hole with neither an old face deleted nor a new one built."""
    segments = []
    def pt(cx, cy, a_deg):
        a = math.radians(a_deg)
        raw = (cx + S * math.cos(a), cy + S * math.sin(a))
        return offset_map.get(_vkey(raw), raw)
    for (cx, cy) in sorted(row_tiles, key=lambda t: t[0]):
        left, tip, right = pt(cx, cy, left_angle), pt(cx, cy, tip_angle), pt(cx, cy, right_angle)
        segments.append((left, tip, cx))
        segments.append((tip, right, cx))
    return segments

def _split_segments_at_x(segments, split_x):
    """Splits an ordered west-to-east list of (p0, p1, owner_cx)
    segments into (left, right) at X=split_x, cutting any segment that
    straddles split_x into two pieces -- both keeping the SAME owner,
    since splitting for the quadrant boundary doesn't change which
    tile's edge this geometrically is. Both halves meet exactly at
    split_x, same as the rail's own X boundary between quadrants."""
    left, right = [], []
    for p0, p1, owner in segments:
        x0, x1 = p0[0], p1[0]
        if x0 <= split_x and x1 <= split_x:
            left.append((p0, p1, owner))
        elif x0 >= split_x and x1 >= split_x:
            right.append((p0, p1, owner))
        else:
            t = (split_x - x0) / (x1 - x0)
            cross = (split_x, p0[1] + t * (p1[1] - p0[1]))
            if x0 < x1:
                left.append((p0, cross, owner)); right.append((cross, p1, owner))
            else:
                right.append((p0, cross, owner)); left.append((cross, p1, owner))
    return left, right

# Looser (0.01mm) match, used ONLY for the rail-merge ownership lookup
# below -- NOT a replacement for the global _vkey (that stays at
# 0.001mm everywhere else, since loosening it globally risks false
# merges elsewhere). By the time the rail merge runs, the wall has
# already been through several earlier, unrelated boolean cuts (wire
# holes, rod holes, canals); even where those cuts are nowhere near a
# given wall-outer corner, Blender's solver can still nudge that
# vertex's stored coordinate by a few microns as a side effect of its
# own internal numerics -- invisible at print scale but enough to flip
# a 0.001mm-rounded key. Nothing in this design has two distinct
# features closer than 0.01mm (the smallest real feature is a 3.5mm
# rod radius), so loosening just this comparison is safe.
def _vkey_loose(p):
    return (round(p[0], 2), round(p[1], 2))

def _face_on_wall_segment(face, p0, p1, z0, z1, tol=0.05):
    """True if EVERY vertex of `face` lies on the vertical plane
    containing the line through p0->p1, within the segment's own span
    (0<=t<=1 along it, a little slack at the ends) and within
    [z0,z1] (a little slack top/bottom) -- i.e. this face is some
    fragment of "the wall's own surface along this one tile edge",
    however many pieces it's currently in. Matching by an exact set of
    4 corners (the original approach, even loosened to 0.01mm) turned
    out to miss real cases: an EARLIER, unrelated cut (e.g. a Y-axis
    rod hole passing straight through a tip point at Z=11.5..18.5) can
    split what was one tall z0..z1 quad into a below-hole piece, an
    above-hole piece, and the hole's own boundary fragments -- NONE of
    which still has all 4 of the original z0/z1 corners, so the exact
    search finds nothing and leaves the fragments behind (confirmed:
    a standalone bmesh-free replica reproduced the exact "0 obsolete
    replaced" + lingering non-manifold edges seen in-engine once a rod
    hole was simulated through that tip). A line/span/Z containment
    test catches every fragment regardless of how it was subdivided,
    without touching the rod hole's own tunnel-wall faces (those bow
    away from this flat plane into the material, so only their
    boundary-circle vertices could ever satisfy this test, and a
    single face never has ALL its verts on that boundary alone)."""
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return False
    tol_t = tol / L
    for v in face.verts:
        vx, vy, vz = v.co.x, v.co.y, v.co.z
        t = ((vx-p0[0])*dx + (vy-p0[1])*dy) / (L*L)
        if t < -tol_t or t > 1 + tol_t:
            return False
        perp = abs((vx-p0[0])*dy - (vy-p0[1])*dx) / L
        if perp > tol:
            return False
        if vz < z0 - tol or vz > z1 + tol:
            return False
    return True

def _find_and_delete_faces_on_segment(bm, p0, p1, z0, z1):
    """Deletes every face in `bm` that's some fragment of the wall's
    own surface along the p0->p1 tile edge -- see
    _face_on_wall_segment. Returns how many faces were deleted."""
    to_delete = [f for f in bm.faces if _face_on_wall_segment(f, p0, p1, z0, z1)]
    if to_delete:
        bmesh.ops.delete(bm, geom=to_delete, context='FACES')
    return len(to_delete)

def merge_rail_into_wall(label, target_obj, x0, x1, y_outer, segments, is_top,
                          z0, z1, shift_x, shift_y, is_local_owner):
    """Adds the rail's NEW material directly into target_obj's own
    mesh -- no boolean union, no separate rail object at all. The
    silhouette is the flat outer roof plus the segment chain tracing
    the wall's true surface, closing into one simple polygon.

    Every "floor" segment corresponds to a vertical face that ALREADY
    exists somewhere as part of the wall's own exterior geometry, built
    by build_plate_body from this same tile edge -- but WHICH
    quadrant's mesh it lives in depends on which tile actually owns it
    (`segments`' own owner_cx, unambiguous per-segment -- see
    _row_offset_segments):
      - owner tile is in THIS quadrant: that exact wall-outer face is
        already sitting in target_obj's own mesh. It's now purely
        internal (rail material continues past it), so every face
        occupying that position gets found and DELETED here rather
        than building a second, duplicate face on top of it --
        confirmed as the real cause of the gap found in the sliced
        STL (two solids with a genuinely duplicate, exactly-coincident
        face along their shared boundary is a case a boolean solver
        can resolve wrong; even merged directly as one mesh, a
        duplicate face is still wrong).
      - owner tile is in the OTHER quadrant (e.g. R07 for
        BottomRail_L): target_obj's mesh never had a face there at
        all, so a brand new side wall gets built, same as for the
        roof/end-cap segments.
    remove_doubles then welds every new vertex that lands exactly on
    an existing wall vertex -- which is every segment endpoint, since
    the whole chain comes straight from GLOBAL_WALL_OFFSET, the wall's
    own true surface."""
    chain_pts = [segments[0][0]] + [s[1] for s in segments]
    roof = [((x0, y_outer), True, None), ((x1, y_outer), True, None)]
    body = [(p, False, None) for p in reversed(chain_pts)]
    pts = roof + body
    if is_top:
        pts = list(reversed(pts))
    pts = [((x + shift_x, y + shift_y), is_roof) for (x, y), is_roof, _ in pts]

    bm = bmesh.new()
    bm.from_mesh(target_obj.data)
    vmap = {}
    def gv(x, y, z):
        k = (round(x, 3), round(y, 3), round(z, 3))
        if k not in vmap:
            vmap[k] = bm.verts.new((x, y, z))
        return vmap[k]

    n = len(pts)
    bv = [gv(p[0], p[1], z0) for p, _ in pts]
    tv = [gv(p[0], p[1], z1) for p, _ in pts]
    try: bm.faces.new(list(reversed(bv)))
    except ValueError: pass
    try: bm.faces.new(tv)
    except ValueError: pass

    # Look up each floor edge's owner by its two (unshifted) endpoint
    # positions directly, rather than trying to track index offsets
    # through the roof-prepended, reversed point list above.
    seg_owner_by_edge = {}
    for p0, p1, owner in segments:
        key = frozenset([_vkey_loose(p0), _vkey_loose(p1)])
        seg_owner_by_edge[key] = owner

    deleted = 0
    for k in range(n):
        kk = (k + 1) % n
        is_roof_k, is_roof_kk = pts[k][1], pts[kk][1]
        if is_roof_k or is_roof_kk:
            try: bm.faces.new([bv[k], bv[kk], tv[kk], tv[k]])
            except ValueError: pass
            continue
        edge_key = frozenset([_vkey_loose((bv[k].co.x - shift_x, bv[k].co.y - shift_y)),
                               _vkey_loose((bv[kk].co.x - shift_x, bv[kk].co.y - shift_y))])
        owner = seg_owner_by_edge.get(edge_key)
        if owner is not None and is_local_owner(owner):
            deleted += _find_and_delete_faces_on_segment(
                bm, (bv[k].co.x, bv[k].co.y), (bv[kk].co.x, bv[kk].co.y), z0, z1)
        else:
            try: bm.faces.new([bv[k], bv[kk], tv[kk], tv[k]])
            except ValueError: pass

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bm.normal_update()
    bm.to_mesh(target_obj.data)
    bm.free()
    target_obj.data.update()

    nm, za = report_manifold_stats(target_obj)
    print(f"  {label}: merged directly into {target_obj.name} (no boolean, "
          f"{deleted} obsolete wall face(s) replaced) -- "
          f"non-manifold edges: {nm}, zero-area faces: {za}")

TOP_FULL_SEGMENTS = _row_offset_segments(TOP_ROW_TILES, 90, 150, 30, GLOBAL_WALL_OFFSET)
BOTTOM_FULL_SEGMENTS = _row_offset_segments(BOTTOM_ROW_TILES, 270, 210, 330, GLOBAL_WALL_OFFSET)
TOP_SEGMENTS_L, TOP_SEGMENTS_R = _split_segments_at_x(TOP_FULL_SEGMENTS, SPLIT_X)
BOTTOM_SEGMENTS_L, BOTTOM_SEGMENTS_R = _split_segments_at_x(BOTTOM_FULL_SEGMENTS, SPLIT_X)

_is_left = lambda owner_cx: owner_cx < SPLIT_X
_is_right = lambda owner_cx: owner_cx >= SPLIT_X

RAIL_SPECS = [
    ("TopRail_L", TOP_RAIL_X0, SPLIT_X, TOP_RAIL_Y_OUTER, TOP_SEGMENTS_L,
     True, 0.0, ROW_SPLIT_MARGIN, tl_obj, _is_left),
    ("TopRail_R", SPLIT_X, TOP_RAIL_X1, TOP_RAIL_Y_OUTER, TOP_SEGMENTS_R,
     True, GAP_BETWEEN_PLATES, ROW_SPLIT_MARGIN, tr_obj, _is_right),
    ("BottomRail_L", BOTTOM_RAIL_X0, SPLIT_X, BOTTOM_RAIL_Y_OUTER, BOTTOM_SEGMENTS_L,
     False, 0.0, -ROW_SPLIT_MARGIN, bl_obj, _is_left),
    ("BottomRail_R", SPLIT_X, BOTTOM_RAIL_X1, BOTTOM_RAIL_Y_OUTER, BOTTOM_SEGMENTS_R,
     False, GAP_BETWEEN_PLATES, -ROW_SPLIT_MARGIN, br_obj, _is_right),
]
for label, x0, x1, y_outer, segments, is_top, shift_x, shift_y, obj, is_local_owner in RAIL_SPECS:
    print(f"\n  {label}: X {x0:.1f}..{x1:.1f}, y_outer={y_outer:.1f}")
    merge_rail_into_wall(label, obj, x0, x1, y_outer, segments, is_top,
                          0.0, PLATE_H + WALL_HEIGHT, shift_x, shift_y, is_local_owner)

print(f"\n{'='*60}")
print("Drilling X-axis rod holes through the new top/bottom rails")
print(f"{'='*60}")
RAIL_ROD_ROWS = [
    ("X_TopRail", RAIL_ROD_Y_TOP + ROW_SPLIT_MARGIN, [tl_obj, tr_obj]),
    ("X_BottomRail", RAIL_ROD_Y_BOTTOM - ROW_SPLIT_MARGIN, [bl_obj, br_obj]),
]
for label, rod_y, objs in RAIL_ROD_ROWS:
    print(f"\n  Rod hole {label} (Y={rod_y:.3f}, Z={RAIL_ROD_Z:.1f})...")
    # Shorter than the default 2000mm cutter used everywhere else --
    # the rail itself only spans up to TOP_RAIL_X0..X1 (-177..177), so
    # a 2000mm-long cylinder is mostly extraneous far-flung geometry
    # for the solver to process near the fragile L06/R07 split corner
    # where the bottom rod hole was leaking/failing. 500mm (250mm each
    # side of X=0) still clears the widest rail (177mm) by 73mm.
    cutter = make_rod_hole_cutter(f"Hole_Rod_{label}", rod_y, RAIL_ROD_Z, length=500.0)
    apply_transforms(cutter)
    for obj in objs:
        safe_cut(f"{label} rod hole on {obj.name}", obj, cutter, primary='EXACT')
    bpy.data.objects.remove(cutter, do_unlink=True)

# ---- Drill the two Y-axis rod holes now that the rails exist -- this
# is now the ONLY place they're cut (see the note by ROD_HOLE_COLUMNS
# above): one pass, through the complete wall+rail solid, so the
# cutter's cylindrical surface never has to coincide with a
# pre-existing tunnel wall from an earlier pass at the same axis.
print(f"\n{'='*60}")
print("Drilling Y-axis threaded-rod holes (through rails)")
print(f"{'='*60}")
for label, col_x, objs in ROD_HOLE_COLUMNS:
    print(f"\n  Rod hole {label} (column X={col_x:.3f}, Z={ROD_HOLE_Z_Y_AXIS:.1f})...")
    # Shortened from the default 2000mm for the same reason the rail's
    # own X-axis rod cutters were: the real geometry here only spans
    # about 345mm (TOP_RAIL_Y_OUTER=172.6 down to BOTTOM_RAIL_Y_OUTER=
    # -172.6) -- a 2000mm cutter is 1650mm+ of pure empty overhang for
    # the EXACT solver to carry through the operation. Confirmed
    # in-engine: with the full-length cutter, this cut reported "clean"
    # (0 non-manifold) while actually adding only 64 new vertices and 4
    # new faces per quadrant -- consistent with punching two separate
    # round openings (entry/exit) WITHOUT the connecting tunnel wall
    # between them, i.e. two blind dimples, not a through-hole. 450mm
    # (225mm each side of Y=0) clears the full rail-to-rail span with
    # margin.
    cutter = make_rod_hole_cutter_y(f"Hole_Rod_{label}", col_x, ROD_HOLE_Z_Y_AXIS, length=450.0)
    apply_transforms(cutter)
    for obj in objs:
        # Diagnostic: a boolean that "cuts cleanly" (0 non-manifold, no
        # leaked verts) can still be a silent no-op if the cutter never
        # actually overlapped solid material -- report_manifold_stats
        # can't tell a real tunnel apart from nothing happening at all,
        # since both leave a clean, unchanged-looking mesh. Vertex/face
        # counts can't lie about that: a real cut always adds new
        # vertices along the cylinder's intersection curve.
        bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        bb_xs = [v.x for v in bb]; bb_ys = [v.y for v in bb]; bb_zs = [v.z for v in bb]
        print(f"    {obj.name} bbox: X {min(bb_xs):.1f}..{max(bb_xs):.1f}, "
              f"Y {min(bb_ys):.1f}..{max(bb_ys):.1f}, Z {min(bb_zs):.1f}..{max(bb_zs):.1f}")
        v0, f0 = len(obj.data.vertices), len(obj.data.polygons)
        vol0 = mesh_volume(obj)
        # Experiment: EXACT reported "clean" (0 non-manifold) on this
        # exact cut while the volume/face evidence says it barely
        # removed anything -- safe_cut's own "primary looked clean,
        # stop there" shortcut means FLOAT never even gets tried as a
        # comparison in that case. Forcing FLOAT as primary here tests
        # whether it handles this column's geometry differently.
        safe_cut(f"{label} rod hole on {obj.name}", obj, cutter, primary='FLOAT')
        v1, f1 = len(obj.data.vertices), len(obj.data.polygons)
        vol1 = mesh_volume(obj)
        if v1 == v0 and f1 == f0:
            print(f"    ⚠⚠ {obj.name}: vertex/face count UNCHANGED ({v0}v/{f0}f) -- "
                  f"this cut did NOT modify the mesh at all, despite reporting clean")
        else:
            print(f"    {obj.name}: {v0}v/{f0}f -> {v1}v/{f1}f")
        print(f"    {obj.name}: volume {vol0:.0f}mm^3 -> {vol1:.0f}mm^3 "
              f"(removed {vol0-vol1:.0f}mm^3)")
    bpy.data.objects.remove(cutter, do_unlink=True)

# ---- Fit tabs at the top/bottom rail L/R seams -- interlocking
# tongue-and-groove registration features so the printed quadrants
# can't slide relative to each other at the rail level, on top of what
# the threaded rods already do. One tab+slot pair per rail (top,
# bottom), at the same X=SPLIT_X seam the rail itself is split at; the
# left half (TopRail_L / BottomRail_L) carries the protruding tab, the
# right half the matching slot.
#
# Width (15mm) runs vertically (Z), not along the rail's own depth
# (Y): the Y-depth available right at the seam varies hugely with
# where the split lands on the tip/valley silhouette -- the top seam
# has ~28.9mm of rail-only Y-depth there, but the bottom seam lands
# almost exactly on a tip, leaving only ~4.6mm. Z has the full 46mm of
# rail height to draw on regardless.
#
# Positioned at the rail's own OUTER surface (y_outer), not tucked
# inward, per your ask to have it flush and visible from outside --
# the tab's outer face actually sits TAB_OUTER_PROUD past y_outer
# (a deliberate, small, visible proud edge, not an exactly-coincident
# plane) both so it reads clearly as a feature from outside and so the
# union has an unambiguous boundary to resolve rather than a knife's-
# edge coincidence with the rail's own flat roof. Inward thickness
# from there is set PER SEAM, not shared, per your ask: the bottom
# seam (near a tip, only ~4.6mm of rail-only depth available) uses
# nearly all of it (5.0mm, leaving ~0.1mm before the chain/wall
# boundary), while the top seam (a valley, ~28.9mm available) uses a
# more modest 12.0mm you specified directly rather than maxing out.
#
# Z-position (5..20mm) sits below the X-axis rail rod (Z~32.5..39.5)
# with margin, within the base slab / bottom of the wall band.
#
# Cross-section in X-Z is a right-trapezoid, not a rectangle: the
# original rectangular tab sat flush with the wall at X=0 starting
# abruptly at Z=5, with nothing at all below it (X>0, Z<5) in the
# tab-side quadrant's own print -- a genuine unsupported horizontal
# overhang, exactly the FDM print problem you flagged. The trapezoid
# ramps the protrusion from 0 (flush, at Z=TAB_Z0) up to full depth
# over TAB_RAMP_HEIGHT of Z (a 45-degree incline, printable without
# support), then stays at full depth for the rest of the tab's height.
print(f"\n{'='*60}")
print("Adding fit tabs at the top/bottom rail L/R seams")
print(f"{'='*60}")

TAB_WIDTH_Z = 15.0
TAB_DEPTH_X = 6.0
# Per-seam Y-thickness, not a single shared value -- per your ask:
# the bottom seam (L06/R07, landing almost on a tip) uses essentially
# ALL of its available rail-only depth (checked numerically: the
# proud outer edge to the chain/wall boundary is 5.108mm there, so
# 5.0mm uses nearly all of it with a hair of margin -- matches what
# you were seeing as "2 or 3mm you can add in" beyond the old 3mm).
# The top seam (L01/R00, a valley -- ~28.9mm available) uses the
# 12.0mm you asked for specifically, well short of the max.
TOP_TAB_THICKNESS_Y = 12.0
BOTTOM_TAB_THICKNESS_Y = 5.0
TAB_Z0 = 5.0
TAB_Z1 = TAB_Z0 + TAB_WIDTH_Z
TAB_RAMP_HEIGHT = TAB_DEPTH_X   # 45-degree self-supporting ramp (rise == run)
TAB_OUTER_PROUD = 0.5   # tab's outer face sits this far past y_outer --
                          # see comment above.
TAB_UNION_OVERLAP_X = 3.0   # the tab profile extends this far PAST X=0
                             # into the tab-side quadrant's own existing
                             # solid, so the union has a genuine
                             # volumetric overlap to resolve rather than
                             # merely touching it at a single coincident
                             # plane -- the same class of degenerate
                             # case (touching, not overlapping,
                             # geometry) that caused several of the
                             # boolean failures earlier this session.
TAB_SLOT_CLEARANCE = 0.2   # the slot is cut this much larger than the
                             # tab's own ramped profile, offset OUTWARD
                             # (perpendicular to each face, mitered at
                             # the corners -- see
                             # _offset_ramped_tab_profile) on every real
                             # tab surface (ramp, deep face, top face),
                             # not just a bounding box. Originally this
                             # was a plain rectangular box (removing
                             # material has no overhang concern, so
                             # nothing FORCED it to match the tab's
                             # shape) -- but that left the female side
                             # not actually reflecting the male tab's
                             # ramp, with needless slop right at the
                             # ramp corner instead of a properly keyed
                             # fit. The near (seam-facing) end still
                             # opens flat at X=-1 rather than following
                             # the profile all the way in, same as
                             # before, to guarantee the cutter actually
                             # punctures through the boundary face
                             # rather than being tangent to it. A small
                             # friction-fit clearance; tune for your
                             # printer if 0.2mm prints too tight/loose.

def _extrude_profile_along_y(bm, profile_xz, y0, y1):
    """Extrudes a closed 2D profile (list of (x,z) points, in order)
    along Y from y0 to y1 into a closed solid prism.

    Winding is deliberately reversed from the "obvious" order below --
    verified in-engine (signed volume of the raw prism) that the naive
    winding produces a fully consistent but INWARD-facing solid (every
    face backwards, not a mixed/broken mesh). A union tolerates that
    fine (confirmed: the TAB_PROFILE prism, built the exact same way,
    unions onto SensorBase_TL/BL without issue), but it's exactly what
    made the fit-tab SLOT cut fail identically on SensorBase_TR/BR --
    "boolean reported success but 2 cutter vertices leaked into the
    result" at the same relative corner regardless of the box's
    position, size, or padding (tested directly against a duplicate:
    shifting/padding every axis still leaked the identical corner,
    ruling out a coincident-geometry cause). Reversing every face here
    made that DIFFERENCE cut resolve cleanly (0 non-manifold edges, 0
    zero-area faces, mesh.validate() clean, removed volume matching the
    box's expected volume) -- confirmed against both SensorBase_TR and
    SensorBase_BR before applying here."""
    near = [bm.verts.new((x, y0, z)) for x, z in profile_xz]
    far = [bm.verts.new((x, y1, z)) for x, z in profile_xz]
    n = len(profile_xz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([near[j], near[i], far[i], far[j]])
    bm.faces.new(near)
    bm.faces.new(list(reversed(far)))

def make_profile_cutter(name, profile_xz, y0, y1):
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    _extrude_profile_along_y(bm, profile_xz, y0, y1)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    return obj

def make_box_cutter(name, x0, x1, y0, y1, z0, z1):
    return make_profile_cutter(name, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y0, y1)

def _offset_ramped_tab_profile(depth_x, ramp_height, z0, z1, clearance, open_x=-1.0):
    """Builds the SLOT profile as the tab's own ramped right-trapezoid
    silhouette (the same shape TAB_PROFILE traces from X=0 outward: up
    the ramp, out to the deep face, across the top) expanded outward by
    `clearance`, perpendicular to each real face and properly mitered
    at the two corners -- so the female cavity actually follows the
    male tab's shape instead of a bounding box that's needlessly loose
    right at the ramp. The near (seam-facing) end is deliberately left
    open at `open_x` (not mitered/closed off) so the cutter still
    reliably punctures through the target's own boundary face, same
    reasoning as the original box cutter's -1.0 start."""
    dx, dz = depth_x, ramp_height
    L = math.hypot(dx, dz)
    ramp_n = (dz / L, -dx / L)
    deep_n = (1.0, 0.0)
    top_n = (0.0, 1.0)

    def miter(n1, n2, corner):
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        mL = math.hypot(mx, my)
        mx, my = mx / mL, my / mL
        cos_half = mx * n1[0] + my * n1[1]
        d = clearance / cos_half
        return (corner[0] + mx * d, corner[1] + my * d)

    deep_bottom_off = miter(ramp_n, deep_n, (depth_x, z0 + ramp_height))
    deep_top_off = miter(deep_n, top_n, (depth_x, z1))
    near_bottom_z = z0 + ramp_n[1] * clearance
    near_top_z = z1 + top_n[1] * clearance

    return [
        (open_x, near_bottom_z),
        deep_bottom_off,
        deep_top_off,
        (open_x, near_top_z),
    ]

TAB_PROFILE = [
    (-TAB_UNION_OVERLAP_X, TAB_Z0),
    (0.0, TAB_Z0),
    (TAB_DEPTH_X, TAB_Z0 + TAB_RAMP_HEIGHT),
    (TAB_DEPTH_X, TAB_Z1),
    (-TAB_UNION_OVERLAP_X, TAB_Z1),
]

TAB_SEAMS = [
    ("Top",    TOP_RAIL_Y_OUTER,    ROW_SPLIT_MARGIN,  -1, tl_obj, tr_obj, TOP_TAB_THICKNESS_Y),
    ("Bottom", BOTTOM_RAIL_Y_OUTER, -ROW_SPLIT_MARGIN, +1, bl_obj, br_obj, BOTTOM_TAB_THICKNESS_Y),
]

for label, y_outer_unshifted, shift_y, inward_sign, left_obj, right_obj, thickness_y in TAB_SEAMS:
    y_outer_shifted = y_outer_unshifted + shift_y
    y_proud = y_outer_shifted - inward_sign * TAB_OUTER_PROUD
    y_inner = y_proud + inward_sign * thickness_y
    y0, y1 = sorted([y_proud, y_inner])
    print(f"\n  {label} seam: Y {y0:.2f}..{y1:.2f} (outer face {TAB_OUTER_PROUD:.1f}mm proud "
          f"of y_outer={y_outer_shifted:.2f}), Z {TAB_Z0:.1f}..{TAB_Z1:.1f}, tab X 0..{TAB_DEPTH_X:.1f}")

    # Both cutters below are built directly in world coordinates (like
    # make_canal_cutter), so no apply_transforms call is needed.
    tab_cutter = make_profile_cutter(f"Hole_{label}Tab", TAB_PROFILE, y0, y1)
    safe_cut(f"{label} seam tab on {left_obj.name}", left_obj, tab_cutter,
              primary='EXACT', operation='UNION')
    bpy.data.objects.remove(tab_cutter, do_unlink=True)

    # The slot's outer edge is clamped to the rail's actual y_outer
    # surface (plus the normal small clearance) rather than reusing
    # y0/y1's outer bound, which includes the tab's own
    # TAB_OUTER_PROUD extension. That proud sliver sticks out into
    # open air past BOTH pieces' real material -- the tab's tip is
    # meant to be visible/external, not socketed -- so a slot cutter
    # reaching that far was mostly sitting in empty space, tangent to
    # the slot side's own boundary rather than genuinely inside or
    # outside it. Confirmed in-engine: this was exactly why the slot
    # cut failed identically on both right-side quadrants ("2 cutter
    # vertices leaked") while the tab's own union (a completely
    # different cutter shape, on the left side) succeeded fine.
    slot_y_outer = y_outer_shifted + (-inward_sign) * TAB_SLOT_CLEARANCE
    slot_y_inner = y_inner + inward_sign * TAB_SLOT_CLEARANCE
    sy0, sy1 = sorted([slot_y_outer, slot_y_inner])
    slot_profile = _offset_ramped_tab_profile(TAB_DEPTH_X, TAB_RAMP_HEIGHT, TAB_Z0, TAB_Z1,
                                               TAB_SLOT_CLEARANCE, open_x=-1.0)
    slot_cutter = make_profile_cutter(f"Hole_{label}Slot", slot_profile, sy0, sy1)
    safe_cut(f"{label} seam slot on {right_obj.name}", right_obj, slot_cutter, primary='EXACT')
    bpy.data.objects.remove(slot_cutter, do_unlink=True)


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

# ---- Assembled-view positioning (viewport only) ----------------------
# Runs AFTER export above, so the exported STLs still have the real
# ROW_SPLIT_MARGIN gap baked into their geometry (needed for print
# separation/handling clearance) -- only the four objects' own
# world-space location is nudged here, closing that gap so the
# viewport shows the tray as it looks assembled. Mesh data is
# untouched; re-running this script rebuilds the objects at the origin
# and reapplies this same nudge, so the assembled view no longer has
# to be redone by hand after every re-run.
print(f"\n{'='*60}")
print("Positioning quadrants together for an assembled view (viewport only)")
print(f"{'='*60}")
tl_obj.location.y -= ROW_SPLIT_MARGIN
tr_obj.location.y -= ROW_SPLIT_MARGIN
bl_obj.location.y += ROW_SPLIT_MARGIN
br_obj.location.y += ROW_SPLIT_MARGIN
bpy.context.view_layer.update()
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.tag_redraw()

print(f"  [POST-NUDGE] tl_obj.location: {tuple(tl_obj.location)}")
print(f"  [POST-NUDGE] bl_obj.location: {tuple(bl_obj.location)}")
print(f"  [POST-NUDGE] Y difference: {tl_obj.location.y - bl_obj.location.y:.3f}mm")

# ---- Wall-segment labeling (W1, W2, ...) -- generalizes the earlier
# W1-only approach into a full boundary-trace walk. Purely additive/
# informational, doesn't touch any geometry. Runs here (after rails +
# fit tabs) because it needs RAIL_SPECS-equivalent data (TOP_ROW_TILES,
# TOP_RAIL_Y_OUTER, etc), all computed earlier in the rail section.
#
# A tile-by-tile approach (the old W1 code) breaks down for the rail
# rows, where merge_rail_into_wall has already replaced several tiles'
# worth of individual zigzag wall edges with ONE flat rail roof --
# labeling tile-by-tile there would put 2-3 labels on what is now
# genuinely a single flat face. So instead: walk the GLOBAL, unsplit
# true-exterior boundary trace edge by edge (same nxt adjacency
# compute_boundary_offset_map builds internally for grid_orig,
# rebuilt directly here to avoid touching that function), and merge
# consecutive edges into ONE labeled segment when either:
#   - they're geometrically collinear (direction within
#     ANGLE_MERGE_TOL_DEG) -- handles genuine multi-tile-wide flat
#     runs on the plain wall (e.g. L02's own 3-edge west-corner run
#     stays 3 separate labels, since those edges are NOT collinear
#     with each other; W1 below is confirmed still exactly the single
#     west edge from the earlier per-tile version), or
#   - they were both replaced by the SAME rail (checked by owner tile
#     membership in TOP_ROW_TILES/BOTTOM_ROW_TILES + which side of
#     SPLIT_X, the same ownership test merge_rail_into_wall's own
#     is_local_owner uses) -- collapses an entire rail's zigzag span
#     into one label, positioned on the rail's own y_outer surface
#     (the wall_outer_offset data at that location now describes
#     buried, no-longer-exposed geometry) instead of the collinearity
#     rule, since the RAW edges there still zigzag even though the
#     BUILT rail face covering them is flat.
print(f"\n{'='*60}")
print("Labeling wall segments (W1, W2, ...)")
print(f"{'='*60}")

WALL_SEGMENT_LABEL_PUSH = 5.0   # matches the original W1's own push
WALL_SEGMENT_LABEL_Z = (0.0 + PLATE_H + WALL_HEIGHT) / 2.0   # matches
                         # W1's own Z -- the rail's own z0/z1 (passed
                         # into merge_rail_into_wall) are the SAME
                         # 0..PLATE_H+WALL_HEIGHT range as the plain
                         # wall, so one fixed Z works for every label.
ANGLE_MERGE_TOL_DEG = 2.0

_seg_nxt, _seg_coord, _seg_owner = {}, {}, {}
for (_cx, _cy) in grid_orig:
    _corners = get_hex_corners(_cx, _cy, HEX_FLAT_WIDTH)
    for _i in range(6):
        _j = (_i + 1) % 6
        _p0, _p1 = _corners[_i], _corners[_j]
        _ek = tuple(sorted([_vkey(_p0), _vkey(_p1)]))
        if FULL_EDGE_COUNT.get(_ek, 0) != 1:
            continue
        _k0, _k1 = _vkey(_p0), _vkey(_p1)
        _seg_nxt[_k0] = _k1
        _seg_coord[_k0] = _p0
        _seg_coord[_k1] = _p1
        _seg_owner[_ek] = (_cx, _cy)

_left_grid_raw = left_grid
_right_grid_raw = [(cx - GAP_BETWEEN_PLATES, cy) for cx, cy in right_grid]
_RAW_TAG_MAP = {}
for _i, (_cx, _cy) in enumerate(_left_grid_raw):
    _RAW_TAG_MAP[_vkey((_cx, _cy))] = f"L{_i:02d}"
for _i, (_cx, _cy) in enumerate(_right_grid_raw):
    _RAW_TAG_MAP[_vkey((_cx, _cy))] = f"R{_i:02d}"

# Start the walk at L02's own west edge specifically, so that edge
# becomes segment #1 (W1) -- matching the W1 label already verified
# earlier, rather than an arbitrary trace start point. (Confirmed
# safe: neither neighboring edge is collinear with it, so it stays a
# standalone segment regardless of where the walk begins.)
_l02_cx, _l02_cy = left_grid[2]
_l02_corners = get_hex_corners(_l02_cx, _l02_cy, HEX_FLAT_WIDTH)
_l02_west_edge, _l02_west_normal_check = None, None
for _i in range(6):
    _j = (_i + 1) % 6
    _p0, _p1 = _l02_corners[_i], _l02_corners[_j]
    _ek = tuple(sorted([_vkey(_p0), _vkey(_p1)]))
    if FULL_EDGE_COUNT.get(_ek, 0) != 1:
        continue
    _dx, _dy = _p1[0] - _p0[0], _p1[1] - _p0[1]
    _L = math.hypot(_dx, _dy)
    _n = (_dy / _L, -_dx / _L)
    if _l02_west_normal_check is None or _n[0] < _l02_west_normal_check[0]:
        _l02_west_normal_check = _n
        _l02_west_edge = (_p0, _p1)
_START_KEY = _vkey(_l02_west_edge[0])

_raw_edges = []
_cur = _START_KEY
while True:
    _nxt_k = _seg_nxt[_cur]
    _ek = tuple(sorted([_cur, _nxt_k]))
    _raw_edges.append((_seg_coord[_cur], _seg_coord[_nxt_k], _seg_owner[_ek]))
    if _nxt_k == _START_KEY:
        break
    _cur = _nxt_k

print(f"  {len(_raw_edges)} true-exterior raw edges in the global trace")

_top_row_set = {_vkey(t) for t in TOP_ROW_TILES}
_bottom_row_set = {_vkey(t) for t in BOTTOM_ROW_TILES}

def _rail_group_for(owner):
    ok = _vkey(owner)
    if ok in _top_row_set:
        return "TopRail_L" if owner[0] < SPLIT_X else "TopRail_R"
    if ok in _bottom_row_set:
        return "BottomRail_L" if owner[0] < SPLIT_X else "BottomRail_R"
    return None

_RAIL_Y_OUTER = {
    "TopRail_L": TOP_RAIL_Y_OUTER, "TopRail_R": TOP_RAIL_Y_OUTER,
    "BottomRail_L": BOTTOM_RAIL_Y_OUTER, "BottomRail_R": BOTTOM_RAIL_Y_OUTER,
}
_RAIL_OUTWARD = {
    "TopRail_L": (0.0, 1.0), "TopRail_R": (0.0, 1.0),
    "BottomRail_L": (0.0, -1.0), "BottomRail_R": (0.0, -1.0),
}

def _edge_dir(p0, p1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    return (dx / L, dy / L)

def _edge_normal(p0, p1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    return (dy / L, -dx / L)

_groups = []
for _edge in _raw_edges:
    _p0, _p1, _owner = _edge
    _rg = _rail_group_for(_owner)
    if _groups:
        _prev = _groups[-1]
        _same_rail = (_rg is not None and _rg == _prev['rail'])
        _both_plain = (_rg is None and _prev['rail'] is None)
        _collinear = False
        if _both_plain:
            _pe = _prev['edges'][-1]
            _d_prev = _edge_dir(_pe[0], _pe[1])
            _d_this = _edge_dir(_p0, _p1)
            _dot = max(-1.0, min(1.0, _d_prev[0]*_d_this[0] + _d_prev[1]*_d_this[1]))
            _angle = math.degrees(math.acos(_dot))
            _collinear = _angle <= ANGLE_MERGE_TOL_DEG
        if _same_rail or (_both_plain and _collinear):
            _prev['edges'].append(_edge)
            continue
    _groups.append({'rail': _rg, 'edges': [_edge]})

print(f"  Merged into {len(_groups)} labeled segments before end-cap transitions")

# Precompute each group's own (position, outward normal, owner tags) --
# uniformly for both plain-wall and rail groups -- before assigning
# final sequential numbers, since transition entries (below) get
# spliced in between groups and need the same uniform shape.
def _group_owner_tags(edges):
    tags = []
    for e in edges:
        tag = _RAW_TAG_MAP.get(_vkey(e[2]), f"({e[2][0]:.1f},{e[2][1]:.1f})")
        if tag not in tags:
            tags.append(tag)
    return tags

def _group_pos_normal(grp):
    edges = grp['edges']
    p_start, p_end = edges[0][0], edges[-1][1]
    if grp['rail'] is not None:
        y_outer = _RAIL_Y_OUTER[grp['rail']]
        out_n = _RAIL_OUTWARD[grp['rail']]
        face = ((p_start[0] + p_end[0]) / 2.0, y_outer)
    else:
        wo_mids = []
        for e in edges:
            wo0 = GLOBAL_WALL_OFFSET.get(_vkey(e[0]), e[0])
            wo1 = GLOBAL_WALL_OFFSET.get(_vkey(e[1]), e[1])
            wo_mids.append(((wo0[0]+wo1[0])/2.0, (wo0[1]+wo1[1])/2.0))
        face = (sum(m[0] for m in wo_mids) / len(wo_mids),
                sum(m[1] for m in wo_mids) / len(wo_mids))
        out_n = _edge_normal(edges[0][0], edges[0][1])
    return face, out_n

# ---- End-cap transitions -- merge_rail_into_wall builds a real,
# distinct connecting face at each rail's OUTER end (the end away from
# SPLIT_X, where it meets a plain-wall tile rather than the matching
# rail on the other quadrant) -- from the rail's own roof corner
# (outer_x, y_outer) down to the plain wall's own wall_outer point at
# that same shared raw corner. The rail's own roof X always exactly
# equals that wall_outer point's X (both derived from the same
# GLOBAL_WALL_OFFSET lookup on the same corner), so the roof point is
# just that wall_outer point with Y swapped to y_outer -- no need to
# separately reach into RAIL_SPECS' x0/x1 for this. The SPLIT_X-side
# end of each rail meets its sibling rail directly (no plain wall,
# same y_outer, no such face exists there) so only transitions between
# a plain group and a rail group -- not rail-to-rail -- get one.
_entries = []   # ordered final list of dicts: {label, edges/pseudo, pos, out_n, tags}
for _i, _grp in enumerate(_groups):
    if _i > 0:
        _prev = _groups[_i - 1]
        _is_transition = (_prev['rail'] is None) != (_grp['rail'] is None)
        if _is_transition:
            _rail_grp = _grp if _grp['rail'] is not None else _prev
            _plain_grp = _prev if _grp['rail'] is not None else _grp
            _shared_raw = _prev['edges'][-1][1]   # == _grp['edges'][0][0]
            _wall_outer_pt = GLOBAL_WALL_OFFSET.get(_vkey(_shared_raw), _shared_raw)
            _y_outer = _RAIL_Y_OUTER[_rail_grp['rail']]
            _roof_pt = (_wall_outer_pt[0], _y_outer)
            _side_sign = -1.0 if _wall_outer_pt[0] < 0 else 1.0
            _t_out_n = (_side_sign, 0.0)
            _t_pos = ((_wall_outer_pt[0] + _roof_pt[0]) / 2.0,
                      (_wall_outer_pt[1] + _roof_pt[1]) / 2.0)
            _t_tags = _group_owner_tags(_plain_grp['edges'][-1:]) + _group_owner_tags(_rail_grp['edges'][:1])
            _entries.append({'pos': _t_pos, 'out_n': _t_out_n,
                              'p_start': _shared_raw, 'p_end': _shared_raw, 'length': 0.0,
                              'tags': _t_tags})
    _pos, _out_n = _group_pos_normal(_grp)
    _entries.append({'pos': _pos, 'out_n': _out_n,
                      'p_start': _grp['edges'][0][0], 'p_end': _grp['edges'][-1][1],
                      'length': sum(math.hypot(e[1][0]-e[0][0], e[1][1]-e[0][1]) for e in _grp['edges']),
                      'tags': _group_owner_tags(_grp['edges']),
                      'edges': _grp['edges']})

print(f"  {len(_entries) - len(_groups)} end-cap transition(s) added -- {len(_entries)} labels total")

WALL_SEGMENT_LABELS = {}   # frozenset({raw_vkey0, raw_vkey1}) -> "W<n>",
                            # keyed per constituent edge so any raw
                            # edge in a merged (non-transition) segment
                            # resolves to it
WALL_SEGMENT_INFO = []      # (label, p_start, p_end, length, owner_tags)

for _n, _entry in enumerate(_entries, start=1):
    _label = f"W{_n}"
    WALL_SEGMENT_INFO.append((_label, _entry['p_start'], _entry['p_end'], _entry['length'], _entry['tags']))
    if 'edges' in _entry:
        for _e in _entry['edges']:
            WALL_SEGMENT_LABELS[frozenset([_vkey(_e[0]), _vkey(_e[1])])] = _label

    _out_n = _entry['out_n']
    _label_x = _entry['pos'][0] + _out_n[0] * WALL_SEGMENT_LABEL_PUSH
    _label_y = _entry['pos'][1] + _out_n[1] * WALL_SEGMENT_LABEL_PUSH

    bpy.ops.object.text_add(location=(_label_x, _label_y, WALL_SEGMENT_LABEL_Z))
    _txt = bpy.context.active_object
    _txt.name = f"WallSeg_{_label}"
    _txt.data.body = _label
    _txt.data.size = 5.0
    _txt.data.align_x = 'CENTER'
    _txt.data.align_y = 'CENTER'
    # Standing upright, facing outward -- identical technique to the
    # original W1: local Z (the readable-from side) points along the
    # segment's own outward normal, local Y kept close to world Z.
    _txt.rotation_mode = 'QUATERNION'
    _outward_vec = Vector((_out_n[0], _out_n[1], 0.0))
    _txt.rotation_quaternion = _outward_vec.to_track_quat('Z', 'Y')

print(f"\n  {'Label':<6} {'P_start':<22} {'P_end':<22} {'Len':>7}  Tiles")
for _label, _p_start, _p_end, _length, _owner_tags in WALL_SEGMENT_INFO:
    print(f"  {_label:<6} ({_p_start[0]:8.3f},{_p_start[1]:8.3f})   "
          f"({_p_end[0]:8.3f},{_p_end[1]:8.3f})   {_length:7.2f}  {','.join(_owner_tags)}")

print(f"  Placed {len(WALL_SEGMENT_INFO)} wall-segment labels")
print("=" * 60)

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
print(f"Rail: {RAIL_TOTAL_FROM_TIP:.1f}mm total from tip")
print(f"Inner sensor tile: {INNER_TILE_WIDTH:.1f}mm wide, {INNER_TILE_HEIGHT:.1f}mm tall, "
      f"{HEX_FLAT_WIDTH - INNER_TILE_WIDTH:.1f}mm gap between neighbors")
print(f"Join plates (flush fit): {'ON' if JOIN_PLATES else 'OFF'}")
print(f"Invisible tile gap: {INVISIBLE_TILE_GAP:.1f} tiles = {GAP_BETWEEN_PLATES:.1f}mm")
print(f"Row split margin: {ROW_SPLIT_MARGIN:.1f}mm each side ({2*ROW_SPLIT_MARGIN:.1f}mm total gap)")
print(f"Wire hole diameter: {WIRE_HOLE_DIAMETER:.1f}mm")
print("="*60)

