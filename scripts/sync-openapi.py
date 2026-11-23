#!/usr/bin/env python3
"""Check or refresh the public Swagger snapshot from the deployed gateway."""

import argparse
import sys
from pathlib import Path
from urllib.request import urlopen

import yaml


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
    return raw, spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="replace the repository snapshot")
    args = parser.parse_args()
    try:
        raw, spec = fetch_public_spec()
        if args.write:
            DESTINATION.write_bytes(raw)
        elif DESTINATION.read_bytes() != raw:
            print("Swagger differs from the deployed public spec; review a --write refresh.", file=sys.stderr)
            return 1
    except yaml.YAMLError:
        print("Gateway did not return valid OpenAPI YAML.", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"Cannot sync the public specification: {type(exc).__name__}", file=sys.stderr)
        return 1
    count = sum(len(METHODS.intersection(path)) for path in spec["paths"].values())
    print(f"OpenAPI {spec['info']['version']}: {count} deployed public operations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
