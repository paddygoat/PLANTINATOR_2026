import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from gl_runtime import configure_environment, ContextCheck


class RuntimeTests(unittest.TestCase):
    def test_linux_selects_matching_glx_backends(self):
        env={'QT_QPA_PLATFORM':'wayland','QT_XCB_GL_INTEGRATION':'xcb_egl'}
        configure_environment(env, 'linux')
        self.assertEqual(env['QT_QPA_PLATFORM'],'xcb')
        self.assertEqual(env['QT_XCB_GL_INTEGRATION'],'xcb_glx')
        self.assertEqual(env['QT_OPENGL'],'desktop')
        self.assertEqual(env['COIN_EGL'],'0')
        self.assertNotIn('COIN_GL_NO_CURRENT_CONTEXT_CHECK',env)

    def test_headless_mode_and_software_option(self):
        env={'QT_QPA_PLATFORM':'offscreen'}
        configure_environment(env,'linux',True)
        self.assertEqual(env['QT_QPA_PLATFORM'],'offscreen')
        self.assertEqual(env['LIBGL_ALWAYS_SOFTWARE'],'1')

    def test_native_context_is_required(self):
        check=ContextCheck.__new__(ContextCheck)
        check.error=None
        check.glx=SimpleNamespace(glXGetCurrentContext=lambda:None)
        self.assertIn('GLX',check.problem(True))
        self.assertIn('Qt',check.problem(False))
        check.glx.glXGetCurrentContext=lambda:42
        self.assertIsNone(check.problem(True))

    def test_render_is_never_called_without_current_native_context(self):
        import qt_app
        context=SimpleNamespace(isValid=lambda:True)
        fake=SimpleNamespace(render_error=None,makeCurrent=Mock(),context=lambda:context,
            context_check=SimpleNamespace(problem=lambda valid:'No current GLX context'),
            render_failed=Mock(),manager=Mock(),rendered_frames=0)
        with patch.object(qt_app,'QtOpenGL',SimpleNamespace(QGLContext=SimpleNamespace(currentContext=lambda:context))):
            qt_app.Viewer.paintGL(fake)
        fake.manager.render.assert_not_called()
        fake.render_failed.emit.assert_called_once()
        self.assertEqual(fake.rendered_frames,0)


if __name__=='__main__':
    unittest.main()
