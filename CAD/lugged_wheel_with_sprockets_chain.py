"""
FreeCAD macro: 12-lug ground-drive wheel with synchronized 13T sprocket

Assembly rules implemented here
-------------------------------
* The ground-drive wheel is an App::Part located at (0, 0, -50) mm.
* The 13T sprocket is centred at (0, 0, 0) mm.
* Both rotate about the global Z axis with exactly the same angle on every
  animation update (1:1 shaft synchronisation).
* The 15T and 21T sprockets and the 58-pitch chain retain the supplied chain
  kinematics.  The wheel is driven directly from Sprocket_13T, not by an
  inferred wheel/sprocket pitch ratio.
"""

import math
import FreeCAD as App
import FreeCADGui as Gui
import Part

try:
    from PySide import QtCore
except ImportError:
    from PySide6 import QtCore


# =============================================================================
# Assembly and wheel dimensions (mm)
# =============================================================================
WHEEL_Z_OFFSET = -50.0
WHEEL_CENTRE_SPACING = 850.0  # centres of the rim + rear-disc envelopes
WHEEL_PHASE_OFFSET = 0.0  # Change only to index the wheel relative to the shaft.

FRONT_DISC_OD = 590.0
FRONT_DISC_THK = 6.0
RIM_OD = 550.0
RIM_WIDTH = 74.0
RIM_WALL_THK = 6.0
REAR_DISC_THK = 6.0
REAR_BOSS_OD = 40.0
REAR_BOSS_LENGTH = 7.0

LUG_COUNT = 12
LUG_LENGTH = 90.0              # radial blade length
LUG_WIDTH = 40.0               # axial blade depth
LUG_THK = 6.0                  # tangential plate thickness
LUG_WELD_OVERLAP = 50.0        # radial length within the front-disc radius
LUG_START_ANGLE = 0.0
LUG_SKEW_ANGLE = 0.0
LUG_OUTER_CHAMFER = 10.0
LUG_HOLE_DIA = 12.0            # visual estimate; change if measured
LUG_HOLE_END_OFFSET = 18.0
LUG_FLANGE_THK = 6.0

STEP_HEIGHT = 12.0             # rearward depth of each step; also 45-degree radial run
OUTER_STEP_RADIUS = 200.0    # outer start of first chamfer
INNER_STEP_RADIUS = 105.0    # outer start of second chamfer

BOSS_OD = 50.0
BOSS_LENGTH = 30.0
CENTRE_BORE_DIA = 30.0
BOSS_CROSS_HOLE_DIA = 12.0
SHAFT_OD = 30.0
# Shared shaft ends flush with both outward-facing front bosses.
SHAFT_LENGTH = (WHEEL_CENTRE_SPACING + RIM_WIDTH + REAR_DISC_THK
                + 2.0 * (FRONT_DISC_THK - 2.0 * STEP_HEIGHT + BOSS_LENGTH))
BOLT_DIA = 12.0
BOLT_LENGTH = 70.0           # under-head length; visual M12 fastener
FASTENER_AF = 19.0          # simplified hex head and nut, across flats
BOLT_HEAD_HEIGHT = 7.5
NUT_HEIGHT = 10.0


# =============================================================================
# Sprocket and chain dimensions (mm)
# =============================================================================
T1 = 28
T2 = 15
T3 = 21
PITCH = 12.700
ROLLER_DIAMETER = 7.77
SPROCKET_BORE_DIAMETER = 10.0
SPROCKET_PLATE_THICKNESS = 4.25
NUM_LINKS = 58
THIRD_SPROCKET_SPACING = 140.0

INNER_WIDTH = 5.72
PIN_DIAMETER = 3.28
LINK_PLATE_THICKNESS = 1.3

R1 = PITCH / (2.0 * math.sin(math.pi / T1))
R2 = PITCH / (2.0 * math.sin(math.pi / T2))
R3 = PITCH / (2.0 * math.sin(math.pi / T3))
ROOT1 = R1 - ROLLER_DIAMETER / 2.0
ROOT2 = R2 - ROLLER_DIAMETER / 2.0
ROOT3 = R3 - ROLLER_DIAMETER / 2.0

