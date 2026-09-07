"""Loader and validator for the echolocation parameter registry.

parameters.json is the only place a parameter is defined. Importers resolve
source column headings through resolve(), coerce units through to_canonical()
and range-check through validate(); none of them name a parameter in code.
Adding a parameter is therefore an edit to parameters.json alone.

Self-check the registry:   uv run data/calls/parameter_registry.py --check
List what is registered:   uv run data/calls/parameter_registry.py --list
Resolve a source heading:  uv run data/calls/parameter_registry.py --resolve "FmaxE"
"""
import json
import re
import sys
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "parameters.json"

REQUIRED_KEYS = {"id", "label", "group", "value_type", "status", "definition"}
NUMERIC_KEYS = {"unit", "sane_min", "sane_max"}
VALUE_TYPES = {"numeric", "categorical", "boolean"}
STATUSES = {"core", "extended", "proposed", "deprecated"}


class RegistryError(Exception):
    """Raised when parameters.json is internally inconsistent."""


def normalise(text: str) -> str:
    """Fold a source column heading to alias form: lowercase, alphanumeric+spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.strip().lower())).strip()


class Registry:
    def __init__(self, path: Path = REGISTRY_PATH):
        self.raw = json.loads(path.read_text(encoding="utf-8"))
        self.units = self.raw["unit_conversions"]
        self.groups = self.raw["groups"]
        self.parameters = {p["id"]: p for p in self.raw["parameters"]}
        self._alias_index = self._build_alias_index()

    def _build_alias_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for pid, param in self.parameters.items():
            keys = [pid, param["label"], *param.get("aliases", [])]
            for key in keys:
                folded = normalise(key)
                if folded in index and index[folded] != pid:
                    raise RegistryError(
                        f"alias {folded!r} is claimed by both {index[folded]!r} and {pid!r}"
                    )
                index[folded] = pid
        return index

    # -- lookup ---------------------------------------------------------

    def resolve(self, heading: str) -> str | None:
        """Map a source column heading to a parameter id, or None if unknown.

        Returning None rather than guessing is deliberate: an unrecognised
        column is reported to the importer's operator, who either adds an
        alias to parameters.json or decides the column is out of scope.
        """
        return self._alias_index.get(normalise(heading))

    def get(self, parameter_id: str) -> dict:
        try:
            return self.parameters[parameter_id]
        except KeyError:
            raise RegistryError(f"unknown parameter {parameter_id!r}") from None

    def by_group(self, group: str) -> list[dict]:
        return [p for p in self.parameters.values() if p["group"] == group]

    def core_ids(self) -> list[str]:
        return [pid for pid, p in self.parameters.items() if p["status"] == "core"]

    # -- coercion and checking ------------------------------------------

    def to_canonical(self, parameter_id: str, value: float, unit: str) -> tuple[float, str]:
        """Convert a value into the parameter's canonical unit."""
        param = self.get(parameter_id)
        if param["value_type"] != "numeric":
            raise RegistryError(f"{parameter_id!r} is not numeric")
        conversion = self.units.get(unit)
        if conversion is None:
            raise RegistryError(f"unknown unit {unit!r} for {parameter_id!r}")
        target = param["unit"]
        if conversion["to"] != target:
            raise RegistryError(
                f"unit {unit!r} converts to {conversion['to']!r}, "
                f"but {parameter_id!r} is measured in {target!r}"
            )
        return value * conversion["factor"], target

    def validate(self, parameter_id: str, value, unit: str | None = None) -> list[str]:
        """Return a list of problems with one value. Empty list means it passes."""
        param = self.get(parameter_id)
        problems: list[str] = []

        if param["status"] == "deprecated":
            replacement = param.get("superseded_by", "nothing")
            problems.append(f"{parameter_id!r} is deprecated, superseded by {replacement!r}")

        if param["value_type"] == "numeric":
            if unit is None:
                problems.append(f"{parameter_id!r} needs a unit")
                return problems
            try:
                canonical, _ = self.to_canonical(parameter_id, float(value), unit)
            except (RegistryError, TypeError, ValueError) as exc:
                problems.append(str(exc))
                return problems
            if not param["sane_min"] <= canonical <= param["sane_max"]:
                problems.append(
                    f"{canonical:g} {param['unit']} is outside the plausible range "
                    f"{param['sane_min']}-{param['sane_max']} for {parameter_id!r}"
                )
        elif param["value_type"] == "categorical":
            if value not in param["values"]:
                problems.append(
                    f"{value!r} is not one of the accepted values for {parameter_id!r}: "
                    f"{', '.join(sorted(param['values']))}"
                )
        elif param["value_type"] == "boolean":
            if not isinstance(value, bool):
                problems.append(f"{parameter_id!r} takes true or false, got {value!r}")

        return problems

    # -- registry self-check --------------------------------------------

    def check(self) -> list[str]:
        """Validate parameters.json itself. Empty list means the registry is sound."""
        problems: list[str] = []
        for pid, param in self.parameters.items():
            missing = REQUIRED_KEYS - param.keys()
            if missing:
                problems.append(f"{pid}: missing required key(s) {', '.join(sorted(missing))}")
            if param.get("value_type") not in VALUE_TYPES:
                problems.append(f"{pid}: value_type must be one of {', '.join(sorted(VALUE_TYPES))}")
            if param.get("status") not in STATUSES:
                problems.append(f"{pid}: status must be one of {', '.join(sorted(STATUSES))}")
            if param.get("group") not in self.groups:
                problems.append(f"{pid}: group {param.get('group')!r} is not declared in \"groups\"")

            if param.get("value_type") == "numeric":
                absent = NUMERIC_KEYS - param.keys()
                if absent:
                    problems.append(f"{pid}: numeric parameter needs {', '.join(sorted(absent))}")
                else:
                    if param["sane_min"] >= param["sane_max"]:
                        problems.append(f"{pid}: sane_min must be below sane_max")
                    unit = param["unit"]
                    if unit != "count" and unit not in {c["to"] for c in self.units.values()}:
                        problems.append(f"{pid}: unit {unit!r} is not a target of any conversion")
            elif param.get("value_type") == "categorical" and not param.get("values"):
                problems.append(f"{pid}: categorical parameter needs a \"values\" vocabulary")

            if param.get("status") == "deprecated" and "superseded_by" not in param:
                problems.append(f"{pid}: deprecated parameter should name superseded_by")
        return problems


def _cli() -> int:
    registry = Registry()
    args = sys.argv[1:]

    if not args or args[0] == "--check":
        problems = registry.check()
        for problem in problems:
            print(f"  ! {problem}")
        counts = {}
        for param in registry.parameters.values():
            counts[param["status"]] = counts.get(param["status"], 0) + 1
        summary = ", ".join(f"{n} {status}" for status, n in sorted(counts.items()))
        print(f"{len(registry.parameters)} parameters registered ({summary})")
        print(f"{len(registry._alias_index)} source-heading aliases indexed")
        print("Registry OK" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0

    if args[0] == "--list":
        for group, description in registry.groups.items():
            print(f"\n{group} — {description}")
            for param in registry.by_group(group):
                unit = f" [{param['unit']}]" if param["value_type"] == "numeric" else ""
                print(f"  {param['status']:9} {param['id']}{unit}")
        return 0

    if args[0] == "--resolve" and len(args) > 1:
        heading = " ".join(args[1:])
        resolved = registry.resolve(heading)
        print(f"{heading!r} -> {resolved!r}" if resolved else f"{heading!r} is not registered")
        return 0 if resolved else 1

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
