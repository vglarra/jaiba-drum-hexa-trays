import bpy, bmesh, math, os
from mathutils import Vector

print("=== FLAT HEX PLATES — PROPER BOUNDARY-TRACED OUTER WALL ===")
print("=" * 60)

# ---- CONFIGURABLE PARAMETERS --------------------
HEX_FLAT_WIDTH = 84.0
HOLE_RADIUS = 28.0
PLATE_H = 2.0

# ---- PERIMETER CONTOUR PARAMETERS --------------------
PERIMETER_THICKNESS = 3.0
TOTAL_WIDTH = HEX_FLAT_WIDTH + 2 * PERIMETER_THICKNESS

# ---- INVISIBLE TILE GAP --------------------
INVISIBLE_TILE_GAP = 1.0
TILE_SPACING = 1.5 * HEX_FLAT_WIDTH
GAP_BETWEEN_PLATES = INVISIBLE_TILE_GAP * TILE_SPACING

# ---- WALL PARAMETERS --------------------
WALL_WIDTH = 6.0
WALL_HEIGHT = 26.0

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
print(f"Wall: {WALL_WIDTH:.1f}mm wide, {WALL_HEIGHT:.1f}mm tall")
print(f"Gap between plates: {GAP_BETWEEN_PLATES:.1f}mm")
print(f"Note: pin holes are OMITTED in this version, per request.")
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

left_grid = []
right_grid = []
for cx, cy in grid_orig:
    if cx < SPLIT_X:
        left_grid.append((cx, cy))
    else:
        right_grid.append((cx + GAP_BETWEEN_PLATES, cy))

print(f"Split at X = {SPLIT_X:.3f}")
print(f"Left: {len(left_grid)} tiles, Right: {len(right_grid)} tiles")
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

def make_hex_plate_with_perimeter(grid_tiles, solid_name):
    """Create hex plate with perimeter contour on exterior edges only"""
    print(f"\nBuilding {solid_name} with {len(grid_tiles)} tiles")
    print(f"  Perimeter thickness: {PERIMETER_THICKNESS}mm (same height as plate: {PLATE_H}mm)")

    edge_owner = {}
    tile_corner_cache = {}
    for (cx, cy) in grid_tiles:
        corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH)
        tile_corner_cache[(cx, cy)] = corners
        for i in range(6):
            j = (i+1) % 6
            p0 = (round(corners[i][0], 3), round(corners[i][1], 3))
            p1 = (round(corners[j][0], 3), round(corners[j][1], 3))
            ekey = tuple(sorted([p0, p1]))
            edge_owner[ekey] = edge_owner.get(ekey, 0) + 1

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

    exterior_ridge_edges = 0
    for idx, (cx, cy) in enumerate(grid_tiles):
        main_corners = tile_corner_cache[(cx, cy)]
        perim_corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH + 2*PERIMETER_THICKNESS)
        
        # Main body side walls
        for i in range(6):
            j = (i+1) % 6
            b0 = gv(main_corners[i][0], main_corners[i][1], 0.0)
            b1 = gv(main_corners[j][0], main_corners[j][1], 0.0)
            t0 = gv(main_corners[i][0], main_corners[i][1], PLATE_H)
            t1 = gv(main_corners[j][0], main_corners[j][1], PLATE_H)
            try: bm.faces.new([b0, b1, t1, t0])
            except: pass
        
        # Perimeter contour - EXTERIOR EDGES ONLY
        for i in range(6):
            j = (i+1) % 6
            m0 = main_corners[i]; m1 = main_corners[j]
            p0m = (round(m0[0], 3), round(m0[1], 3))
            p1m = (round(m1[0], 3), round(m1[1], 3))
            ekey = tuple(sorted([p0m, p1m]))
            if edge_owner[ekey] != 1:
                continue
            exterior_ridge_edges += 1

            p0 = perim_corners[i]; p1 = perim_corners[j]
            
            b_m0 = gv(m0[0], m0[1], 0.0); b_m1 = gv(m1[0], m1[1], 0.0)
            b_p0 = gv(p0[0], p0[1], 0.0); b_p1 = gv(p1[0], p1[1], 0.0)
            t_m0 = gv(m0[0], m0[1], PLATE_H); t_m1 = gv(m1[0], m1[1], PLATE_H)
            t_p0 = gv(p0[0], p0[1], PLATE_H); t_p1 = gv(p1[0], p1[1], PLATE_H)
            
            try: bm.faces.new([b_p0, b_p1, t_p1, t_p0])
            except: pass
            try: bm.faces.new([t_m0, t_m1, t_p1, t_p0])
            except: pass
            try: bm.faces.new([b_m0, b_m1, t_m1, t_m0])
            except: pass
            try: bm.faces.new([b_p0, b_p1, b_m1, b_m0])
            except: pass
        
        # Bottom and top faces
        bottom_verts = [gv(c[0], c[1], 0.0) for c in main_corners]
        try: bm.faces.new(list(reversed(bottom_verts)))
        except: pass
        
        top_verts = [gv(c[0], c[1], PLATE_H) for c in main_corners]
        try: bm.faces.new(top_verts)
        except: pass
        
        if idx < 3 or idx >= len(grid_tiles)-3:
            print(f"  Tile {idx}: center=({cx:.3f}, {cy:.3f})")
    
    print(f"  Created {len(grid_tiles)} tiles — perimeter ridge built on "
          f"{exterior_ridge_edges} true exterior edges")
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    return obj

