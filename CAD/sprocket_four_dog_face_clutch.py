"""FreeCAD macro: 28-tooth sprocket with four ramped overrunning face dogs.

All dimensions are millimetres. Run in FreeCAD with Macro > Macros, or execute
this file from FreeCAD's Python console. Geometry helpers also work headlessly.

SUPPLIED: 28 teeth, 12.7 pitch, bore 30.2, plate 4.2, dog OD 55,
finished dog projection 13.5 after a 5.5 top cut (original peak 19.0),
dog base height 4.0, rear boss OD 47 / ID 30.2 / length 10.5,
and mating dog-clutch pin diameter 8.0.
Datum: rear plate face Z=0; front plate face Z=4.2. Dogs project in +Z;
rear boss projects in -Z. Overall axial length is 28.2 mm.

PHOTO-BASED ASSUMPTIONS (editable below): roller diameter 7.77, tooth
addendum 3.0, tooth-tip width 1.8, pin clearance 0.2,
and ramp handedness. The tooth flanks and dog ramps are approximate visual
geometry, not a certified chain-tooth or mating-clutch manufacturing profile.
Dog ID is assumed to continue the 30.2 bore. Dog height is measured from the
front plate face, not from the rear of the plate or the top of the dog base.
"""
import math
import FreeCAD as App
import Part

TEETH = 28
PITCH = 12.7
BORE_DIA = 30.2
PLATE_THICKNESS = 4.2
DOG_COUNT = 4
DOG_OD = 55.0
DOG_HEIGHT = 12.5       # Finished dog height AFTER flattening, above plate.
DOG_TOP_CUT = 5.5       # Material removed from the original ramp peak.
DOG_ORIGINAL_HEIGHT = DOG_HEIGHT + DOG_TOP_CUT
DOG_FINISHED_HEIGHT = DOG_HEIGHT
REAR_BOSS_OD = 47.0
REAR_BOSS_HEIGHT = 10.5

# Assumed details: adjust after measuring the actual part or mating clutch.
ROLLER_DIA = 7.77
TOOTH_ADDENDUM = 3.0
TOOTH_TIP_WIDTH = 1.8
ROOT_ARC_HALF_ANGLE = 65.0
DOG_BASE_HEIGHT = 4.0
DOG_RAMP_LOW_HEIGHT = DOG_BASE_HEIGHT + 0.3
DOG_PIN_DIA = 8.0        # Mating clutch pin, independent of chain ROLLER_DIA.
DOG_PIN_CLEARANCE = 0.2  # Total clearance across gap (editable).
# Radial-sided gaps widen outward. Size their narrowest opening at the bore
# for the pin plus clearance; this replaces the photo-estimated 8-degree gap.
DOG_GAP_ANGLE = math.degrees(2.0 * math.asin(
    (DOG_PIN_DIA + DOG_PIN_CLEARANCE) / BORE_DIA))
DOG_PHASE_ANGLE = 0.0
DOG_HANDEDNESS = 1        # +1 rises counterclockwise viewed from the dog side.
DOG_RAMP_SEGMENTS = 48    # Ruled loft approximation to a circumferential ramp.

V = App.Vector


def rotated(x, y, angle, z=0.0):
    return V(x * math.cos(angle) - y * math.sin(angle),
             x * math.sin(angle) + y * math.cos(angle), z)


def ring(outer_dia, inner_dia, height, z):
    return Part.makeCylinder(outer_dia / 2, height, V(0, 0, z)).cut(
        Part.makeCylinder(inner_dia / 2, height + 2, V(0, 0, z - 1)))


def make_sprocket_plate():
    """28 circular roller seats joined by approximate flanks and rounded tips."""
    pitch_radius = PITCH / (2 * math.sin(math.pi / TEETH))
    tip_radius = pitch_radius + TOOTH_ADDENDUM
    roller_radius = ROLLER_DIA / 2
    root_half_angle = math.radians(ROOT_ARC_HALF_ANGLE)
    tip_half_angle = TOOTH_TIP_WIDTH / (2 * tip_radius)
    step = 2 * math.pi / TEETH
    seat_x = pitch_radius - roller_radius * math.cos(root_half_angle)
    seat_y = roller_radius * math.sin(root_half_angle)
    edges = []
    for i in range(TEETH):
        angle = i * step
        lower = rotated(seat_x, -seat_y, angle)
        root = rotated(pitch_radius - roller_radius, 0, angle)
        upper = rotated(seat_x, seat_y, angle)
        tip_mid_angle = angle + step / 2
        tip_a = rotated(tip_radius, 0, tip_mid_angle - tip_half_angle)
        tip_mid = rotated(tip_radius, 0, tip_mid_angle)
        tip_b = rotated(tip_radius, 0, tip_mid_angle + tip_half_angle)
        next_lower = rotated(seat_x, -seat_y, angle + step)
        edges.extend([
            Part.Arc(lower, root, upper).toShape(),
            Part.makeLine(upper, tip_a),
            Part.Arc(tip_a, tip_mid, tip_b).toShape(),
            Part.makeLine(tip_b, next_lower),
        ])
    plate = Part.Face(Part.Wire(edges)).extrude(V(0, 0, PLATE_THICKNESS))
    bore = Part.makeCylinder(BORE_DIA / 2, PLATE_THICKNESS + 2, V(0, 0, -1))
    return plate.cut(bore)


