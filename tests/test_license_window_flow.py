import unittest

from interfaz.ventana_licencia import VentanaLicencia


class LicenseWindowFlowTests(unittest.TestCase):
    def _window_stub(self):
        window = VentanaLicencia.__new__(VentanaLicencia)
        window._force_profile_view = False
        window._screen_override = ""
        return window

    def test_profile_form_state_without_profile(self):
        window = self._window_stub()
        state = window._resolve_screen_state({"profile_ready": False, "has_valid_license": False, "plan": ""})
        self.assertEqual(state, "profile_form")

    def test_choose_path_state_with_profile_and_without_license(self):
        window = self._window_stub()
        state = window._resolve_screen_state({"profile_ready": True, "has_valid_license": False, "plan": ""})
        self.assertEqual(state, "choose_path")

    def test_request_license_override_wins(self):
        window = self._window_stub()
        window._screen_override = "request_license"
        state = window._resolve_screen_state({"profile_ready": True, "has_valid_license": False, "plan": ""})
        self.assertEqual(state, "request_license")

    def test_paste_code_override_wins(self):
        window = self._window_stub()
        window._screen_override = "paste_code"
        state = window._resolve_screen_state({"profile_ready": True, "has_valid_license": False, "plan": ""})
        self.assertEqual(state, "paste_code")

    def test_trial_active_state(self):
        window = self._window_stub()
        state = window._resolve_screen_state({"profile_ready": True, "has_valid_license": True, "plan": "trial"})
        self.assertEqual(state, "trial_active")

    def test_license_active_state(self):
        window = self._window_stub()
        state = window._resolve_screen_state({"profile_ready": True, "has_valid_license": True, "plan": "mensual"})
        self.assertEqual(state, "license_active")

    def test_trial_expired_without_license_returns_trial_expired(self):
        window = self._window_stub()
        state = window._resolve_screen_state({"profile_ready": True, "has_valid_license": False, "plan": "", "local_status": {"trial_expired": True}})
        self.assertEqual(state, "trial_expired")


if __name__ == "__main__":
    unittest.main()
