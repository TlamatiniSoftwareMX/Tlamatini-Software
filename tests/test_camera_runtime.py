import unittest
from unittest import mock

from core import inventario_foto


class _FakeCapture:
    def __init__(self, opened):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def release(self):
        self.released = True


class CameraRuntimeTests(unittest.TestCase):
    def test_linux_prefers_v4l2_and_never_dshow(self):
        fake_cv = mock.Mock(CAP_V4L2=200, CAP_DSHOW=700)
        with mock.patch.object(inventario_foto, "cv2", fake_cv), mock.patch.object(inventario_foto.sys, "platform", "linux"):
            self.assertEqual(inventario_foto._backends_camara(), [200, None])

    def test_windows_prefers_dshow(self):
        fake_cv = mock.Mock(CAP_DSHOW=700)
        with mock.patch.object(inventario_foto, "cv2", fake_cv), mock.patch.object(inventario_foto.sys, "platform", "win32"):
            self.assertEqual(inventario_foto._backends_camara(), [700, None])

    def test_camera_falls_back_and_releases_failed_capture(self):
        first = _FakeCapture(False)
        second = _FakeCapture(True)
        fake_cv = mock.Mock(CAP_V4L2=200)
        fake_cv.VideoCapture.side_effect = [first, second]
        with mock.patch.object(inventario_foto, "cv2", fake_cv), mock.patch.object(inventario_foto.sys, "platform", "linux"):
            result = inventario_foto.abrir_camara(2)

        self.assertIs(result, second)
        self.assertTrue(first.released)
        self.assertEqual(fake_cv.VideoCapture.call_args_list, [mock.call(2, 200), mock.call(2)])


if __name__ == "__main__":
    unittest.main()
