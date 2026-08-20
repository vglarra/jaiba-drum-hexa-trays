import bpy, bmesh, math, os
from mathutils import Vector

print("=== FLAT HEX PLATES — WITH INVISIBLE TILE GAP ===")
print("=" * 60)

# ---- CONFIGURABLE PARAMETERS --------------------
# Tile size
HEX_FLAT_WIDTH = 84.0  # Flat-to-flat width of hex tiles

# Hole positions
HOLE_RADIUS = 28.0  # Distance from tile center to hole center (mm)
# For reference: APOTHEM = HEX_FLAT_WIDTH/2 = 42.0mm
# So HOLE_RADIUS = 28.0 means holes are 14.0mm from the edge

PLATE_H = 2.0  # Plate thickness (also used for perimeter)

# ---- PERIMETER CONTOUR PARAMETERS --------------------
PERIMETER_THICKNESS = 3.0  # Extra thickness around the plate (mm)
# Total plate width = HEX_FLAT_WIDTH + 2 * PERIMETER_THICKNESS

# ---- INVISIBLE TILE GAP --------------------
# This creates a gap by shifting the right plate as if there's an invisible tile
# between the plates. Set to 0 for no gap, HEX_FLAT_WIDTH for one tile gap, etc.
INVISIBLE_TILE_GAP = 1.0  # Number of invisible tiles between plates
# 0 = no gap, 1 = one tile width gap, 0.5 = half tile gap, etc.

# Calculate actual gap in mm
TILE_SPACING = 1.5 * HEX_FLAT_WIDTH  # Horizontal spacing between hex tile centers
GAP_BETWEEN_PLATES = INVISIBLE_TILE_GAP * TILE_SPACING

PIN_DIAMETER = 15.0
PIN_RADIUS = PIN_DIAMETER / 2.0
PIN_DEPTH = 40.0
PIN_CLEARANCE = 0.2
PIN_Z = 20.0

# ---- WIRE HOLE CONFIGURATION --------------------
WIRE_HOLE_DIAMETER = 12.0  # Diameter of wire holes (mm)
WIRE_HOLE_RADIUS = WIRE_HOLE_DIAMETER / 2.0

# Wire hole position - which face to put them on
# 0° = right face, 60° = upper-right, 120° = upper-left
# 180° = left face, 240° = lower-left, 300° = lower-right
WIRE_HOLE_ANGLE = 180  # 180° means pointing to the left

# ---- Direction mapping --------------------
DIRECTION_NAMES = {
    0: "Right",
    60: "Upper-Right",
    120: "Upper-Left",
    180: "Left",
    240: "Lower-Left",
    300: "Lower-Right"
}

# ---- Derived geometry (calculated automatically) ----
S  = HEX_FLAT_WIDTH / math.sqrt(3)  # Circumradius
H  = S * math.sqrt(3)  # Width
V  = S * 1.5  # Height
APOTHEM = HEX_FLAT_WIDTH / 2.0  # Center to edge midpoint

# Total width of a tile including perimeter
TOTAL_WIDTH = HEX_FLAT_WIDTH + 2 * PERIMETER_THICKNESS
TOTAL_S = TOTAL_WIDTH / math.sqrt(3)  # Circumradius of tile with perimeter

# Calculate the diagonal extent
DIAGONAL_EXTENT = TOTAL_S * 2  # Full diagonal (corner to corner)

print(f"Tile geometry:")
print(f"  HEX_FLAT_WIDTH: {HEX_FLAT_WIDTH:.3f}mm")
print(f"  APOTHEM (center to edge): {APOTHEM:.3f}mm")
print(f"  HOLE_RADIUS: {HOLE_RADIUS:.3f}mm")
print(f"  Distance from edge to hole: {APOTHEM - HOLE_RADIUS:.1f}mm")
print(f"  PLATE_H: {PLATE_H:.1f}mm")
print(f"  Tile spacing (center to center): {TILE_SPACING:.1f}mm")
print(f"")
print(f"Perimeter contour:")
print(f"  PERIMETER_THICKNESS: {PERIMETER_THICKNESS:.1f}mm")
print(f"  Total width with perimeter: {TOTAL_WIDTH:.1f}mm")
print(f"  Diagonal extent: {DIAGONAL_EXTENT:.1f}mm")
print(f"")
print(f"Invisible tile gap:")
print(f"  INVISIBLE_TILE_GAP: {INVISIBLE_TILE_GAP:.1f} tiles")
print(f"  Actual gap: {GAP_BETWEEN_PLATES:.1f}mm")
print(f"  (This is like having {INVISIBLE_TILE_GAP:.1f} invisible tiles between the plates)")
print(f"")
print(f"Wire holes:")
print(f"  Wire hole diameter: {WIRE_HOLE_DIAMETER:.1f}mm")
print(f"  Wire hole direction: {DIRECTION_NAMES.get(WIRE_HOLE_ANGLE, f'{WIRE_HOLE_ANGLE}°')} ({WIRE_HOLE_ANGLE}°)")
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

