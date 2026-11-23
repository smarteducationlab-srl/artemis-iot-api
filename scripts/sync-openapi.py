#!/usr/bin/env python3
"""Check or refresh the public Swagger snapshot from the deployed gateway."""

import argparse
import sys
from pathlib import Path
from urllib.request import urlopen

import yaml
from openapi_spec_validator import validate
from openapi_spec_validator.exceptions import OpenAPIError
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError


SOURCE = "https://iot.artemis.cnaf.infn.it/lab/openapi.yaml"
DESTINATION = Path(__file__).resolve().parents[1] / "openapi.yaml"
METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def fetch_public_spec():
    with urlopen(SOURCE, timeout=15) as response:
        if response.geturl() != SOURCE:
            raise ValueError("unexpected redirect from the canonical gateway")
        limit = 2_000_000
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("OpenAPI response exceeds the size limit")
    return raw


def validate_public_spec(raw):
    spec = yaml.safe_load(raw)
    if not isinstance(spec, dict) or not str(spec.get("openapi", "")).startswith("3."):
        raise ValueError("expected an OpenAPI 3 specification")
    paths = spec.get("paths")
    if not isinstance(paths, dict) or not paths or any(
        not isinstance(path, str) or not path.startswith("/")
        or path.split("/", 2)[1] in {"internal", "lab", "actuator"}
        or not isinstance(operations, dict)
        for path, operations in paths.items()
    ):
        raise ValueError("expected a non-empty public API with no internal routes")
    if not isinstance(spec.get("info", {}).get("version"), str):
        raise ValueError("missing OpenAPI info.version")
    count = sum(len(METHODS.intersection(path)) for path in paths.values())
    if not count:
        raise ValueError("expected at least one public operation")

    def check_references(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if not isinstance(ref, str) or not ref.startswith("#/"):
                    raise ValueError("only local OpenAPI references are allowed")
                target = spec
                for segment in ref[2:].split("/"):
                    key = segment.replace("~1", "/").replace("~0", "~")
                    if not isinstance(target, dict) or key not in target:
                        raise ValueError(f"unresolved OpenAPI reference: {ref}")
                    target = target[key]
            for value in node.values():
                check_references(value)
        elif isinstance(node, list):
            for value in node:
                check_references(value)

    check_references(spec)
    try:
        validate(spec)
    except (OpenAPIError, OpenAPIValidationError) as exc:
        raise ValueError("invalid OpenAPI document") from exc
    return spec["info"]["version"], count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="replace the repository snapshot")
    mode.add_argument("--validate-local", action="store_true", help="validate the checked-in snapshot without network")
    args = parser.parse_args()
    try:
        raw = DESTINATION.read_bytes() if args.validate_local else fetch_public_spec()
        version, count = validate_public_spec(raw)
        if args.write:
            DESTINATION.write_bytes(raw)
        elif not args.validate_local and DESTINATION.read_bytes() != raw:
            print("Swagger differs from the deployed public spec; review a --write refresh.", file=sys.stderr)
            return 1
    except yaml.YAMLError:
        print("Gateway did not return valid OpenAPI YAML.", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"Cannot sync the public specification: {type(exc).__name__}", file=sys.stderr)
        return 1
    source = "snapshot" if args.validate_local else "deployed gateway"
    print(f"OpenAPI {version}: {count} public operations ({source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
