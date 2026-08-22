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
                                                # base plate's rod Z (5mm) --
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

# ---- THREADED ROD HOLES (unite the 4 quadrant plates) — UNCHANGED, same
# positions as before, not touched by this update at all --------------
ROD_HOLE_DIAMETER = 7.0
ROD_HOLE_RADIUS = ROD_HOLE_DIAMETER / 2.0
ROD_HOLE_Y_OFFSET = 20.0
ROD_HOLE_Y_OFFSET_L04_R06 = -20.0
ROD_HOLE_Z_X_AXIS = PLATE_H / 4.0
ROD_HOLE_Z_Y_AXIS = 3.0 * PLATE_H / 4.0
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
        if obj.name.startswith(("SensorBase", "Hole_", "Wire_", "TileNum_", "Cut_")):
            to_remove.append(obj)
    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)
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
    mesh.validate()
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

def make_rod_hole_cutter(name, y_center, z_center, length=2000.0):
    print(f"    Rod hole at Y={y_center:.3f}, Z={z_center:.3f} (⌀{ROD_HOLE_DIAMETER:.1f}mm, along X)")

    mesh=bpy.data.meshes.new(name+"_mesh")
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bm=bmesh.new()
    segs=32
    half=length/2.0
    bv,tv=[],[]

    for i in range(segs):
        a=2*math.pi*i/segs
        yo=ROD_HOLE_RADIUS*math.cos(a)
        zo=ROD_HOLE_RADIUS*math.sin(a)
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
    cutter_positions = {(round(v.co.x,3), round(v.co.y,3), round(v.co.z,3))
                         for v in cutter.data.vertices}
    result_positions = {(round(v.co.x,3), round(v.co.y,3), round(v.co.z,3))
                         for v in result_obj.data.vertices}
    leaked = cutter_positions & result_positions
    return len(leaked) > 0, len(leaked)

def try_cut_on_copy(target, cutter, solver):
    """Returns (ok, delta_nm, delta_za, dup, abs_nm, abs_za) -- the delta
    is relative to `target`'s own state going in, but abs_nm/abs_za are
    the FINAL non-manifold/zero-area counts on the result itself. A
    delta of 0 only means this particular operation didn't make things
    WORSE than whatever `target` already was -- it says nothing about
    whether `target` was already broken. safe_cut below picks/reports
    based on the absolute counts for that reason."""
    nm0, za0 = report_manifold_stats(target)
    dup = duplicate_obj(target, target.name + "_TRY")
    ok = do_diff(dup, cutter, solver=solver)
    if not ok:
        bpy.data.objects.remove(dup, do_unlink=True)
        return False, None, None, None, None, None
    nm1, za1 = report_manifold_stats(dup)
    leaked, leak_count = cutter_leaked_into_result(cutter, dup)
    if leaked:
        print(f"      {solver}: boolean reported success but {leak_count} cutter "
              f"vertices leaked into the result — treating as failed")
        nm1 = nm0 + 1000
    print(f"      {solver}: non-manifold edges: {nm1-nm0} (total now {nm1}), "
          f"zero-area faces: {za1-za0} (total now {za1})")
    return True, nm1 - nm0, za1 - za0, dup, nm1, za1

def safe_cut(label, target, cutter, primary='EXACT'):
    print(f"    Cutting {label}...")
    alt = 'FLOAT' if primary == 'EXACT' else 'EXACT'
    ok1, _, _, dup1, nm1, za1 = try_cut_on_copy(target, cutter, primary)
    if ok1 and nm1 == 0 and za1 == 0:
        target.data = dup1.data
        bpy.data.objects.remove(dup1, do_unlink=True)
        print(f"    ✓ {label} cut cleanly with {primary}")
        return True
    ok2, _, _, dup2, nm2, za2 = try_cut_on_copy(target, cutter, alt)
    candidates = []
    if ok1: candidates.append((nm1 + za1, primary, dup1, nm1, za1))
    if ok2: candidates.append((nm2 + za2, alt, dup2, nm2, za2))
    if not candidates:
        print(f"    ⚠ {label}: both solvers failed — material NOT removed")
        return False
    candidates.sort(key=lambda c: c[0])
    best_score, best_solver, best_dup, best_nm, best_za = candidates[0]
    target.data = best_dup.data
    for _, _, d, _, _ in candidates:
        if d is not best_dup:
            bpy.data.objects.remove(d, do_unlink=True)
    bpy.data.objects.remove(best_dup, do_unlink=True)
    if best_score > 0:
        print(f"    ⚠ {label}: cleanest available ({best_solver}) still has "
              f"{best_nm} non-manifold edges, {best_za} zero-area faces")
    else:
        print(f"    ✓ {label} cut cleanly with {best_solver}")
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
# (unchanged from before — this is the ORIGINAL build order, nothing
# reordered around it)
tl_obj = build_side(tl_tiles, "SensorBase_TL", shift_x=0.0, shift_y=ROW_SPLIT_MARGIN)
tr_obj = build_side(tr_tiles, "SensorBase_TR", shift_x=GAP_BETWEEN_PLATES, shift_y=ROW_SPLIT_MARGIN)
bl_obj = build_side(bl_tiles, "SensorBase_BL", shift_x=0.0, shift_y=-ROW_SPLIT_MARGIN)
br_obj = build_side(br_tiles, "SensorBase_BR", shift_x=GAP_BETWEEN_PLATES, shift_y=-ROW_SPLIT_MARGIN)

quadrant_objs = [tl_obj, tr_obj, bl_obj, br_obj]

# ---- X-axis threaded-rod holes (unite the 4 quadrants) — UNCHANGED,
# same positions, same order as before ----
print(f"\n{'='*60}")
print("Drilling X-axis threaded-rod holes")
print(f"{'='*60}")
ROD_HOLE_ROWS = [
    ("X_L02-R04", y2, ROD_HOLE_Y_OFFSET, [tl_obj, tr_obj]),
    ("X_L04-R06", y1, ROD_HOLE_Y_OFFSET_L04_R06, [bl_obj, br_obj]),
]
for label, row_cy, y_offset, objs in ROD_HOLE_ROWS:
    print(f"\n  Rod hole {label} (row Y={row_cy:.3f}, hole Y={row_cy + y_offset:.3f}, Z={ROD_HOLE_Z_X_AXIS:.1f})...")
    cutter = make_rod_hole_cutter(f"Hole_Rod_{label}", row_cy + y_offset, ROD_HOLE_Z_X_AXIS)
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
print(f"Rail: {RAIL_TOTAL_FROM_TIP:.1f}mm total from tip")
print(f"Inner sensor tile: {INNER_TILE_WIDTH:.1f}mm wide, {INNER_TILE_HEIGHT:.1f}mm tall, "
      f"{HEX_FLAT_WIDTH - INNER_TILE_WIDTH:.1f}mm gap between neighbors")
print(f"Join plates (flush fit): {'ON' if JOIN_PLATES else 'OFF'}")
print(f"Invisible tile gap: {INVISIBLE_TILE_GAP:.1f} tiles = {GAP_BETWEEN_PLATES:.1f}mm")
print(f"Row split margin: {ROW_SPLIT_MARGIN:.1f}mm each side ({2*ROW_SPLIT_MARGIN:.1f}mm total gap)")
print(f"Wire hole diameter: {WIRE_HOLE_DIAMETER:.1f}mm")
print("="*60)