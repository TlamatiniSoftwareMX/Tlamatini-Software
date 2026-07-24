import unittest
from unittest import mock

from interfaz.dashboard import DashboardTLAMATINI


class _ImmediateRoot:
    def winfo_exists(self):
        return True

    def after(self, _delay, callback):
        callback()
        return "focus-refresh"


class DashboardWindowLifecycleTests(unittest.TestCase):
    def test_focus_return_refreshes_status_without_rebuilding_dashboard(self):
        dashboard = DashboardTLAMATINI.__new__(DashboardTLAMATINI)
        dashboard.root = _ImmediateRoot()
        dashboard._refresh_pending = False
        dashboard._focus_refresh_job = None
        dashboard._refrescar_estado_sin_reconstruir = mock.Mock()
        dashboard._reconstruir_dashboard = mock.Mock()

        dashboard._al_recuperar_foco()

        dashboard._refrescar_estado_sin_reconstruir.assert_called_once_with()
        dashboard._reconstruir_dashboard.assert_not_called()


if __name__ == "__main__":
    unittest.main()
