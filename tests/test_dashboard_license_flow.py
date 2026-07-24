import unittest
from unittest import mock

from interfaz import dashboard


class DashboardLicenseFlowTests(unittest.TestCase):
    def test_current_version_label_uses_runtime_version(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        app.update_checker = mock.Mock()
        app.update_checker.local_state.return_value = {"current_version": "5.2.4"}
        self.assertEqual(app._current_version_label(), "Versión 5.2.4")

    def test_dashboard_license_request_uses_manual_format(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        app._safe_dict = lambda value: value if isinstance(value, dict) else {}
        app._user_profile = lambda: {
            "full_name": "Cliente Demo",
            "email": "cliente@example.com",
            "phone": "+52 555 123 4567",
            "country": "México",
        }
        app._license_dashboard_state_label = lambda _status: "Sin licencia"

        with mock.patch.object(
            dashboard,
            "get_installation_payload",
            return_value={
                "installation_id": "12345678-1234-1234-1234-1234567890ab",
                "os_name": "Linux",
                "app_version": "5.2",
            },
        ):
            request_text = app._license_request_text({"license_status": {"plan": "mensual"}})

        self.assertIn("Nombre: Cliente Demo", request_text)
        self.assertIn("Email: cliente@example.com", request_text)
        self.assertIn("Plan solicitado: mensual", request_text)

    def test_license_panel_mode_without_profile_shows_form(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        self.assertEqual(app._license_panel_mode({}, False), "license_active")

    def test_license_panel_mode_with_profile_and_without_license_shows_two_paths(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        self.assertEqual(app._license_panel_mode({"state": "missing", "plan": ""}, True), "license_active")

    def test_license_panel_mode_trial_active(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        self.assertEqual(app._license_panel_mode({"state": "valid", "plan": "trial"}, True), "license_active")

    def test_license_panel_mode_license_active(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        self.assertEqual(app._license_panel_mode({"state": "valid", "plan": "mensual"}, True), "license_active")

    def test_open_license_forwards_initial_view(self):
        fake_root = object()
        fake_parent = object()
        fake_window = object()
        with mock.patch.object(dashboard, "VentanaLicencia", return_value=fake_window) as window_ctor, mock.patch.object(
            dashboard, "_mostrar_encima"
        ) as show:
            dashboard.abrir_licencia(fake_root, fake_parent, initial_view="manual")

        window_ctor.assert_called_once_with(fake_root, initial_view="manual")
        show.assert_called_once_with(fake_window, fake_parent)

    def test_access_gate_state_without_profile(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        app._safe_dict = lambda value: value if isinstance(value, dict) else {}
        app._user_profile = lambda: {"full_name": "", "email": ""}
        self.assertEqual(app._access_gate_state({"license_status": {}}), "license_active")

    def test_access_gate_state_without_access_shows_choose_path(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        app._safe_dict = lambda value: value if isinstance(value, dict) else {}
        app._user_profile = lambda: {"full_name": "Cliente Demo", "email": "cliente@example.com"}
        self.assertEqual(app._access_gate_state({"license_status": {"state": "missing"}}), "license_active")

    def test_access_gate_state_trial_expired(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        app._safe_dict = lambda value: value if isinstance(value, dict) else {}
        app._user_profile = lambda: {"full_name": "Cliente Demo", "email": "cliente@example.com"}
        self.assertEqual(app._access_gate_state({"license_status": {"state": "missing", "trial_expired": True}}), "license_active")

    def test_can_access_with_trial_or_license(self):
        app = dashboard.DashboardTLAMATINI.__new__(dashboard.DashboardTLAMATINI)
        app._safe_dict = lambda value: value if isinstance(value, dict) else {}
        self.assertTrue(app._can_access_with_status({"license_status": {"state": "valid", "plan": "trial"}}))
        self.assertTrue(app._can_access_with_status({"license_status": {"state": "valid", "plan": "mensual"}}))
        self.assertTrue(app._can_access_with_status({"license_status": {"state": "missing"}}))


if __name__ == "__main__":
    unittest.main()