# Assign tiles with gap
left_grid = []
right_grid = []
for cx, cy in grid_orig:
    if cx < SPLIT_X:
        left_grid.append((cx, cy))
    else:
        # Shift right plate by the gap (creates space for invisible tiles)
        right_grid.append((cx + GAP_BETWEEN_PLATES, cy))

print(f"Split at X = {SPLIT_X:.3f}")
print(f"Left: {len(left_grid)} tiles, Right: {len(right_grid)} tiles")
print(f"Gap between plates: {GAP_BETWEEN_PLATES:.1f}mm")
print("=" * 60)

# ---- Pin assignments ------------------------
PIN_ASSIGNMENTS = {
    ('L', 1): (0, 'Pair1'),
    ('L', 3): (60, 'Pair2'),
    ('L', 5): (300, 'Pair3'),
    ('L', 6): (240, 'Pair4'),
    ('R', 0): (180, 'Pair1'),
    ('R', 2): (120, 'Pair2'),
    ('R', 5): (240, 'Pair3'),
    ('R', 7): (60, 'Pair4'),
}

print("Pin assignments:")
for key, (angle, pair) in PIN_ASSIGNMENTS.items():
    print(f"  {key}: face at {angle}° ({pair})")
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

# ---- Builders (same as before) -------------------------
def get_hole_position(cx, cy, angle_deg):
    """Get hole position at the given angle using HOLE_RADIUS"""
    angle_rad = math.radians(angle_deg)
    x = cx + HOLE_RADIUS * math.cos(angle_rad)
    y = cy + HOLE_RADIUS * math.sin(angle_rad)
    return x, y

def get_hex_corners(cx, cy, flat_width):
    """Get the 6 vertices of a hex tile with given flat width"""
    s = flat_width / math.sqrt(3)
    angles = [math.radians(30 + 60*i) for i in range(6)]
    return [(cx + s*math.cos(a), cy + s*math.sin(a)) for a in angles]

def make_hex_plate_with_perimeter(grid_tiles, solid_name):
    """Create hex plate with perimeter contour (same height as main plate)"""
    print(f"\nBuilding {solid_name} with {len(grid_tiles)} tiles")
    print(f"  Perimeter thickness: {PERIMETER_THICKNESS}mm (same height as plate: {PLATE_H}mm)")
    
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
    
    for idx, (cx, cy) in enumerate(grid_tiles):
        main_corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH)
        perim_corners = get_hex_corners(cx, cy, HEX_FLAT_WIDTH + 2*PERIMETER_THICKNESS)
        
        # Create main body side walls
        for i in range(6):
            j = (i+1) % 6
            b0 = gv(main_corners[i][0], main_corners[i][1], 0.0)
            b1 = gv(main_corners[j][0], main_corners[j][1], 0.0)
            t0 = gv(main_corners[i][0], main_corners[i][1], PLATE_H)
            t1 = gv(main_corners[j][0], main_corners[j][1], PLATE_H)
            try: bm.faces.new([b0, b1, t1, t0])
            except: pass
        
        # Create perimeter contour
        for i in range(6):
            j = (i+1) % 6
            m0 = main_corners[i]; m1 = main_corners[j]
            p0 = perim_corners[i]; p1 = perim_corners[j]
            
            b_m0 = gv(m0[0], m0[1], 0.0); b_m1 = gv(m1[0], m1[1], 0.0)
            b_p0 = gv(p0[0], p0[1], 0.0); b_p1 = gv(p1[0], p1[1], 0.0)
            t_m0 = gv(m0[0], m0[1], PLATE_H); t_m1 = gv(m1[0], m1[1], PLATE_H)
            t_p0 = gv(p0[0], p0[1], PLATE_H); t_p1 = gv(p1[0], p1[1], PLATE_H)
            
            # Outer perimeter wall
            try: bm.faces.new([b_p0, b_p1, t_p1, t_p0])
            except: pass
            # Top perimeter surface
            try: bm.faces.new([t_m0, t_m1, t_p1, t_p0])
            except: pass
            # Inner perimeter wall
            try: bm.faces.new([b_m0, b_m1, t_m1, t_m0])
            except: pass
        
        # Bottom faces
        bottom_verts = [gv(c[0], c[1], 0.0) for c in main_corners]
        try: bm.faces.new(list(reversed(bottom_verts)))
        except: pass
        
        for i in range(6):
            j = (i+1) % 6
            b_m = gv(main_corners[i][0], main_corners[i][1], 0.0)
            b_n = gv(main_corners[j][0], main_corners[j][1], 0.0)
            b_p = gv(perim_corners[i][0], perim_corners[i][1], 0.0)
            b_q = gv(perim_corners[j][0], perim_corners[j][1], 0.0)
            try: bm.faces.new([b_p, b_q, b_n, b_m])
            except: pass
        
        # Top faces
        top_verts = [gv(c[0], c[1], PLATE_H) for c in main_corners]
        try: bm.faces.new(top_verts)
        except: pass
        
        for i in range(6):
            j = (i+1) % 6
            t_m = gv(main_corners[i][0], main_corners[i][1], PLATE_H)
            t_n = gv(main_corners[j][0], main_corners[j][1], PLATE_H)
            t_p = gv(perim_corners[i][0], perim_corners[i][1], PLATE_H)
            t_q = gv(perim_corners[j][0], perim_corners[j][1], PLATE_H)
            try: bm.faces.new([t_m, t_n, t_q, t_p])
            except: pass
        
        if idx < 3 or idx >= len(grid_tiles)-3:
            print(f"  Tile {idx}: center=({cx:.3f}, {cy:.3f})")
    
    print(f"  Created {len(grid_tiles)} tiles with perimeter contour")
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    return obj

