from io import BytesIO
from unittest import TestCase
from unittest.mock import patch
import os

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from database.db import repository
from main import app


class ApiTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {"HPS_DATABASE_URL": ""})
        cls.env.start()
        repository.cache_clear()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        repository.cache_clear()
        cls.client.close()
        cls.env.stop()

    def test_demo_search_and_statistics(self):
        w = self.client.get("/api/workspace").json()
        self.assertEqual(len(w["prices"]), 67)
        self.assertFalse(w["persistent"])
        self.assertTrue(all(r["is_demo"] for r in w["prices"]))
        search = self.client.post("/api/search", json={
            "item_name": "Laptop", "names": sorted({p["item_name"] for p in w["prices"]}),
        })
        self.assertEqual(search.json(), ["Laptop Bisnis 14 inci"])
        result = self.client.post("/api/statistics", json={"values": [10, 11, 11, 12, 100]}).json()
        self.assertEqual(result["stats"]["median"], 11)
        self.assertIn("Di atas", result["flags"][-1])

    def test_xlsx_preview_then_commit(self):
        initial = self.client.get("/api/templates/reference")
        wb = load_workbook(BytesIO(initial.content))
        ws = wb.active
        values = {"item_name": "Kabel Demo", "specification": "4 mm", "unit": "meter",
                  "price": 25000, "observation_date": "2026-01-05", "quantity": 5}
        ws.append([values.get(cell.value) for cell in ws[1]])
        file = BytesIO()
        wb.save(file)
        meta = {"source_type": "GOVERNMENT", "source_name": "Rujukan demo", "effective_year": 2026,
                "effective_date": "2026-01-01", "version": "v1"}
        import json
        preview = self.client.post("/api/import/reference/preview",
                                   files={"file": ("Referensi.xlsx", file.getvalue())},
                                   data={"meta": json.dumps(meta)})
        self.assertEqual(preview.status_code, 200, preview.text)
        data = preview.json()
        self.assertEqual(len(data["rows"]), 1)
        added = self.client.post("/api/import/reference", json={"rows": data["rows"], "meta": meta})
        self.assertEqual(added.status_code, 200, added.text)
        row = added.json()["rows"][0]
        self.assertTrue(row["is_demo"])
        self.assertEqual(row["effective_year"], 2026)

    def test_analysis_save_and_report(self):
        w = self.client.get("/api/workspace").json()
        original = w["analyses"][0]
        request = {
            "context": original["context"], "indices": w["indices"],
            "observations": [r for r in w["prices"] if r["item_name"] == original["context"]["item_name"]],
            "choices": {
                r["price_observation_id"]: {"decision": r["decision"], "justification": r["justification"]}
                for r in original["evidence"]
            },
            "save": True,
        }
        res = self.client.post("/api/analyze", json=request)
        self.assertEqual(res.status_code, 200, res.text)
        snapshot = res.json()
        self.assertGreaterEqual(snapshot["result"]["stats"]["n"], 30)
        self.assertGreater(snapshot["result"]["outlier_count"], 0)
        self.assertIsNotNone(snapshot["result"]["forecast"]["price"])
        xlsx = self.client.post("/api/report", json=snapshot)
        self.assertEqual(xlsx.status_code, 200, xlsx.text[:100] if xlsx.status_code != 200 else "")
        wb = load_workbook(BytesIO(xlsx.content), data_only=True)
        self.assertEqual(len(wb.sheetnames), 5)
        self.assertEqual(wb["Ringkasan Eksekutif"]["B21"].value, snapshot["result"]["benchmark"])
        request["choices"][original["evidence"][0]["price_observation_id"]] = {"decision": "EXCLUDE"}
        missing = self.client.post("/api/analyze", json=request)
        self.assertEqual(missing.status_code, 422)
        self.assertIn("justifikasi", missing.json()["detail"])
