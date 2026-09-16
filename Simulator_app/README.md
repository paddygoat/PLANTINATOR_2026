# WEEDINATOR detailed wheel and chain simulator — v3.2

## Start the updated app

Close the older running app, then run:

```bash
python3 app.py
```

The window title reads **WEEDINATOR · detailed CAD viewer · Qt5 · v3.2**. This is now the default application. It uses installed **PySide2 (Qt5)**, **Pivy/Coin with OpenGL**, and **FreeCAD's Part geometry kernel**. These dependencies are present on the machine where the app was built. Use the system Python compatible with FreeCAD; installing a generic package named FreeCAD with pip is not a substitute. On a system with a different FreeCAD library location, set `FREECAD_LIB` to the directory containing `FreeCAD.so`. A desktop display and working OpenGL context are required.

## Front disc rendering update (v3.2)

CAD checks confirm that the disc is 590 mm in diameter, has a 6 mm axial thickness, two rearward chamfered steps and an intact 30 mm bore. The renderer now meshes each CAD face separately and supplies explicit analytic surface normals, keeping flat plate faces separate from rounded edges and bore walls. It also explicitly requests a 24-bit depth buffer, enables depth testing and writing, and tightens the camera clipping range around the assembly to improve separation of thin surfaces. These changes address rendering artifacts without changing dimensions.

Regression tests verify flat front/back normals, mesh bounds and volume, as well as the original lug details. The reported visual distortion cannot be directly confirmed in the build session because a desktop display is unavailable.

## OpenGL startup fix (v3.1)

The Linux launcher now selects Qt's X11/GLX desktop OpenGL backend to match the installed Coin library. QApplication is created before Coin initialisation. The viewer requests a compatibility context without requiring multisampling, makes its context current before drawing, and checks both Qt and native GLX before entering Coin's renderer. If context creation fails, the app pauses and shows an error instead of calling Coin without a context. It does not disable Coin's context assertion.

An X11/XWayland display is required. The launcher checks display connectivity before constructing QApplication. Settings are scoped to the app process; system graphics configuration is unchanged.

For a driver issue, try Mesa software rendering:

```bash
python3 app.py --software
```

This retains the detailed CAD solids and uses Mesa software OpenGL instead of hardware acceleration. It still requires a working graphical display.

## Why details were missing

The older Tkinter viewer manually drew simplified polygons. Its lug blades were plain rectangles; it never generated the hole cuts, chamfers or welded flange solids. Qt5 by itself cannot restore omitted geometry.

The new viewer builds the original bundled CAD geometry and tessellates its actual surfaces at a 0.15 mm tolerance for OpenGL display. This includes the **10 mm lug chamfers, 12 mm through-holes, 6 mm flanges, stepped wheel face, rim, boss, sprocket tooth cuts and chain plates/pins/rollers**. OpenGL depth testing handles visibility. The screen shows tessellated solids rather than the older schematic.

The lug holes run along the tangential direction through the blades, so the startup front view sees them edge-on. Click **Lug detail** to pause and focus on the first blade from a slightly oblique side angle. Chamfers and the through-hole can then be inspected. A hole can still be hidden by other geometry when viewing from a different direction.

The disc has two rearward 12 mm steps. Their 45-degree chamfers start at radii 200 mm and 105 mm, ending at 188 mm and 93 mm respectively. The central land is 24 mm behind the outer land, with the hub seated on it. The rear profile follows the stepped front at a 6 mm axial offset.

## Controls

The right-side **Simulation & 3D camera** panel includes:

- Play/Pause, step one pitch, reset motion, signed chain speed, and chain-position slider.
- Front, Back, Top, Right and Isometric views.
- Orbit horizontally/vertically, roll, pan and zoom.
- **Restore startup view**: restores the front orientation and full-assembly framing.
- **Lug detail**: pauses, shows the wheel and focuses on a blade.
- **Chain close-up**: frames the sprockets and chain.
- Wheel visibility and loading another file's numeric dimensions.