def make_dog(index):
    """Annular ramp with a steep drive face and a rising overrun face.

    Radial rectangular sections keep the ramp height equal across its width.
    Adjacent sections form a fine ruled approximation to a helical ramp.
    """
    span = 360.0 / DOG_COUNT - DOG_GAP_ANGLE
    start = DOG_PHASE_ANGLE + index * 360.0 / DOG_COUNT
    bottom = PLATE_THICKNESS + DOG_BASE_HEIGHT - 0.05  # Union overlap.
    sections = []
    fractions = [i / DOG_RAMP_SEGMENTS for i in range(DOG_RAMP_SEGMENTS + 1)]
    # Include the exact ramp/flat junction, avoiding a sloping transition strip.
    junction = (DOG_FINISHED_HEIGHT - DOG_RAMP_LOW_HEIGHT) / (DOG_ORIGINAL_HEIGHT - DOG_RAMP_LOW_HEIGHT)
    if 0.0 < junction < 1.0:
        fractions.append(junction)
    for fraction in sorted(set(fractions)):
        angle = math.radians(start + DOG_HANDEDNESS * span * fraction)
        ramp_height = DOG_RAMP_LOW_HEIGHT + fraction * (DOG_ORIGINAL_HEIGHT - DOG_RAMP_LOW_HEIGHT)
        top = PLATE_THICKNESS + min(ramp_height, DOG_FINISHED_HEIGHT)
        points = [rotated(r, 0, angle, z) for r, z in (
            (BORE_DIA / 2 - 0.02, bottom), (DOG_OD / 2, bottom),
            (DOG_OD / 2, top), (BORE_DIA / 2 - 0.02, top))]
        sections.append(Part.makePolygon(points + [points[0]]))
    return Part.makeLoft(sections, True, True)


def build_shapes():
    if not (TEETH >= 3 and PITCH > 0 and PLATE_THICKNESS > 0 and
            REAR_BOSS_OD > BORE_DIA > 0 and REAR_BOSS_HEIGHT > 0 and
            DOG_OD > BORE_DIA and DOG_COUNT == 4 and
            0 < DOG_BASE_HEIGHT < DOG_RAMP_LOW_HEIGHT < DOG_HEIGHT and
            DOG_PIN_DIA > 0 and DOG_PIN_CLEARANCE >= 0 and
            0 <= DOG_TOP_CUT and DOG_RAMP_LOW_HEIGHT < DOG_FINISHED_HEIGHT <= DOG_ORIGINAL_HEIGHT and
            0 < DOG_GAP_ANGLE < 360.0 / DOG_COUNT and
            DOG_HANDEDNESS in (-1, 1) and DOG_RAMP_SEGMENTS >= 4):
        raise ValueError('Invalid sprocket or dog dimensions.')
    plate = make_sprocket_plate()
    rear_boss = ring(REAR_BOSS_OD, BORE_DIA, REAR_BOSS_HEIGHT, -REAR_BOSS_HEIGHT)
    dog_base = ring(DOG_OD, BORE_DIA, DOG_BASE_HEIGHT, PLATE_THICKNESS)
    dogs = [make_dog(i) for i in range(DOG_COUNT)]
    result = plate.fuse(rear_boss).fuse(dog_base)
    for dog in dogs:
        result = result.fuse(dog)
    # Finish a truly cylindrical through-bore through the loft approximations.
    cutter = Part.makeCylinder(BORE_DIA / 2,
                              REAR_BOSS_HEIGHT + PLATE_THICKNESS + DOG_HEIGHT + 2,
                              V(0, 0, -REAR_BOSS_HEIGHT - 1))
    result = result.cut(cutter)
    # Preserve valid loft seams: refining these ruled ramps can invalidate
    # their trimmed faces on some OpenCascade versions.
    if not result.isValid() or len(result.Solids) != 1:
        raise RuntimeError('Clutch geometry is not a valid single solid.')
    return result, plate, rear_boss, dogs


def main():
    import FreeCADGui as Gui
    shape, _, _, _ = build_shapes()
    doc = App.newDocument('SprocketFourDogClutch')
    obj = doc.addObject('Part::Feature', 'SprocketFourDogClutch')
    obj.Label = '28T sprocket — four-dog overrunning face clutch'
    obj.Shape = shape
    for name, value in (
        ('ChainPitch', PITCH), ('BoreDiameter', BORE_DIA),
        ('PlateThickness', PLATE_THICKNESS), ('DogOutsideDiameter', DOG_OD),
        ('DogProjection', DOG_FINISHED_HEIGHT), ('DogBaseHeight', DOG_BASE_HEIGHT),
        ('DogTopCut', DOG_TOP_CUT), ('DogPinDiameter', DOG_PIN_DIA),
        ('DogPinClearance', DOG_PIN_CLEARANCE), ('RearBossDiameter', REAR_BOSS_OD),
        ('RearBossLength', REAR_BOSS_HEIGHT)):
        obj.addProperty('App::PropertyLength', name, 'Dimensions')
        setattr(obj, name, value)
        obj.setEditorMode(name, 1)
    obj.addProperty('App::PropertyInteger', 'ToothCount', 'Dimensions')
    obj.ToothCount = TEETH
    obj.setEditorMode('ToothCount', 1)
    obj.addProperty('App::PropertyString', 'GeometryNotes', 'Dimensions')
    obj.GeometryNotes = 'Edit macro parameters and rerun; tooth flanks and dog ramps are photo approximations.'
    obj.ViewObject.ShapeColor = (0.62, 0.64, 0.68)
    obj.ViewObject.LineColor = (0.16, 0.17, 0.19)
    obj.ViewObject.DisplayMode = 'Flat Lines'
    doc.recompute()
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    App.Console.PrintMessage('Created valid 28T four-dog clutch; total thickness 28.2 mm.\n')
    return doc


if __name__ == '__main__':
    main()