def make_wire_hole_cutter(name, cx, cy):
    """Wire hole - consistent position for all tiles with configurable diameter"""
    hx, hy = get_hole_position(cx, cy, WIRE_HOLE_ANGLE)
    print(f"    Wire hole at ({hx:.3f}, {hy:.3f}) (angle: {WIRE_HOLE_ANGLE}°, ⌀{WIRE_HOLE_DIAMETER:.1f}mm)")
    
    dz = 0.0
    bottom=-2.0
    top=dz+PLATE_H+2.0
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

def make_hole_cutter(name, hole_x, hole_y, hole_z, depth, radius):
    print(f"    Pin hole at ({hole_x:.3f}, {hole_y:.3f}), z={hole_z:.3f}")
    
    mesh=bpy.data.meshes.new(name+"_mesh")
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bm=bmesh.new()
    segs=64
    half=depth/2.0+2.0
    bv,tv=[],[]
    for i in range(segs):
        a=2*math.pi*i/segs
        y_off=radius*math.cos(a)
        z_off=radius*math.sin(a)
        bv.append(bm.verts.new((-half,y_off,z_off)))
        tv.append(bm.verts.new((half,y_off,z_off)))
    for i in range(segs):
        j=(i+1)%segs
        bm.faces.new([bv[i],bv[j],tv[j],tv[i]])
    bm.faces.new(list(reversed(bv)))
    bm.faces.new(tv)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    
    obj.location=Vector((hole_x, hole_y, hole_z))
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
    zero_area   = sum(1 for f in bm.faces if f.calc_area() < 1e-5)
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
    bpy.ops.object.text_add(location=(cx, cy, PLATE_H + 1.0))
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

        key = (half_char, i)
        if key in PIN_ASSIGNMENTS:
            angle, pair_label = PIN_ASSIGNMENTS[key]
            print(f"    Pin assignment: face at {angle}° ({pair_label})")
            
            hole_x, hole_y = get_hole_position(cx, cy, angle)
            dist = math.hypot(hole_x - cx, hole_y - cy)
            print(f"    Hole position at ({hole_x:.3f}, {hole_y:.3f})")
            print(f"    Distance from center: {dist:.3f}mm (target: {HOLE_RADIUS:.1f}mm)")
            
            r = PIN_RADIUS + PIN_CLEARANCE
            pin_z = PIN_Z
            if pair_label in ['Pair1', 'Pair4']:
                pin_z = PIN_Z - 5.0
            
            hole = make_hole_cutter(f"Hole_{tag}", hole_x, hole_y, pin_z, PIN_DEPTH, r)
            apply_transforms(hole)
            safe_cut(f"{tag} {pair_label} pin", obj, hole, primary='EXACT')
            bpy.data.objects.remove(hole, do_unlink=True)

        add_tile_label(tag, cx, cy)
    
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

export_obj(left_obj,  "flat_hex_plate_LEFT.stl")
export_obj(right_obj, "flat_hex_plate_RIGHT.stl")

print("\n" + "="*60)
print("=== DONE ===")
print(f"Left plate: {len(left_grid)} tiles")
print(f"Right plate: {len(right_grid)} tiles")
print(f"Total tiles: {len(left_grid) + len(right_grid)}")
print(f"Tile size: {HEX_FLAT_WIDTH:.1f}mm flat-to-flat")
print(f"Perimeter thickness: {PERIMETER_THICKNESS:.1f}mm")
print(f"Total width with perimeter: {TOTAL_WIDTH:.1f}mm")
print(f"Invisible tile gap: {INVISIBLE_TILE_GAP:.1f} tiles = {GAP_BETWEEN_PLATES:.1f}mm")
print(f"Hole radius from center: {HOLE_RADIUS:.1f}mm")
print(f"Wire hole diameter: {WIRE_HOLE_DIAMETER:.1f}mm")
print(f"Wire hole direction: {DIRECTION_NAMES.get(WIRE_HOLE_ANGLE, f'{WIRE_HOLE_ANGLE}°')} ({WIRE_HOLE_ANGLE}°)")
print("="*60)