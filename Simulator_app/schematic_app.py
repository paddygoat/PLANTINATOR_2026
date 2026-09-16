#!/usr/bin/env python3
"""Run with system Python: python3 app.py [source macro.py]."""
import argparse
import math
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from model import DEFAULT_SOURCE, Model
from camera import Camera


class Simulator(tk.Tk):
    def __init__(self, source=DEFAULT_SOURCE):
        super().__init__()
        self.title('WEEDINATOR · 3D wheel & chain simulator · v2')
        self.geometry('1180x820')
        self.minsize(820, 600)
        self.model = Model(source)
        self.camera = Camera()
        self.drag_origin = None
        self.offset = 0.0
        self.running = False
        self.last = time.perf_counter()
        self.speed = tk.DoubleVar(value=100)
        self.show_wheel = tk.BooleanVar(value=True)
        self.chain_zoom = tk.BooleanVar(value=False)
        self.phase = tk.DoubleVar(value=0)
        bar = ttk.Frame(self, padding=12)
        bar.pack(fill='x')
        ttk.Label(bar, text='WHEEL / CHAIN', font=('Sans', 16, 'bold')).pack(side='left')
        ttk.Button(bar, text='Load dimensions…', command=self.load).pack(side='right')
        controls = ttk.Frame(self, padding=(12, 0, 12, 10))
        controls.pack(fill='x')
        self.play = ttk.Button(controls, text='▶ Play', command=self.toggle)
        self.play.pack(side='left')
        ttk.Button(controls, text='Step 1 pitch', command=self.step).pack(side='left', padx=6)
        ttk.Button(controls, text='Reset', command=self.reset).pack(side='left')
        ttk.Label(controls, text='  Chain speed (mm/s)').pack(side='left')
        ttk.Scale(controls, from_=-400, to=400, variable=self.speed, length=190).pack(side='left')
        ttk.Checkbutton(controls, text='Wheel', variable=self.show_wheel, command=self.draw).pack(side='left', padx=8)
        ttk.Checkbutton(controls, text='Chain close-up', variable=self.chain_zoom, command=self.draw).pack(side='left')
        camera_box = ttk.LabelFrame(self, text='3D CAMERA · orbit / roll / pan / zoom', padding=6)
        camera_box.pack(fill='x', padx=12, pady=(0, 8))
        presets = ttk.Frame(camera_box)
        presets.pack(fill='x')
        ttk.Label(presets, text='View:').pack(side='left')
        for name in ('Front', 'Back', 'Top', 'Right', 'Isometric'):
            ttk.Button(presets, text=name, command=lambda name=name: self.set_view(name)).pack(side='left', padx=2)
        ttk.Button(presets, text='Restore startup view', command=self.restore_camera).pack(side='left', padx=8)
        orbit = ttk.Frame(camera_box)
        orbit.pack(fill='x', pady=4)
        for label, axis, amount in (
            ('Orbit ←', 'yaw', -10), ('Orbit →', 'yaw', 10),
            ('Orbit ↑', 'pitch', -10), ('Orbit ↓', 'pitch', 10),
            ('Roll ↶', 'roll', -10), ('Roll ↷', 'roll', 10),
        ):
            ttk.Button(orbit, text=label, command=lambda axis=axis, amount=amount: self.rotate_camera(axis, amount)).pack(side='left', padx=2)
        framing = ttk.Frame(camera_box)
        framing.pack(fill='x')
        for label, dx, dy in (('Pan ←', -30, 0), ('Pan →', 30, 0), ('Pan ↑', 0, -30), ('Pan ↓', 0, 30)):
            ttk.Button(framing, text=label, command=lambda dx=dx, dy=dy: self.pan_camera(dx, dy)).pack(side='left', padx=2)
        ttk.Button(framing, text='Zoom +', command=lambda: self.zoom_camera(1.2)).pack(side='left', padx=2)
        ttk.Button(framing, text='Zoom −', command=lambda: self.zoom_camera(1/1.2)).pack(side='left', padx=2)
        ttk.Label(camera_box, text='Drag to orbit · Shift-drag to pan · Mouse wheel to zoom').pack(anchor='w', pady=(4, 0))
        self.canvas = tk.Canvas(self, background='#101b25', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=12)
        self.canvas.bind('<Configure>', lambda _: self.draw())
        self.canvas.bind('<ButtonPress-1>', lambda event: setattr(self, 'drag_origin', (event.x, event.y)))
        self.canvas.bind('<B1-Motion>', self.drag_camera)
        self.canvas.bind('<ButtonRelease-1>', lambda _: setattr(self, 'drag_origin', None))
        self.canvas.bind('<MouseWheel>', lambda event: self.zoom_camera(1.1 if event.delta > 0 else 1/1.1))
        self.canvas.bind('<Button-4>', lambda _: self.zoom_camera(1.1))
        self.canvas.bind('<Button-5>', lambda _: self.zoom_camera(1/1.1))
        self.info = ttk.Label(self, padding=(12, 8), font=('Sans', 11))
        self.info.pack(fill='x')
        scrub = ttk.Frame(self, padding=(12, 0, 12, 6))
        scrub.pack(fill='x')
        ttk.Label(scrub, text='Chain loop position').pack(side='left')
        ttk.Scale(scrub, from_=0, to=100, variable=self.phase, command=self.scrub).pack(side='left', fill='x', expand=True, padx=10)
        ttk.Label(self, text='3D schematic · simplified solids · continuous pitch-circle approximation; no loads, slip or collision physics', padding=(12, 2, 12, 12)).pack(fill='x')
        self.bind('<space>', lambda _: self.toggle())
        self.after(30, self.tick)

    def set_view(self, name):
        self.camera.preset(name)
        self.draw()

    def restore_camera(self):
        self.camera.reset()
        self.chain_zoom.set(False)
        self.draw()

    def rotate_camera(self, axis, amount):
        setattr(self.camera, axis, (getattr(self.camera, axis)+amount) % 360)
        self.draw()

    def pan_camera(self, dx, dy):
        self.camera.pan_x += dx
        self.camera.pan_y += dy
        self.draw()

    def zoom_camera(self, factor):
        self.camera.magnify(factor)
        self.draw()

    def drag_camera(self, event):
        if self.drag_origin is not None:
            dx, dy = event.x-self.drag_origin[0], event.y-self.drag_origin[1]
            if event.state & 0x0001:
                self.pan_camera(dx, dy)
            else:
                self.camera.yaw += dx*0.4
                self.camera.pitch += dy*0.4
                self.draw()
        self.drag_origin = (event.x, event.y)

    def load(self):
        path = filedialog.askopenfilename(filetypes=[('Python macro', '*.py')])
        if not path:
            return
        try:
            model = Model(path)
        except Exception as error:
            messagebox.showerror('Cannot load dimensions', str(error))
            return
        self.model = model
        self.reset()

    def toggle(self):
        self.running = not self.running
        self.last = time.perf_counter()
        self.play.configure(text='Ⅱ Pause' if self.running else '▶ Play')

    def reset(self):
        self.running = False
        self.play.configure(text='▶ Play')
        self.offset = 0
        self.phase.set(0)
        self.draw()

    def step(self):
        self.running = False
        self.play.configure(text='▶ Play')
        self.offset += self.model.pitch
        self.phase.set(self.offset % self.model.length / self.model.length * 100)
        self.draw()

    def scrub(self, value):
        self.running = False
        self.play.configure(text='▶ Play')
        self.offset = float(value) / 100 * self.model.length
        self.draw()

    def tick(self):
        now = time.perf_counter()
        if self.running:
            self.offset += self.speed.get() * min(now-self.last, 0.15)
            self.phase.set(self.offset % self.model.length / self.model.length * 100)
            self.draw()
        self.last = now
        self.after(30, self.tick)

    def draw(self):
        c, m = self.canvas, self.model
        c.delete('all')
        width, height = max(c.winfo_width(), 100), max(c.winfo_height(), 100)
        if self.chain_zoom.get():
            xmin, xmax = -m.radii[0]-25, m.x+m.radii[1]+25
            ymin, ymax = -m.dim['THIRD_SPROCKET_SPACING']-m.radii[2]-25, m.radii[0]+25
        else:
            extent = max(m.dim['FRONT_DISC_OD']/2-m.dim['LUG_WELD_OVERLAP']+m.dim['LUG_LENGTH'], m.dim['FRONT_DISC_OD']/2) + 30
            xmin, xmax = -extent, max(extent, m.x+m.radii[1]+25)
            ymin, ymax = min(-extent, -m.dim['THIRD_SPROCKET_SPACING']-m.radii[2]-25), extent
        scale = max(0.01, min((width-60)/(xmax-xmin), (height-60)/(ymax-ymin))) * self.camera.zoom
        plane_z = 0
        scene = []
        def project(x, y, z=None):
            return self.camera.project(x-(xmin+xmax)/2, y-(ymin+ymax)/2, plane_z if z is None else z)
        def xy(x, y, z=None):
            px, py, _ = project(x, y, z)
            return (width/2+px*scale+self.camera.pan_x, height/2-py*scale+self.camera.pan_y)
        def primitive(kind, points, **kw):
            depth = sum(project(*point)[2] for point in points)/len(points)
            coords = [value for point in points for value in xy(*point)]
            scene.append((depth, kind, coords, kw))
        def circle(x, y, r, **kw):
            kw.setdefault('fill', '')
            primitive('polygon', [(x+r*math.cos(i*math.tau/64), y+r*math.sin(i*math.tau/64)) for i in range(64)], **kw)
        def line(a, b, **kw):
            primitive('line', [a, b], **kw)
        angles = m.angles(self.offset)
        if self.show_wheel.get():
            wheel_z = m.dim['WHEEL_Z_OFFSET']
            plane_z = wheel_z-m.dim['RIM_WIDTH']
            circle(0, 0, m.dim['RIM_OD']/2, outline='#315a50', width=2)
            for i in range(24):
                a = i*math.tau/24
                x, y = m.dim['RIM_OD']/2*math.cos(a), m.dim['RIM_OD']/2*math.sin(a)
                line((x, y, plane_z), (x, y, wheel_z), fill='#315a50')
            plane_z = wheel_z
            circle(0, 0, m.dim['FRONT_DISC_OD']/2, fill='#193a36', outline='#4c907c', width=2)
            for level, key in enumerate(('OUTER_STEP_RADIUS', 'INNER_STEP_RADIUS')):
                plane_z = wheel_z + m.dim['FRONT_DISC_THK'] - level*m.dim['STEP_HEIGHT']
                circle(0, 0, m.dim[key], outline='#315a50', width=2)
                plane_z -= m.dim['STEP_HEIGHT']
                circle(0, 0, m.dim[key]-m.dim['STEP_HEIGHT'], outline='#315a50', width=2)
            plane_z = wheel_z
            for i in range(int(m.dim['LUG_COUNT'])):
                a = angles[0] + math.radians(m.dim['WHEEL_PHASE_OFFSET']+m.dim['LUG_START_ANGLE']+m.dim['LUG_SKEW_ANGLE']) + i*math.tau/m.dim['LUG_COUNT']
                start = m.dim['FRONT_DISC_OD']/2-m.dim['LUG_WELD_OVERLAP']
                end = start+m.dim['LUG_LENGTH']
                z0 = wheel_z+m.dim['FRONT_DISC_THK']
                z1 = z0+m.dim['LUG_WIDTH']
                primitive('polygon', [(start*math.cos(a), start*math.sin(a), z0),
                                      (end*math.cos(a), end*math.sin(a), z0),
                                      (end*math.cos(a), end*math.sin(a), z1),
                                      (start*math.cos(a), start*math.sin(a), z1)],
                          fill='#885138', outline='#d98e57', width=2)
            a = angles[0]+math.radians(m.dim['WHEEL_PHASE_OFFSET'])
            line((0, 0), (m.dim['FRONT_DISC_OD']/2*math.cos(a), m.dim['FRONT_DISC_OD']/2*math.sin(a)), fill='#65d6b4', width=2, dash=(6, 4))
        plane_z = 0
        for i, ((x, y), r, teeth, angle) in enumerate(zip(m.centres, m.radii, m.teeth, angles)):
            points = []
            for j in range(int(teeth)*4):
                a = angle+j*math.tau/(teeth*4)
                radius = r + (2.3 if j%4 in (1, 2) else -m.dim['ROLLER_DIAMETER']/2)
                points.append((x+radius*math.cos(a), y+radius*math.sin(a)))
            primitive('polygon', points, fill='#465360', outline='#abb9c6', width=1)
            circle(x, y, m.dim['SPROCKET_BORE_DIAMETER']/2, fill='#101b25', outline='#c3ced6')
            line((x, y), (x+(r-8)*math.cos(angle), y+(r-8)*math.sin(angle)), fill='#ffcf70', width=3)
            primitive('text', [(x, y-r-14)], text=f'{int(teeth)}T', fill='#eef3f7', font=('Sans', 11, 'bold'))
        points = [m.position(i*m.pitch+self.offset) for i in range(m.count)]
        for i, a in enumerate(points):
            line(a, points[(i+1)%m.count], fill='#d3dde5' if i%2 == 0 else '#8697a8', width=max(2, 3*scale))
        for i, (x, y) in enumerate(points):
            circle(x, y, m.dim['ROLLER_DIAMETER']/2, fill='#ffc567' if i == 0 else '#bcc9d4', outline='#263645')
        for _, kind, coords, options in sorted(scene, key=lambda item: item[0]):
            getattr(c, 'create_'+kind)(*coords, **options)
        c.create_text(18, 18, anchor='nw', fill='#93aaba', text=f'3D SCHEMATIC · orbit {self.camera.yaw % 360:.0f}° / {self.camera.pitch % 360:.0f}° · roll {self.camera.roll % 360:.0f}° · zoom {self.camera.zoom:.1f}×')
        rpm = self.speed.get()/m.radii[0]*60/math.tau
        self.info.configure(text=f'{m.count} links × {m.pitch:g} mm  |  Loop {m.length:.2f} mm  |  Driven centre X {m.x:.2f} mm\nSpeed {self.speed.get():.1f} mm/s  |  Wheel / first sprocket {rpm:.2f} rpm (clockwise positive)  |  Wheel angle {math.degrees(angles[0])+m.dim["WHEEL_PHASE_OFFSET"]:.1f}°')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', default=DEFAULT_SOURCE, help='Macro from which to read numeric dimensions')
    args = parser.parse_args()
    Simulator(args.source).mainloop()
