"""Select the GLX backend required by the installed Linux Coin renderer."""
import ctypes
import os
import sys


def configure_environment(environ=None, platform=None, software=False):
    env = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    if software:
        env['LIBGL_ALWAYS_SOFTWARE'] = '1'
    if platform.startswith('linux'):
        # Offscreen/minimal are deliberately retained for non-rendering tests.
        if env.get('QT_QPA_PLATFORM', '').split(':')[0] not in ('offscreen', 'minimal'):
            env['QT_QPA_PLATFORM'] = 'xcb'
            env['QT_XCB_GL_INTEGRATION'] = 'xcb_glx'
        env['QT_OPENGL'] = 'desktop'
        env['COIN_EGL'] = '0'


class ContextCheck:
    def __init__(self):
        self.glx = None
        self.error = None
        if sys.platform.startswith('linux'):
            try:
                self.glx = ctypes.CDLL('libGLX.so.0')
                self.glx.glXGetCurrentContext.restype = ctypes.c_void_p
                self.glx.glXGetCurrentContext.argtypes = []
            except OSError as error:
                self.error = str(error)

    def problem(self, qt_valid):
        if not qt_valid:
            return 'Qt could not make the viewer’s OpenGL context current.'
        if self.error:
            return 'GLX is unavailable: '+self.error
        if self.glx is not None and not self.glx.glXGetCurrentContext():
            return 'No current GLX context. This Coin build requires X11/GLX rather than Wayland/EGL.'
        return None


def check_display():
    """Report an unavailable X11 display before Qt's plugin can abort the process."""
    if not sys.platform.startswith('linux') or os.environ.get('QT_QPA_PLATFORM') != 'xcb':
        return
    try:
        x11 = ctypes.CDLL('libX11.so.6')
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        display = x11.XOpenDisplay(None)
    except OSError as error:
        raise RuntimeError('X11 support is unavailable: '+str(error)) from error
    if not display:
        raise RuntimeError('Cannot connect to the X11/XWayland display. Run this app from a terminal in your graphical desktop session.')
    x11.XCloseDisplay(display)
