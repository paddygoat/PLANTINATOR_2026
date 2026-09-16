# PLANTINATOR 2026

PLANTINATOR 2026 explores a practical way to develop machinery with complex moving geometry: describe the mechanism in Python, refine it with an LLM such as GPT Astra, and inspect its movement in a dedicated Qt5 simulation application. When the mechanism is ready for further engineering, construct the corresponding model in FreeCAD and add the surrounding structure. This combines repeatable geometry generation, rapid visual feedback, and conventional CAD detailing in one development workflow.

The repository contains a lugged wheel and chain mechanism, including paired wheels, a shared shaft, sprockets, and individual chain components. Its dimensions and motion relationships are expressed in code, making the assembly suitable for systematic changes rather than repeated manual reconstruction.

## Why describe moving geometry in Python?

Building an assembly manually in FreeCAD involves more than drawing its individual parts. Components must have consistent dimensions, occupy the correct positions, and maintain their intended relationships as the mechanism moves. Repeated features, such as wheel lugs and chain links, multiply the positioning work. A change to wheel spacing or sprocket geometry can affect several other parts of the design.

A Python macro captures these relationships explicitly. Dimensions become named parameters; repeated shapes come from functions and loops; placements follow mathematical rules. Instead of editing every affected component separately, the designer changes the relevant inputs and regenerates the assembly. FreeCAD also supports parametric modelling through its interface, but code makes large sets of repeated operations especially straightforward to reproduce and review.

In this project, parameters describe features such as disc diameter, lug count, chain pitch, and wheel spacing. The current sprocket tooth counts are 28, 15, and 21, despite older comments mentioning 13 teeth. Reading the executable parameters therefore matters more than relying on historical labels. The wheel and first sprocket share a defined rotational relationship, preserving their intended shaft synchronisation during animation.

## Working with an LLM

An LLM can help translate mechanical intentions into changes to the Python model. A request might be: “Increase the distance between the wheels while keeping the shaft ends flush with the outer bosses.” The useful result is a change to the relevant dimensions and relationships, which the designer can inspect, run, and revise.

This reduces the effort of writing repetitive modelling operations, tracing dependencies, and adjusting placement calculations. It also makes experimentation accessible through ordinary language. A designer can describe the desired arrangement, ask for an explanation of the geometry, and request a specific alteration without manually repeating every CAD operation.

The strongest workflow uses small, explicit requests. State the dimensions, coordinate directions, fixed relationships, and expected motion. Review the resulting code, then inspect the model. Keep successful revisions in version control so that alternatives can be compared or reversed. The LLM assists with implementation; the designer decides whether the mechanism meets its engineering requirements.

## Faster visual checks with Qt5

The dedicated application in [Simulator_app](Simulator_app/) shortens the feedback loop between changing a model and seeing it move. It uses PySide2 for Qt5, Pivy/Coin with OpenGL for display, and FreeCAD’s Part geometry kernel to construct the solids. It does not require the full FreeCAD desktop interface for each inspection.

That distinction is useful during frequent revisions. Opening FreeCAD, loading or rerunning a macro, waiting for document construction, and arranging the view introduces repeated interaction. The dedicated viewer concentrates on the mechanism and its controls, allowing human attention to stay on the geometry and motion. The practical speed advantage comes from this focused workflow and reuse of display geometry; no benchmark is claimed here.

The viewer displays tessellated CAD surfaces, including holes, chamfers, bosses, sprocket teeth, and chain details. During playback, it updates component transformations rather than rebuilding every solid for every frame. Controls include play/pause, signed speed, stepping by one chain pitch, and a position slider. Standard views, orbit, pan, zoom, lug inspection, and chain close-ups help examine details from useful angles.

Use **Load dimensions** to read supported numeric constants from a Python file and rebuild the view. This feature does not execute arbitrary selected macros: geometry comes from the bundled `source_model.py`. New geometry logic must therefore be incorporated into that source and the application restarted or rebuilt. Keep the CAD macro and simulator source consistent when developing changes.

Check the default source path before launching: the repository stores its CAD macro inside `CAD/`, while the simulator currently expects it at repository root.

## Continue the design in FreeCAD

The workflow retains a route into a native FreeCAD document. Open [FreeCAD_Simulator.FCMacro](Simulator_app/FreeCAD_Simulator.FCMacro) in FreeCAD and execute it, keeping its sibling files together. It runs the bundled geometry source and creates actual document objects. Save the resulting document as an `.FCStd` working file for subsequent editing.

This handoff is more precise than treating the standalone viewer as a general CAD exporter. The current application does not provide a universal working-file import/export pipeline. If dimensions were loaded from another file in the viewer, transfer those accepted values into the bundled source before generating the FreeCAD document. Verify that both environments show the same arrangement.

Once inside FreeCAD, add static items such as the supporting frame, bearing mounts, brackets, guards, or mounting plates. Use the mechanism’s shaft positions and movement envelope to guide their placement. Keep these additions organised separately and save a separate working document before rerunning generation code, which creates a fresh mechanism document. Generated solids do not automatically provide a complete sketch-based feature history.

## A practical development cycle

Start with the Python geometry, ask the LLM for a clearly bounded change, and inspect the revised mechanism in Qt5. Check several positions across a complete cycle, including close approaches and reversals. Once the arrangement is satisfactory, generate the FreeCAD document and develop the supporting structure around it.

The simulator uses a continuous pitch-circle approximation, rather than a rigid-link contact solver. It does not calculate loads, traction, tension, or collisions. Visual agreement supports geometric development, while fabrication still requires dimensional, clearance, and mechanical checks. Used together, Python, LLM assistance, Qt5 visualisation, and FreeCAD make complex mechanisms easier to iterate and understand.