V = App.Vector


# =============================================================================
# Wheel geometry
# =============================================================================
def annulus(outer_diameter, inner_diameter, height, z0):
    outer = Part.makeCylinder(outer_diameter / 2.0, height, V(0, 0, z0))
    inner = Part.makeCylinder(
        inner_diameter / 2.0, height + 2.0, V(0, 0, z0 - 1.0)
    )
    return outer.cut(inner)


def make_front_disc():
    """Revolve a disc with two 12 mm rearward drops and 45-degree ramps.

    Each step radius marks the outer start of its ramp. Equal radial and
    axial runs give 45 degrees. The rear profile follows the front profile
    at FRONT_DISC_THK behind it, keeping material beneath all three levels.
    """
    outer = FRONT_DISC_OD / 2.0
    bore = CENTRE_BORE_DIA / 2.0
    depth = STEP_HEIGHT
    if not (depth > 0.0 and FRONT_DISC_THK > 0.0 and
            outer > OUTER_STEP_RADIUS > OUTER_STEP_RADIUS - depth >
            INNER_STEP_RADIUS > INNER_STEP_RADIUS - depth > bore):
        raise ValueError("Disc step radii, depth and bore must leave three flat lands.")
    front = [
        (outer, FRONT_DISC_THK),
        (OUTER_STEP_RADIUS, FRONT_DISC_THK),
        (OUTER_STEP_RADIUS - depth, FRONT_DISC_THK - depth),
        (INNER_STEP_RADIUS, FRONT_DISC_THK - depth),
        (INNER_STEP_RADIUS - depth, FRONT_DISC_THK - 2.0 * depth),
        (bore, FRONT_DISC_THK - 2.0 * depth),
    ]
    back = [(r, z - FRONT_DISC_THK) for r, z in reversed(front)]
    points = [V(r, 0, z) for r, z in front + back]
    points.append(points[0])
    return Part.Face(Part.makePolygon(points)).revolve(V(0, 0, 0), V(0, 0, 1), 360)


def plate_from_xz(points, y0, thickness):
    """Extrude an X-Z plate profile in the tangential (+Y) direction."""
    wire_points = [V(x, y0, z) for x, z in points]
    wire_points.append(wire_points[0])
    return Part.Face(Part.makePolygon(wire_points)).extrude(V(0, thickness, 0))


def add_wheel_feature(doc, parent, name, label, shape, colour):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    obj.ViewObject.ShapeColor = colour
    obj.ViewObject.LineColor = (0.15, 0.15, 0.15)
    parent.addObject(obj)
    return obj


def make_drive_lug(angle_deg):
    """Build one of the 12 front-side bent, radial traction cleats.

    The standing blade is 90 mm radial x 40 mm axial and is normal to the
    front disc.  Its separate flat flange is welded to the front (+Z) face of
    the 590 mm disc.  The whole lug is then indexed around global Z.
    """
    disc_radius = FRONT_DISC_OD / 2.0
    radial_start = disc_radius - LUG_WELD_OVERLAP
    radial_end = radial_start + LUG_LENGTH
    axial_front = FRONT_DISC_THK + LUG_WIDTH

    blade_profile = [
        (radial_start, FRONT_DISC_THK),
        (radial_end - LUG_OUTER_CHAMFER, FRONT_DISC_THK),
        (radial_end, FRONT_DISC_THK + LUG_OUTER_CHAMFER),
        (radial_end, axial_front - LUG_OUTER_CHAMFER),
        (radial_end - LUG_OUTER_CHAMFER, axial_front),
        # Chamfer the inner-end corner on the edge away from the wheel disc.
        (radial_start + LUG_OUTER_CHAMFER, axial_front),
        (radial_start, axial_front - LUG_OUTER_CHAMFER),
    ]
    blade = plate_from_xz(blade_profile, -LUG_THK / 2.0, LUG_THK)

    if LUG_HOLE_DIA > 0.0:
        hole_x = radial_end - LUG_HOLE_END_OFFSET
        hole = Part.makeCylinder(
            LUG_HOLE_DIA / 2.0,
            LUG_THK + 2.0,
            V(hole_x, -LUG_THK / 2.0 - 1.0, FRONT_DISC_THK + LUG_WIDTH / 2.0),
            V(0, 1, 0),
        )
        blade = blade.cut(hole)

    flange = Part.makeBox(
        LUG_WELD_OVERLAP,
        LUG_WIDTH,
        LUG_FLANGE_THK,
        V(radial_start, -LUG_WIDTH / 2.0, FRONT_DISC_THK),
    )
    lug = blade.fuse(flange)
    lug.rotate(V(0, 0, 0), V(0, 0, 1), angle_deg + LUG_SKEW_ANGLE)
    return lug


