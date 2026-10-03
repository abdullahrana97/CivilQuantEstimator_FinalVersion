import io
import json
import math
import unittest
from pypdf import PdfReader
from core.calculations import calculate, default_inputs, make_record, material_totals, procurement_quantity
from core.project import export_project, import_project, boq_rows
from core.reports import make_pdf


class QuantityTests(unittest.TestCase):
    def test_brickwork_independent_geometry(self):
        p = default_inputs("Brickwork")
        p.update(opening_area=2.1, quantity=2)
        r = calculate("Brickwork", p)
        volume = (10 * 3 * 2 - 2.1) * .23
        bricks = volume / (.24 * .12 * .085)
        mortar = volume - bricks * .23 * .11 * .075
        self.assertAlmostEqual(r["metrics"]["Masonry volume (m³)"], volume)
        self.assertEqual(r["materials"]["Bricks (each)"], math.ceil(bricks * 1.05))
        self.assertAlmostEqual(r["materials"]["Sand (m³)"], mortar * 1.33 * 1.05 * 4 / 5)

    def test_plaster_known_case(self):
        p = default_inputs("Plaster")
        p.update(length=10., height=3., quantity=2, opening_area=10., thickness_mm=10., wastage=0., dry_factor=1.33)
        r = calculate("Plaster", p)
        self.assertAlmostEqual(r["metrics"]["Net area (m²)"], 50)
        self.assertAlmostEqual(r["materials"]["Cement (50 kg bags)"], .5 * 1.33 / 5 * 1440 / 50)

    def test_concrete_ratio_conserves_dry_volume(self):
        p = default_inputs("Concrete")
        r = calculate("Concrete", p)
        cement_m3 = r["materials"]["Cement (50 kg bags)"] * 50 / 1440
        total = cement_m3 + r["materials"]["Sand (m³)"] + r["materials"]["Aggregate (m³)"]
        self.assertAlmostEqual(total, 5 * 3 * .15 * 1.54 * 1.05)

    def test_steel_physical_mass(self):
        p = default_inputs("Steel")
        p["wastage"] = 0.
        self.assertAlmostEqual(calculate("Steel", p)["materials"]["Steel (kg)"], math.pi * .006**2 * 7850 * 60)

    def test_invalid_inputs_are_rejected(self):
        for key, value in [("length", -1.), ("length", float("nan")), ("length", float("inf")),
                           ("quantity", 1.2), ("quantity", True), ("opening_area", 31.)]:
            p = default_inputs("Plaster")
            p[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                calculate("Plaster", p)

    def test_all_openings_give_zero_materials(self):
        p = default_inputs("Brickwork")
        p["opening_area"] = 30.
        self.assertTrue(all(q == 0 for q in calculate("Brickwork", p)["materials"].values()))

    def test_import_recalculates_tampered_results(self):
        r = make_record("Concrete", default_inputs("Concrete"))
        expected = r["result"]["materials"].copy()
        r["result"]["materials"]["Sand (m³)"] = 99999999
        restored = import_project(export_project("Test", [r], {}, "PKR"))
        self.assertEqual(restored["records"][0]["result"]["materials"], expected)

    def test_import_rejects_malformed_shapes_and_nan(self):
        for obj in [[], {}, dict(schema_version=2, records="bad"), dict(schema_version=2, records=[{}])]:
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                import_project(json.dumps(obj).encode())
        r = make_record("Steel", default_inputs("Steel"))
        bad = dict(schema_version=2, records=[r], rates={"Steel (kg)": float("nan")})
        with self.assertRaises(ValueError):
            import_project(json.dumps(bad).encode())

    def test_bag_rounding_happens_after_aggregation(self):
        p = default_inputs("Plaster")
        p.update(length=1., height=1., thickness_mm=1.)
        records = [make_record("Plaster", p), make_record("Plaster", p)]
        cement = material_totals(records)["Cement (50 kg bags)"]
        self.assertEqual(procurement_quantity("Cement (50 kg bags)", cement), 1)

    def test_unpriced_cost_not_fabricated(self):
        r = make_record("Steel", default_inputs("Steel"))
        self.assertIsNone(boq_rows([r], {})[0]["Material amount"])

    def test_pdf_contains_all_takeoffs_and_wraps_long_names(self):
        records = [make_record(m, default_inputs(m), "Very long <project> label & details " * 3)
                   for m in ("Brickwork", "Plaster", "Concrete", "Steel")]
        data = make_pdf("Demo & verification", records, {}, "PKR")
        pdf = PdfReader(io.BytesIO(data))
        text = "\n".join(p.extract_text() for p in pdf.pages)
        for m in ("Brickwork", "Plaster", "Concrete", "Steel"):
            self.assertIn(m, text)
        self.assertIn("Unpriced", text)
        self.assertGreaterEqual(len(pdf.pages), 2)


if __name__ == "__main__":
    unittest.main()
