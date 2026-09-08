import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "project_inventory"))
from scanner import scan_project, scan_roots


class ScannerTests(unittest.TestCase):
    def test_scan_project_detects_language_aws_and_evidence(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "main.tf").write_text('resource "aws_s3_bucket" "x" {}\n', encoding="utf-8")
            (path / "app.py").write_text("import boto3\nboto3.client('lambda')\n", encoding="utf-8")
            (path / "openapi.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")
            result = scan_project(path)
            self.assertEqual(result["languages"]["Terraform"], 1)
            self.assertEqual(result["languages"]["Python"], 1)
            self.assertIn("S3", result["signals"]["aws_services"])
            self.assertIn("Lambda", result["signals"]["aws_services"])
            self.assertTrue(any(e["kind"] == "aws_service" and e["file"] == "main.tf" for e in result["evidence"]))
            self.assertTrue(any(i["type"] == "http-api" for i in result["interfaces"]))
            self.assertTrue(any(r["name"] == "S3" for r in result["resources"]))

    def test_scan_roots_emits_v2_relationship_container(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "service-a").mkdir()
            (root / "service-a" / "go.mod").write_text("module example/service-a\n")
            data = scan_roots([root])
            self.assertEqual(data["version"], "2.0")
            self.assertIn("relationships", data)
            self.assertEqual(len(data["projects"]), 1)


if __name__ == "__main__":
    unittest.main()