def add_outer_wall(obj, grid_tiles, side_label):
    """Adds the outer wall via DIRECT mesh construction, traced along the
    REAL tile boundary (not a convex hull — a convex hull skips over
    every concave notch in a shape like this flower, which is exactly
    what produced the gaps in the previous attempt). Only builds on
    TRUE exterior edges (matching what make_hex_plate_with_perimeter
    already uses), and explicitly connects adjacent wall segments at
    each boundary vertex so concave/convex corners don't leave a gap
    or a disconnected sliver."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    vmap = {}
    for v in bm.verts:
        k = (round(v.co.x, 3), round(v.co.y, 3), round(v.co.z, 3))
        vmap[k] = v

    def gv(x, y, z):
        k = (round(x, 3), round(y, 3), round(z, 3))
        if k not in vmap:
            vmap[k] = bm.verts.new((x, y, z))
        return vmap[k]

    z0 = PLATE_H
    z1 = PLATE_H + WALL_HEIGHT
    outer_flat_width = TOTAL_WIDTH + 2*WALL_WIDTH

    # Exterior-edge check done against the tile's TRUE HEX_FLAT_WIDTH
    # boundary (where neighbors genuinely share a coincident edge) —
    # same edge index reused for the actual wall geometry at the larger
    # TOTAL_WIDTH / outer_flat_width corners.
    edge_owner = {}
    tile_flat_corners = {}
    for (cx, cy) in grid_tiles:
        corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH)
        tile_flat_corners[(cx, cy)] = corners
        for i in range(6):
            j = (i+1) % 6
            p0 = (round(corners[i][0], 3), round(corners[i][1], 3))
            p1 = (round(corners[j][0], 3), round(corners[j][1], 3))
            ekey = tuple(sorted([p0, p1]))
            edge_owner[ekey] = edge_owner.get(ekey, 0) + 1

    exterior_edge_count = 0
    corner_touches = {}
    for (cx, cy) in grid_tiles:
        flat_corners = tile_flat_corners[(cx, cy)]
        inner_corners = get_hex_corners(cx, cy, TOTAL_WIDTH)
        outer_corners = get_hex_corners(cx, cy, outer_flat_width)
        for i in range(6):
            j = (i+1) % 6
            f0 = flat_corners[i]; f1 = flat_corners[j]
            p0 = (round(f0[0], 3), round(f0[1], 3))
            p1 = (round(f1[0], 3), round(f1[1], 3))
            ekey = tuple(sorted([p0, p1]))
            if edge_owner[ekey] != 1:
                continue
            exterior_edge_count += 1

            i0 = inner_corners[i]; i1 = inner_corners[j]
            o0 = outer_corners[i]; o1 = outer_corners[j]

            b_i0 = gv(i0[0], i0[1], z0); b_i1 = gv(i1[0], i1[1], z0)
            b_o0 = gv(o0[0], o0[1], z0); b_o1 = gv(o1[0], o1[1], z0)
            t_i0 = gv(i0[0], i0[1], z1); t_i1 = gv(i1[0], i1[1], z1)
            t_o0 = gv(o0[0], o0[1], z1); t_o1 = gv(o1[0], o1[1], z1)

            try: bm.faces.new([b_o0, b_o1, t_o1, t_o0])   # outer wall
            except: pass
            try: bm.faces.new([t_i0, t_i1, t_o1, t_o0])   # top cap
            except: pass
            try: bm.faces.new([b_i0, b_i1, t_i1, t_i0])   # inner wall
            except: pass
            try: bm.faces.new([b_o0, b_o1, b_i1, b_i0])   # bottom cap
            except: pass

            key_i0 = (round(i0[0], 3), round(i0[1], 3))
            key_i1 = (round(i1[0], 3), round(i1[1], 3))
            corner_touches.setdefault(key_i0, []).append((o0, b_i0, t_i0))
            corner_touches.setdefault(key_i1, []).append((o1, b_i1, t_i1))

    # Connect adjacent segments at each boundary vertex where two
    # exterior edges genuinely meet at different offset points (rare —
    # most same-tile transitions already coincide exactly, verified).
    corners_joined = 0
    end_caps_added = 0
    for key, touches in corner_touches.items():
        if len(touches) == 2:
            (oA, b_iA, t_iA), (oB, b_iB, t_iB) = touches
            if (round(oA[0],3), round(oA[1],3)) == (round(oB[0],3), round(oB[1],3)):
                continue   # already coincide, nothing to fill
            b_oA = gv(oA[0], oA[1], z0); t_oA = gv(oA[0], oA[1], z1)
            b_oB = gv(oB[0], oB[1], z0); t_oB = gv(oB[0], oB[1], z1)
            try: bm.faces.new([b_iA, b_oA, b_oB])
            except: pass
            try: bm.faces.new([t_iA, t_oB, t_oA])
            except: pass
            try: bm.faces.new([b_oA, t_oA, t_oB, b_oB])
            except: pass
            corners_joined += 1
        elif len(touches) == 1:
            # The REAL bug: a wall segment ends here because the tile's
            # next edge going around is interior (no wall) — the wall's
            # rectangular cross-section is left completely open at this
            # end with nothing closing it. Cap it directly.
            (o, b_i, t_i) = touches[0]
            b_o = gv(o[0], o[1], z0); t_o = gv(o[0], o[1], z1)
            try: bm.faces.new([b_i, b_o, t_o, t_i])
            except: pass
            end_caps_added += 1

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    nm, za = report_manifold_stats(obj)
    print(f"\n  Outer wall for {side_label}: {exterior_edge_count} true exterior "
          f"edges, {corners_joined} corners connected, {end_caps_added} end caps "
          f"added — {WALL_WIDTH:.1f}mm wide, "
          f"z={z0:.1f}..{z1:.1f}mm. Mesh after wall: "
          f"{nm} non-manifold edges, {za} zero-area faces")
    return True

def make_wire_hole_cutter(name, cx, cy):
    """Wire hole - goes through the full height"""
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

def try_cut_on_copy(target, cutter, solver):
    nm0, za0 = report_manifold_stats(target)
    dup = duplicate_obj(target, target.name + "_TRY")
    ok = do_diff(dup, cutter, solver=solver)
    if not ok:
        bpy.data.objects.remove(dup, do_unlink=True)
        return False, None, None, None
    nm1, za1 = report_manifold_stats(dup)
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
def build_side(grid_tiles, half_char, solid_name):
    print(f"\n{'='*60}")
    print(f"Building {solid_name} with {len(grid_tiles)} tiles")
    print(f"{'='*60}")
    
    obj = make_hex_plate_with_perimeter(grid_tiles, solid_name)
    
    for i, (cx, cy) in enumerate(grid_tiles):
        tag = f"{half_char}{i:02d}"
        print(f"\n  [{i+1}/{len(grid_tiles)}] Processing {tag} at ({cx:.3f}, {cy:.3f})...")

        wire = make_wire_hole_cutter(f"Wire_{tag}", cx, cy)
        apply_transforms(wire)
        safe_cut(f"{tag} wire hole", obj, wire, primary='EXACT')
        bpy.data.objects.remove(wire, do_unlink=True)

        add_tile_label(tag, cx, cy)

    # Outer wall — proper boundary-traced, not convex hull
    add_outer_wall(obj, grid_tiles, solid_name)

    nm, za = report_manifold_stats(obj)
    print(f"\n  Final stats for {solid_name}:")
    print(f"    Non-manifold edges: {nm}")
    print(f"    Zero-area faces: {za}")
    
    return obj

# ---- Build both plates ----
left_obj = build_side(left_grid, 'L', "SensorBase_L")
right_obj = build_side(right_grid, 'R', "SensorBase_R")

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

export_obj(left_obj,  "flat_hex_plate-Walls_LEFT.stl")
export_obj(right_obj, "flat_hex_plate-Walls_RIGHT.stl")

print("\n" + "="*60)
print("=== DONE ===")
print(f"Left plate: {len(left_grid)} tiles")
print(f"Right plate: {len(right_grid)} tiles")
print(f"Total tiles: {len(left_grid) + len(right_grid)}")
print(f"Tile size: {HEX_FLAT_WIDTH:.1f}mm flat-to-flat")
print(f"Perimeter thickness: {PERIMETER_THICKNESS:.1f}mm")
print(f"Wall: {WALL_WIDTH:.1f}mm wide, {WALL_HEIGHT:.1f}mm tall")
print(f"Invisible tile gap: {INVISIBLE_TILE_GAP:.1f} tiles = {GAP_BETWEEN_PLATES:.1f}mm")
print(f"Wire hole diameter: {WIRE_HOLE_DIAMETER:.1f}mm")
print("="*60)