Drag to orbit. Shift-drag or right-drag to pan. Scroll to zoom. Camera changes do not alter mechanism dimensions or shaft synchronisation. Startup remains the previous front view; animation starts paused.

Startup defaults to `../lugged_wheel_with_sprockets_chain.py`, and the file picker starts at that file. The bundled lug geometry includes three 10 mm chamfers, including the inner corner furthest from the disc.

**Load dimensions** reads direct numeric constants from a macro with the same parameter names; missing values use bundled defaults. It does not execute the selected file. Only the trusted bundled `source_model.py` supplies executable geometry code. This is a simulator for this assembly family, not a general macro interpreter.

## Other entry points

The older lightweight Tkinter schematic remains available explicitly:

```bash
python3 app.py --schematic
```

It is simplified and does not display the new CAD details.

For a native FreeCAD document, open **FreeCAD_Simulator.FCMacro** inside FreeCAD and execute it. Keep all sibling files together. This version has its own Qt dock and retains the original axonometric startup view. It requires `FreeCADGui` and creates actual document objects; the standalone Qt5 app uses the geometry kernel without the FreeCAD desktop UI.

## Source fidelity and limits

The source has `T1 = 28` despite older comments saying 13T. The app uses **28T / 15T / 21T**, with 58 pitches at 12.7 mm: a 736.6 mm loop. The solved second centre is approximately (136.120482, 0) mm and the third is (0, −140) mm.

The wheel rotates 1:1 with the first sprocket, plus `WHEEL_PHASE_OFFSET`, at Z = −50 mm. Geometry is retained from the bundled source; the original user file is untouched.

Motion retains the original continuous pitch-circle approximation. Angular speed is chain speed divided by pitch radius, which differs slightly from ideal integer tooth ratios. Equal arc-distance roller spacing produces chords shorter than the fixed chain pitch on arcs, so slight link/roller alignment discrepancies can remain. This is not a rigid-link/contact solver and does not calculate loads, traction, tension or collisions.

## Verification

```bash
python3 -m unittest discover -s . -v
```

Fifteen tests cover OpenGL backend selection and the no-context render guard, as well as the original path/rotation behaviour, dimension input, schematic camera math, CAD lug validity, actual hole/chamfer cutouts, tessellated detail vertices and shaft synchronisation. CAD tests require FreeCAD's Python libraries.

The Qt5 window, CAD scene construction, playback operations and camera controls have also passed a headless smoke test with `QT_QPA_PLATFORM=offscreen`. A missing-context smoke test also confirms that rendering is skipped and an error is shown without a Coin abort. These checks do **not** validate the final OpenGL image: a working desktop display was unavailable in the build session.

## Plain boss and shaft

The plain front boss is OD 50 / ID 30 x 30 mm, seated on the recessed centre. A local-X diameter-12 hole passes through its midpoint with a simplified M12 x 70 hex bolt and nut (threads omitted). The OD 30 x 954 mm shared shaft extends rearward with its front (+Z) end flush with the boss front face and remains solid and undrilled. The bolt intentionally intersects the shaft pending a later shaft-hole change.

## Rear rim closure

The Ø550 mm rim extends 74 mm rearward from the main Ø590 mm disc. A Ø550 x 6 mm closing disc meets its far end and extends another 6 mm rearward (local Z −80 to −74 mm; total rearward depth 80 mm). Its Ø30 mm centre bore accommodates the shaft.

A second plain boss (OD 40 / ID 30 x 7 mm) is seated on the outside of the rear closing disc, extending rearward from local Z −80 to −87 mm.

## Second wheel

A complete second wheel, including both discs, rim, 12 lugs, both bosses and locking fasteners, is rotated 180 degrees about Y. The centres of the 80 mm rim + rear-disc envelopes are 850 mm apart along negative Z. Its reference plane is 930 mm behind the first. Both wheels rotate together with one solid OD 30 x 954 mm shaft, flush with the two outward-facing front boss faces. Shaft holes remain uncut.
