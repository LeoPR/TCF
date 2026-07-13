"""Reproducible R0/R1 checks for the provisional DatasetH bridge."""

from __future__ import annotations

import json

from dataset_h import DatasetH, DuplicateFieldError, NonStandardJsonConstantError


SOURCE_JSON = """{
  "id": 7,
  "active": true,
  "nullable": null,
  "profile": {
    "name": "Ada",
    "nickname": ""
  },
  "contacts": [
    {"kind": "email", "value": "ada@example.test", "verified": true},
    {"kind": "phone", "value": "+55 11 99999-0000"}
  ],
  "matrix": [[1, 2], [], [3]],
  "notes": "line 1\\nline 2",
  "empty_object": {},
  "empty_list": [],
  "score": 1.5
}"""


PYTHON_SOURCE = {
    "id": 7,
    "active": True,
    "nullable": None,
    "profile": {
        "name": "Ada",
        "nickname": "",
    },
    "contacts": [
        {"kind": "email", "value": "ada@example.test", "verified": True},
        {"kind": "phone", "value": "+55 11 99999-0000"},
    ],
    "matrix": [[1, 2], [], [3]],
    "notes": "line 1\nline 2",
    "empty_object": {},
    "empty_list": [],
    "score": 1.5,
}


def main() -> None:
    from_json = DatasetH.from_json(SOURCE_JSON)
    from_python = DatasetH.from_python(PYTHON_SOURCE)

    assert from_json == from_python
    assert DatasetH.from_json(from_json.to_json()) == from_json
    assert json.loads(from_json.to_json()) == json.loads(SOURCE_JSON)

    try:
        DatasetH.from_json('{"a": 1, "a": 2}')
    except DuplicateFieldError:
        pass
    else:
        raise AssertionError("duplicate JSON fields must be rejected")

    try:
        DatasetH.from_json('{"value": NaN}')
    except NonStandardJsonConstantError:
        pass
    else:
        raise AssertionError("non-standard JSON constants must be rejected")

    print("DatasetH root: {}".format(type(from_json.root).__name__))
    print("JSON -> DatasetH -> JSON: PASS")
    print("Python source -> DatasetH equivalence: PASS")
    print("duplicate-field policy: reject")
    print("NaN/Infinity policy: reject")
    print("TCF codec: intentionally not exercised")


if __name__ == "__main__":
    main()
