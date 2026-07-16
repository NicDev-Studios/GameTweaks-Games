import copy
import json
import unittest
from pathlib import Path

from jsonschema.validators import validator_for


ROOT = Path(__file__).resolve().parent.parent


class ModSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((ROOT / "schemas/mod.schema.json").read_text())
        cls.example = json.loads((ROOT / "examples/mod.json").read_text())
        validator = validator_for(cls.schema)
        validator.check_schema(cls.schema)
        cls.validator = validator(cls.schema)

    def assert_valid(self, definition: dict) -> None:
        errors = list(self.validator.iter_errors(definition))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def assert_invalid(self, definition: dict) -> None:
        self.assertTrue(list(self.validator.iter_errors(definition)))

    def definition(self) -> dict:
        return copy.deepcopy(self.example)

    def test_agent_integration_requires_a_semantic_agent_version(self) -> None:
        self.assert_valid(self.definition())

        missing = self.definition()
        del missing["compatibility"]["minimumAgentVersion"]
        self.assert_invalid(missing)

        for version in ("latest", "01.2.3", "1.2.3-01", "1.2.3-alpha..1"):
            invalid = self.definition()
            invalid["compatibility"]["minimumAgentVersion"] = version
            with self.subTest(version=version):
                self.assert_invalid(invalid)

    def test_config_file_integration_forbids_an_agent_version(self) -> None:
        definition = self.definition()
        definition["integration"] = "configFile"
        del definition["compatibility"]["minimumAgentVersion"]
        self.assert_valid(definition)

        definition["compatibility"]["minimumAgentVersion"] = "0.1.0"
        self.assert_invalid(definition)


if __name__ == "__main__":
    unittest.main()
