from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "project_inventory"))
from scanner import scan_project


def test_scan_project_detects_language_and_aws(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('resource "aws_s3_bucket" "x" {}\n', encoding="utf-8")
    (tmp_path / "app.py").write_text("import boto3\nboto3.client('lambda')\n", encoding="utf-8")
    result = scan_project(tmp_path)
    assert result["languages"]["Terraform"] == 1
    assert result["languages"]["Python"] == 1
    assert "S3" in result["signals"]["aws_services"]
    assert "Lambda" in result["signals"]["aws_services"]
