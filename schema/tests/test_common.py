import json
import sys
import urllib.parse
from pathlib import Path

import jsonschema.validators
import referencing
import yaml

base_dir = Path(__file__).parent.parent

failed = False


def make_registry(schema_dir: Path) -> referencing.Registry:
    def file_retrieve(uri):
        path = schema_dir / urllib.parse.urlparse(uri).path.removeprefix("/")
        result = json.loads(path.read_text(encoding="utf-8"))
        return referencing.Resource.from_contents(result)

    return referencing.Registry(retrieve=file_retrieve)


def get_validator(registry: referencing.Registry, schema_name: str):
    schema = registry.get_or_retrieve(schema_name).value.contents
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema, registry=registry)


def test_file(file: Path, schema_key: str, validator):
    global failed

    example_base_name = file.stem

    print(f"   Validating example '{example_base_name}' against schema '{schema_key}'", end="", flush=True)

    if file.suffix == ".yaml":
        json_data = yaml.safe_load(file.read_text())
    else:
        json_data = json.loads(file.read_text())
    errors = list(validator.iter_errors(json_data))

    has_errors = bool(errors)
    expects_errors = file.stem.endswith(".FAIL")
    if expects_errors != has_errors:
        print("\r❌")
        failed = True

        if expects_errors:
            print("\tExpected to fail, but didn't")
        else:
            # Deepest first - shallow errors are usually consequences of the deep ones
            errors.sort(key=lambda e: -len(e.path))

            print(f"\t'{example_base_name}' does not match schema '{schema_key}':")
            for e in errors:
                print(f"\t- {e.json_path}: {e.message}")

    else:
        print("\r✅")


def test_directory(dir: Path, schema_key: str, validator):
    for file in sorted(dir.glob("**/*")):
        if file.is_file():
            test_file(file, schema_key, validator)


def test_schemas(dirname):
    examples_dir = base_dir / "examples" / dirname
    registry = make_registry(base_dir / "generated" / dirname)

    for entry in sorted(examples_dir.glob("*")):
        schema_key = entry.stem
        schema = get_validator(registry, f"/{schema_key}.schema.json")

        if entry.is_dir():
            test_directory(entry, schema_key, schema)
        else:
            test_file(entry, schema_key, schema)

    if failed:
        sys.exit(-1)