def hex_prism_x(x0, centre_z, across_flats, length):
    """Simplified hex fastener along local X; no helical thread geometry."""
    radius = across_flats / math.sqrt(3.0)
    points = [V(x0, radius * math.cos(i * math.pi / 3.0),
                centre_z + radius * math.sin(i * math.pi / 3.0))
              for i in range(6)]
    points.append(points[0])
    return Part.Face(Part.makePolygon(points)).extrude(V(length, 0, 0))


def create_ground_drive_wheel(doc):
    """Create the wheel as one movable App::Part, locally centred on the origin."""
    wheel = doc.addObject("App::Part", "GroundDriveWheel")
    wheel.Label = "Twin 12-lug wheels — 850 mm centres, shared shaft"

    disc = make_front_disc()
    add_wheel_feature(
        doc, wheel, "WheelFrontDisc", "Front disc — two rearward 12 mm steps, 45 degree chamfers", disc,
        (0.35, 0.72, 0.56),
    )

    rim = annulus(RIM_OD, RIM_OD - 2.0 * RIM_WALL_THK, RIM_WIDTH, -RIM_WIDTH)
    add_wheel_feature(
        doc, wheel, "WheelRearRim", "Rear rim — 550 mm OD x 74 mm", rim,
        (0.30, 0.55, 0.43),
    )

    # Closing plate sits against the far end of the rim and extends rearward.
    rear_disc = annulus(RIM_OD, CENTRE_BORE_DIA, REAR_DISC_THK,
                        -RIM_WIDTH - REAR_DISC_THK)
    add_wheel_feature(
        doc, wheel, "WheelRearDisc", "Rear closing disc — 550 mm OD x 6 mm, 30 mm bore",
        rear_disc, (0.35, 0.72, 0.56),
    )

    # Rear boss projects outward (-Z) from the closing disc.
    rear_boss = annulus(REAR_BOSS_OD, CENTRE_BORE_DIA, REAR_BOSS_LENGTH,
                        -RIM_WIDTH - REAR_DISC_THK - REAR_BOSS_LENGTH)
    add_wheel_feature(
        doc, wheel, "WheelRearBoss", "Rear boss — OD 40, ID 30, length 7 mm",
        rear_boss, (0.42, 0.30, 0.18),
    )

    # Plain boss seated directly on the recessed centre of the disc.
    hub_z = FRONT_DISC_THK - 2.0 * STEP_HEIGHT
    cross_z = hub_z + BOSS_LENGTH / 2.0
    boss = annulus(BOSS_OD, CENTRE_BORE_DIA, BOSS_LENGTH, hub_z)
    cross_hole = Part.makeCylinder(
        BOSS_CROSS_HOLE_DIA / 2.0, BOSS_OD + 2.0,
        V(-BOSS_OD / 2.0 - 1.0, 0, cross_z), V(1, 0, 0),
    )
    boss = boss.cut(cross_hole)
    add_wheel_feature(
        doc, wheel, "WheelCentreBoss", "Plain boss — OD 50, ID 30, length 30 mm", boss,
        (0.42, 0.30, 0.18),
    )

    # Solid shaft: deliberately NOT cut by cross_hole or by the bolt.
    # End the shaft at the front (+Z) face of the boss.
    shaft = Part.makeCylinder(
        SHAFT_OD / 2.0, SHAFT_LENGTH, V(0, 0, hub_z + BOSS_LENGTH - SHAFT_LENGTH)
    )
    add_wheel_feature(
        doc, wheel, "WheelShaft", "Shared solid shaft — OD 30 x {:.1f} mm, undrilled".format(SHAFT_LENGTH), shaft,
        (0.65, 0.67, 0.70),
    )

    # M12 visual assembly: nominal shank/bore, simplified hex head and nut.
    # The bolt intentionally intersects the undrilled shaft at this design stage.
    bolt_start = -BOSS_OD / 2.0
    bolt_shank = Part.makeCylinder(
        BOLT_DIA / 2.0, BOLT_LENGTH, V(bolt_start, 0, cross_z), V(1, 0, 0)
    )
    bolt_head = hex_prism_x(bolt_start - BOLT_HEAD_HEIGHT, cross_z,
                            FASTENER_AF, BOLT_HEAD_HEIGHT)
    add_wheel_feature(
        doc, wheel, "WheelLockBolt", "M12 x 70 locking bolt — simplified threads", 
        bolt_shank.fuse(bolt_head), (0.72, 0.74, 0.77),
    )
    nut_x = BOSS_OD / 2.0
    nut = hex_prism_x(nut_x, cross_z, FASTENER_AF, NUT_HEIGHT)
    nut = nut.cut(Part.makeCylinder(BOLT_DIA / 2.0, NUT_HEIGHT + 2.0,
                                   V(nut_x - 1.0, 0, cross_z), V(1, 0, 0)))
    add_wheel_feature(
        doc, wheel, "WheelLockNut", "M12 locking nut — simplified threads", nut,
        (0.62, 0.64, 0.67),
    )

    lug_group = doc.addObject("App::DocumentObjectGroup", "WheelLugs")
    lug_group.Label = "12 front-side bent radial lugs — 30 degree pitch"
    wheel.addObject(lug_group)
    pitch_angle = 360.0 / LUG_COUNT
    for number in range(LUG_COUNT):
        angle = LUG_START_ANGLE + number * pitch_angle
        lug = doc.addObject("Part::Feature", "WheelLug_{:02d}".format(number + 1))
        lug.Label = "Wheel lug {:02d} — {:.1f} degrees".format(number + 1, angle)
        lug.Shape = make_drive_lug(angle)
        lug.ViewObject.ShapeColor = (0.60, 0.28, 0.16)
        lug.ViewObject.LineColor = (0.15, 0.10, 0.08)
        lug_group.addObject(lug)

    # Both rim + rear-disc envelopes are RIM_WIDTH + REAR_DISC_THK deep.
    # Flipping local Z moves the second envelope centre toward +Z, so its
    # origin needs the centre spacing PLUS one complete envelope depth.
    second_z = -WHEEL_CENTRE_SPACING - RIM_WIDTH - REAR_DISC_THK
    # Snapshot before cloning; FreeCAD and the headless viewer expose these
    # collections under different names. Copy only Part::Feature solids:
    # groups can expose an aggregate Shape but have no ShapeColor.
    originals = list(doc.Objects if hasattr(doc, "Objects") else doc.objects)
    for original in originals:
        if (original.TypeId != "Part::Feature" or
                not original.Name.startswith("Wheel") or
                original.Name == "WheelShaft" or not hasattr(original, "Shape")):
            continue
        copied_shape = original.Shape.copy()
        copied_shape.rotate(V(0, 0, 0), V(0, 1, 0), 180.0)
        copied_shape.translate(V(0, 0, second_z))
        add_wheel_feature(
            doc, wheel, "WheelSecond" + original.Name[5:],
            "Second wheel — " + original.Label, copied_shape,
            original.ViewObject.ShapeColor,
        )

    # This is the requested -50 mm Z movement.  Child geometry remains local,
    # so one rotation of this container drives every wheel component together.
    wheel.Placement = App.Placement(V(0, 0, WHEEL_Z_OFFSET), App.Rotation())
    return wheel


