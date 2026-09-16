#!/usr/bin/env python3
"""Detailed Qt5 CAD simulator. Use --schematic for the older lightweight view."""
import argparse
from model import DEFAULT_SOURCE

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', default=DEFAULT_SOURCE)
    parser.add_argument('--schematic', action='store_true', help='Use the simplified Tkinter viewer')
    parser.add_argument('--software', action='store_true', help='Use Mesa software OpenGL for the detailed viewer')
    args = parser.parse_args()
    if args.schematic:
        from schematic_app import Simulator
        Simulator(args.source).mainloop()
    else:
        try:
            from gl_runtime import configure_environment
            configure_environment(software=args.software)
            from qt_app import launch
            raise SystemExit(launch(args.source))
        except ImportError as error:
            parser.exit(1, f'Detailed viewer dependency missing: {error}\nUse system Python with FreeCAD, PySide2 (Qt5), and Pivy installed, or run with --schematic.\n')

        except RuntimeError as error:
            parser.exit(1, f'Cannot start detailed viewer: {error}\n')
