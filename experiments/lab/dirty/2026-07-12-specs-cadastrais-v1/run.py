"""Exploracao de specs cadastrais fora do core #TCF.8.

O laboratorio mede o blob completo do FLOOR, sempre com round-trip. Os specs
sao prototipos locais: nenhum deles entra no registry de src/tcf por este script.
"""
from __future__ import annotations

import math
import csv
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import TemplatedCheckedSpec, decode, encode  # noqa: E402
from tcf.natures.templated_checked import BASE94  # noqa: E402


class FixedDigitsDemo:
    """Spec local para medir codigo decimal fixo sem mascara ou DV."""

    def __init__(self, name: str, width: int):
        self.name = name
        self.width = width
        self.encoded_length = math.ceil(math.log(10**width, len(BASE94)))

    def encode_value(self, value: str) -> tuple[str, str]:
        if len(value) != self.width or not value.isdigit():
            return "_" + value, "format_mismatch"
        number = int(value)
        chars = []
        for _ in range(self.encoded_length):
            chars.append(BASE94[number % len(BASE94)])
            number //= len(BASE94)
        return "".join(reversed(chars)), "compressible"

    def decode_value(self, payload: str) -> str:
        if payload.startswith("_"):
            return payload[1:]
        number = 0
        for char in payload:
            number = number * len(BASE94) + BASE94.index(char)
        return str(number).zfill(self.width)


def masked_digits(name: str, pattern: str, widths: tuple[int, ...], separators: tuple[str, ...]):
    regex = re.compile(pattern)
    body_length = sum(widths)
    encoded_length = math.ceil(math.log(10**body_length, len(BASE94)))

    def formatter(digits: list[int]) -> str:
        text = "".join(str(digit) for digit in digits)
        out = []
        cursor = 0
        for width, separator in zip(widths, separators):
            out.append(text[cursor:cursor + width])
            out.append(separator)
            cursor += width
        return "".join(out[:-1])

    return TemplatedCheckedSpec(
        name=name,
        regex=regex,
        body_length=body_length,
        check_length=0,
        check_fn=lambda _body: [],
        formatter=formatter,
        encoded_length=encoded_length,
    )


def normalize(table: dict[str, list]) -> dict[str, list[str]]:
    return {name: ["" if value is None else str(value) for value in values]
            for name, values in table.items()}


def measure_single(label: str, values: list[str], spec) -> None:
    baseline = encode(values)
    candidate = encode(values, nature=spec)
    assert decode(candidate, nature=spec) == values
    print("single", label, len(values), len(baseline.encode()),
          len(candidate.encode()), candidate != baseline)


def measure_multi(label: str, table: dict[str, list[str]], column: str, spec) -> None:
    table = normalize(table)
    baseline = encode(table)
    candidate = encode(table, nature_per_col={column: spec})
    assert decode(candidate, nature_per_col={column: spec}) == table
    print("multi", label, len(next(iter(table.values()))), len(baseline.encode()),
          len(candidate.encode()), candidate != baseline)


def main() -> None:
    date_iso = masked_digits(
        "date-iso-demo", r"^(\d{4})-(\d{2})-(\d{2})$",
        (4, 2, 2), ("-", "-", ""),
    )
    phone_tpch = masked_digits(
        "phone-tpch-demo", r"^(\d{2})-(\d{3})-(\d{3})-(\d{4})$",
        (2, 3, 3, 4), ("-", "-", "-", ""),
    )
    datetime_iso = masked_digits(
        "datetime-iso-demo", r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$",
        (4, 2, 2, 2, 2, 2), ("-", "-", " ", ":", ":", ""),
    )
    cep = masked_digits(
        "cep-demo", r"^(\d{5})-(\d{3})$",
        (5, 3), ("-", ""),
    )
    rg_sp = masked_digits(
        "rg-sp-demo", r"^(\d{2})\.(\d{3})\.(\d{3})-(\d)$",
        (2, 3, 3, 1), (".", ".", "-", ""),
    )
    code11 = FixedDigitsDemo("code11-demo", 11)

    print("base lengths", len(BASE94),
          {width: {base: math.ceil(width * math.log(10, base))
                   for base in (64, len(BASE94), 96)}
           for width in (8, 9, 10, 11, 12, 15, 18)})

    with DatasetReader("br-identidades") as reader:
        people = normalize(reader.columns("pessoas", limit=5000))
        companies = normalize(reader.columns("empresas", limit=5000))
    with DatasetReader("tpch-sf001") as reader:
        customer = normalize(reader.columns("customer"))
        orders = normalize(reader.columns("orders"))
    with (ROOT / "datasets" / "samples" / "online-retail" /
          "online-retail-sample.csv").open(encoding="utf-8", newline="") as stream:
        online_dates = [row["InvoiceDate"] for row in csv.DictReader(stream)]

    measure_single("date-people", people["data_cadastro"], date_iso)
    measure_multi("date-people", people, "data_cadastro", date_iso)
    measure_multi("date-companies", companies, "data_abertura", date_iso)
    measure_multi("date-orders", orders, "o_orderdate", date_iso)
    measure_multi("phone-customer", customer, "c_phone", phone_tpch)
    measure_single("datetime-online-retail", online_dates, datetime_iso)

    rng = random.Random(20260712)
    cep_random = [
        f"{rng.randrange(100000000):08d}"[:5] + "-" + f"{rng.randrange(1000):03d}"
        for _ in range(5000)
    ]
    cep_cluster = [
        f"{index % 100000:05d}-{index % 1000:03d}"
        for index in range(5000)
    ]
    rg_random = [
        f"{rng.randrange(100):02d}.{rng.randrange(1000):03d}."
        f"{rng.randrange(1000):03d}-{rng.randrange(10)}"
        for _ in range(5000)
    ]
    rg_cluster = [
        f"{index // 100000:02d}.{index % 1000:03d}."
        f"{(index // 1000) % 1000:03d}-{index % 10}"
        for index in range(5000)
    ]
    code_random = [f"{rng.randrange(10**11):011d}" for _ in range(5000)]
    code_cluster = [f"{10**10 + index:011d}" for index in range(5000)]

    measure_single("cep-random", cep_random, cep)
    measure_single("cep-cluster", cep_cluster, cep)
    measure_single("rg-sp-random-shaped", rg_random, rg_sp)
    measure_single("rg-sp-sequential-shaped", rg_cluster, rg_sp)
    measure_single("code11-random", code_random, code11)
    measure_single("code11-sequential", code_cluster, code11)


if __name__ == "__main__":
    main()