# =============================================================================
# Three-sprocket chain geometry and path
# =============================================================================
def make_left_outer_tangent(start_center, end_center, start_radius, end_radius):
    dx = end_center.x - start_center.x
    dy = end_center.y - start_center.y
    centre_distance = math.hypot(dx, dy)
    radius_difference = end_radius - start_radius
    if centre_distance <= abs(radius_difference):
        raise ValueError("Sprocket centres are too close for an external chain tangent.")

    ux = dx / centre_distance
    uy = dy / centre_distance
    left_x = -uy
    left_y = ux
    normal_parallel = -radius_difference / centre_distance
    normal_perpendicular = math.sqrt(1.0 - normal_parallel * normal_parallel)
    nx = normal_parallel * ux + normal_perpendicular * left_x
    ny = normal_parallel * uy + normal_perpendicular * left_y

    return {
        "start_point": V(start_center.x + start_radius * nx, start_center.y + start_radius * ny, 0),
        "end_point": V(end_center.x + end_radius * nx, end_center.y + end_radius * ny, 0),
        "normal_angle": math.atan2(ny, nx),
        "length": math.sqrt(centre_distance * centre_distance - radius_difference * radius_difference),
    }


def build_chain_path(upper_right_x):
    centres = [V(0, 0, 0), V(upper_right_x, 0, 0), V(0, -THIRD_SPROCKET_SPACING, 0)]
    radii = [R1, R2, R3]
    tangents = [
        make_left_outer_tangent(centres[i], centres[(i + 1) % 3], radii[i], radii[(i + 1) % 3])
        for i in range(3)
    ]
    segments = []
    arc_segments = [None, None, None]
    path_distance = 0.0
    two_pi = 2.0 * math.pi

    for i in range(3):
        incoming = tangents[(i - 1) % 3]
        outgoing = tangents[i]
        arc_start = incoming["normal_angle"]
        arc_end = outgoing["normal_angle"]
        clockwise_sweep = (arc_start - arc_end) % two_pi
        arc_length = radii[i] * clockwise_sweep
        arc = {
            "kind": "arc", "sprocket_index": i, "start": path_distance,
            "end": path_distance + arc_length, "centre": centres[i],
            "radius": radii[i], "start_angle": arc_start, "length": arc_length,
        }
        segments.append(arc)
        arc_segments[i] = arc
        path_distance += arc_length

        straight = {
            "kind": "straight", "start": path_distance,
            "end": path_distance + outgoing["length"],
            "start_point": outgoing["start_point"], "end_point": outgoing["end_point"],
            "length": outgoing["length"],
        }
        segments.append(straight)
        path_distance += outgoing["length"]

    return {"centres": centres, "segments": segments, "arc_segments": arc_segments, "length": path_distance}


