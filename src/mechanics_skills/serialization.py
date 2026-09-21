"""
Serialization utilities ensuring deterministic JSON output, stable key ordering,
UTF-8 encoding, and artifact persistence.
"""

import json
import os
from pathlib import Path
from typing import Any, Union


class MechanicsJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder supporting dataclasses and custom models."""

    def default(self, obj: Any) -> Any:
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()
        return super().default(obj)


def to_json(obj: Any, indent: int = 2) -> str:
    """Serialize object to formatted JSON string with sorted keys."""
    return json.dumps(
        obj,
        cls=MechanicsJSONEncoder,
        indent=indent,
        ensure_ascii=False,
        sort_keys=True,
    )


def write_json_file(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """Atomically write data to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp_path = p.with_suffix(p.suffix + ".tmp")
    content = to_json(data, indent=indent)
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(p)


def read_json_file(path: Union[str, Path]) -> Any:
    """Read and parse JSON file."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))
