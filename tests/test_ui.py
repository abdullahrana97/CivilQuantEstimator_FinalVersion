import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from core.calculations import default_inputs, make_record


class StreamlitTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()

    def click(self, app, label):
        next(b for b in app.button if b.label == label).click().run()
        self.assertEqual(len(app.exception), 0)

    def test_all_six_pages_render_without_key(self):
        app = self.app()
        self.assertEqual(len(app.exception), 0)
        for page in ["Quantity takeoff", "Knowledge base", "CiviGuide AI", "Agent review", "Project & exports", "Overview"]:
            self.click(app, page)

    def test_save_export_and_remove(self):
        app = self.app()
        self.click(app, "Quantity takeoff")
        self.click(app, "Calculate & save takeoff")
        self.assertEqual(len(app.session_state.records), 1)
        self.click(app, "Project & exports")
        self.click(app, "Prepare PDF report")
        self.assertTrue(app.session_state.pdf.startswith(b"%PDF"))
        self.click(app, "Remove selected item")
        self.assertEqual(app.session_state.records, [])

    def test_restored_project_applies_before_widgets(self):
        app = self.app()
        app.session_state.pending_import = dict(name="Restored", records=[make_record("Steel", default_inputs("Steel"))], rates={}, currency="USD")
        app.run()
        self.assertEqual(app.session_state.project_name, "Restored")
        self.assertEqual(len(app.session_state.records), 1)
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