def create_sprocket(doc, name, teeth, pitch_radius, root_radius):
    outer_radius = pitch_radius + 2.3
    sprocket = Part.makeCylinder(outer_radius, SPROCKET_PLATE_THICKNESS)
    scale_y = 0.85

    p_root = V(root_radius, 0, 0)
    p_a = V(pitch_radius - 1.6, 2.77 * scale_y, 0)
    p_b = V(pitch_radius - 1.6, -2.77 * scale_y, 0)
    p_up = V(pitch_radius + 1.75, 4.5 * scale_y, 0)
    p_low = V(pitch_radius + 1.75, -4.5 * scale_y, 0)
    p_3 = V(pitch_radius + 5.1, 5.5 * scale_y, 0)
    p_4 = V(pitch_radius + 5.1, -5.5 * scale_y, 0)

    arc_root = Part.Arc(p_b, p_root, p_a).toShape()
    arc_up = Part.Arc(p_a, p_up, p_3).toShape()
    arc_low = Part.Arc(p_4, p_low, p_b).toShape()
    line_out = Part.LineSegment(p_3, p_4).toShape()
    wedge = Part.Face(Part.Wire([arc_root, arc_up, line_out, arc_low])).extrude(
        V(0, 0, SPROCKET_PLATE_THICKNESS + 2.0)
    )
    wedge.translate(V(0, 0, -1.0))

    for index in range(teeth):
        cutter = wedge.copy()
        cutter.rotate(V(0, 0, 0), V(0, 0, 1), index * 360.0 / teeth)
        sprocket = sprocket.cut(cutter)

    bore = Part.makeCylinder(SPROCKET_BORE_DIAMETER / 2.0, SPROCKET_PLATE_THICKNESS + 2.0, V(0, 0, -1.0))
    obj = doc.addObject("Part::Feature", name)
    obj.Label = name.replace("_", " ")
    obj.Shape = sprocket.cut(bore)
    obj.ViewObject.ShapeColor = (0.20, 0.20, 0.20)
    return obj


