import runpy
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
validate_public_spec = runpy.run_path(str(ROOT / "scripts/sync-openapi.py"))["validate_public_spec"]


class OpenApiValidationTest(unittest.TestCase):
    def test_checked_in_snapshot(self):
        version, count = validate_public_spec((ROOT / "openapi.yaml").read_bytes())
        self.assertTrue(version)
        self.assertGreater(count, 0)

    def check_operation(self, operation):
        return validate_public_spec(yaml.safe_dump({
            "openapi": "3.0.3",
            "info": {"title": "Fixture", "version": "test"},
            "paths": {"/example": {"get": operation}},
        }).encode())

    def test_rejects_scalar_operation(self):
        with self.assertRaisesRegex(ValueError, "invalid OpenAPI"):
            self.check_operation(123)

    def test_rejects_operation_without_required_responses(self):
        with self.assertRaisesRegex(ValueError, "invalid OpenAPI"):
            self.check_operation({"summary": "No responses"})

    def test_rejects_external_reference_before_validation(self):
        with self.assertRaisesRegex(ValueError, "only local OpenAPI references"):
            self.check_operation({"responses": {"200": {"$ref": "https://fixture.invalid/response"}}})

    def test_accepts_valid_operation(self):
        self.assertEqual(("test", 1), self.check_operation({
            "responses": {"200": {"description": "OK"}},
        }))