def create_link_plate(thickness, z_offset):
    radius = 4.0
    cyl1 = Part.makeCylinder(radius, thickness, V(0, 0, z_offset))
    cyl2 = Part.makeCylinder(radius, thickness, V(PITCH, 0, z_offset))
    box = Part.makeBox(PITCH, radius * 2.0, thickness, V(0, -radius, z_offset))
    return cyl1.fuse(cyl2).fuse(box)


def get_path_pos(distance, segments, total_length):
    distance = distance % total_length
    for segment in segments:
        if distance < segment["end"]:
            local = distance - segment["start"]
            if segment["kind"] == "arc":
                angle = segment["start_angle"] - local / segment["radius"]
                centre = segment["centre"]
                return V(
                    centre.x + segment["radius"] * math.cos(angle),
                    centre.y + segment["radius"] * math.sin(angle), 0,
                )
            return segment["start_point"] + (
                segment["end_point"] - segment["start_point"]
            ) * (local / segment["length"])

    first = segments[0]
    return first["centre"] + V(
        first["radius"] * math.cos(first["start_angle"]),
        first["radius"] * math.sin(first["start_angle"]), 0,
    )


# =============================================================================
# Build the combined document
# =============================================================================
doc = App.newDocument("LuggedWheel_13T_Sprocket_Chain")

# The wheel and Sprocket_13T have the same X/Y shaft centre.  The wheel is
# offset only in Z by the requested -50 mm.
ground_drive_wheel = create_ground_drive_wheel(doc)

# Solve the 15T centre location for an exact 58-link loop.
target_length = NUM_LINKS * PITCH
upper_right_x = 85.0
for _ in range(50):
    test_path = build_chain_path(upper_right_x)
    error = test_path["length"] - target_length
    if abs(error) < 1.0e-8:
        break
    step = 0.01
    slope = (build_chain_path(upper_right_x + step)["length"] - build_chain_path(upper_right_x - step)["length"]) / (2.0 * step)
    upper_right_x -= error / slope
else:
    raise RuntimeError("Unable to solve the three-sprocket chain centre distance.")

chain_path = build_chain_path(upper_right_x)
centres = chain_path["centres"]
path_segments = chain_path["segments"]
arc_segments = chain_path["arc_segments"]
total_chain_length = chain_path["length"]

sprocket_13t = create_sprocket(doc, "Sprocket_13T", T1, R1, ROOT1)
sprocket_15t = create_sprocket(doc, "Sprocket_15T", T2, R2, ROOT2)
sprocket_21t = create_sprocket(doc, "Sprocket_21T", T3, R3, ROOT3)
sprockets = [sprocket_13t, sprocket_15t, sprocket_21t]
for sprocket, centre in zip(sprockets, centres):
    sprocket.Placement.Base = centre

# Chain-link solids and objects.
inner_plate_z1 = SPROCKET_PLATE_THICKNESS / 2.0 + INNER_WIDTH / 2.0
inner_plate_z2 = SPROCKET_PLATE_THICKNESS / 2.0 - INNER_WIDTH / 2.0 - LINK_PLATE_THICKNESS
inner_link = create_link_plate(LINK_PLATE_THICKNESS, inner_plate_z1).fuse(
    create_link_plate(LINK_PLATE_THICKNESS, inner_plate_z2)
).fuse(
    Part.makeCylinder(ROLLER_DIAMETER / 2.0, INNER_WIDTH, V(0, 0, SPROCKET_PLATE_THICKNESS / 2.0 - INNER_WIDTH / 2.0))
).fuse(
    Part.makeCylinder(ROLLER_DIAMETER / 2.0, INNER_WIDTH, V(PITCH, 0, SPROCKET_PLATE_THICKNESS / 2.0 - INNER_WIDTH / 2.0))
)

outer_plate_z1 = inner_plate_z1 + LINK_PLATE_THICKNESS + 0.2
outer_plate_z2 = inner_plate_z2 - LINK_PLATE_THICKNESS - 0.2
pin_length = (outer_plate_z1 - outer_plate_z2) + LINK_PLATE_THICKNESS + 1.0
outer_link = create_link_plate(LINK_PLATE_THICKNESS, outer_plate_z1).fuse(
    create_link_plate(LINK_PLATE_THICKNESS, outer_plate_z2)
).fuse(
    Part.makeCylinder(PIN_DIAMETER / 2.0, pin_length, V(0, 0, outer_plate_z2 - 0.5))
).fuse(
    Part.makeCylinder(PIN_DIAMETER / 2.0, pin_length, V(PITCH, 0, outer_plate_z2 - 0.5))
)

links = []
for index in range(NUM_LINKS):
    link = doc.addObject("Part::Feature", "ChainLink_{:02d}".format(index))
    link.Shape = inner_link if index % 2 == 0 else outer_link
    link.ViewObject.ShapeColor = (0.70, 0.70, 0.70) if index % 2 == 0 else (0.50, 0.50, 0.50)
    links.append(link)

sprocket_phase_offsets = [
    math.degrees(arc["start_angle"] + arc["start"] / arc["radius"])
    for arc in arc_segments
]


# =============================================================================
# Animation: Sprocket_13T and the 12-lug wheel are rigidly synchronous
# =============================================================================
animation_offset = 0.0


def apply_simulation_state():
    """Place links and rotate every driven part using the current chain offset."""
    for index, link in enumerate(links):
        d1 = (index * PITCH + animation_offset) % total_chain_length
        d2 = ((index + 1) * PITCH + animation_offset) % total_chain_length
        p1 = get_path_pos(d1, path_segments, total_chain_length)
        p2 = get_path_pos(d2, path_segments, total_chain_length)
        yaw = math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x))
        link.Placement = App.Placement(p1, App.Rotation(V(0, 0, 1), yaw))

    sprocket_angles = [
        sprocket_phase_offsets[0] - math.degrees(animation_offset / R1),
        sprocket_phase_offsets[1] - math.degrees(animation_offset / R2),
        sprocket_phase_offsets[2] - math.degrees(animation_offset / R3),
    ]
    for sprocket, angle in zip(sprockets, sprocket_angles):
        sprocket.Placement.Rotation = App.Rotation(V(0, 0, 1), angle)

    # Exact 1:1 synchronisation with the 13T sprocket, retaining Z = -50 mm.
    ground_drive_wheel.Placement = App.Placement(
        V(0, 0, WHEEL_Z_OFFSET),
        App.Rotation(V(0, 0, 1), sprocket_angles[0] + WHEEL_PHASE_OFFSET),
    )


def update_simulation():
    global animation_offset
    animation_offset += 1.0
    apply_simulation_state()
    Gui.updateGui()


doc.recompute()
apply_simulation_state()
doc.recompute()

Gui.activeDocument().activeView().viewAxonometric()
Gui.SendMsgToActiveView("ViewFit")

# Stop timers left behind by an earlier execution before making a new one.
# The public handle is deliberately App.sim_timer, so the console command
# ``App.sim_timer.stop()`` always addresses the timer driving this macro.
for timer_name in ("sim_timer", "lugged_wheel_chain_timer"):
    old_timer = getattr(App, timer_name, None)
    if old_timer is not None:
        old_timer.stop()

App.sim_timer = QtCore.QTimer()
App.sim_timer.timeout.connect(update_simulation)
App.sim_timer.start(10)

# Backward-compatible alias for the stop command printed by older versions.
App.lugged_wheel_chain_timer = App.sim_timer
App.Console.PrintMessage(
    "Combined wheel/sprocket simulation running. Stop with: "
    "App.sim_timer.stop()\n"
)
