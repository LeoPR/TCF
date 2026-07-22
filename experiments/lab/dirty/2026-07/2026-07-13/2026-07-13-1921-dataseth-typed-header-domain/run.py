"""Research runner: typed header domains for DatasetH primitive scalars.

This is a dirty-lab prototype, not the #TCF.8H grammar. It studies two ways to
keep TCF's ordinary body string-oriented while preserving primitive identity:

1. HDOM: a typed per-column domain lives in the header and a bN index stream
   selects its entries. This is the direct form of ``null = index_ref``.
2. HK: the header maps a small stream of *kinds*; ordinary scalar payloads are
   still passed through ``tcf.encode(list[str])``. Null/non-finites have no
   payload and therefore never collide with strings such as ``"null"``.

Both are deliberately external and use #PROTO magic. No TCF core grammar is
claimed or modified here.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from tcf import decode as tcf_decode  # noqa: E402
from tcf import encode as tcf_encode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402


HDOM_MAGIC = b"#PROTO.HDOM value"
HK_MAGIC = b"#PROTO.HK value"


class PrototypeDecodeError(ValueError):
    """Malformed research wire."""


@dataclass(frozen=True)
class Atom:
    """Semantic atom; special values are kinds, never magic string payloads."""

    kind: str
    payload: str | None = None


FIXED_KINDS = {
    "true": "t",
    "false": "f",
    "null": "z",
    "nan": "q",
    "pos_inf": "p",
    "neg_inf": "m",
}
PAYLOAD_KINDS = {"string": "s", "integer": "i", "number": "d"}
CODE_TO_KIND = {code: kind for kind, code in {**FIXED_KINDS, **PAYLOAD_KINDS}.items()}
CODE_ORDER = tuple("sidtfzqpm")


def atom_from_python(value: object) -> Atom:
    """Maps Python primitives into a semantic, reflexive identity domain."""
    if value is None:
        return Atom("null")
    if isinstance(value, bool):
        return Atom("true" if value else "false")
    if isinstance(value, int):
        return Atom("integer", str(value))
    if isinstance(value, float):
        if math.isnan(value):
            return Atom("nan")
        if value == math.inf:
            return Atom("pos_inf")
        if value == -math.inf:
            return Atom("neg_inf")
        return Atom("number", repr(value))
    if isinstance(value, str):
        return Atom("string", value)
    raise TypeError(f"unsupported scalar: {type(value).__name__}")


def atom_to_python(atom: Atom) -> object:
    """Output adapter used only by this lab; JSON-standard output remains separate."""
    if atom.kind == "null":
        return None
    if atom.kind == "true":
        return True
    if atom.kind == "false":
        return False
    if atom.kind == "nan":
        return float("nan")
    if atom.kind == "pos_inf":
        return math.inf
    if atom.kind == "neg_inf":
        return -math.inf
    if atom.kind == "integer":
        return int(atom.payload or "")
    if atom.kind == "number":
        return float(atom.payload or "")
    if atom.kind == "string":
        return atom.payload or ""
    raise PrototypeDecodeError(f"unknown atom kind {atom.kind!r}")


def atoms(values: list[object]) -> list[Atom]:
    return [atom_from_python(value) for value in values]


def width_for(cardinality: int) -> int | None:
    if cardinality <= 1:
        return 0
    if cardinality <= 2:
        return 1
    if cardinality <= 4:
        return 2
    if cardinality <= 16:
        return 4
    return None


def pack(indices: list[int], width: int) -> bytes:
    if width == 0:
        return b""
    bits = "".join(f"{index:0{width}b}" for index in indices)
    bits += "0" * ((-len(bits)) % 8)
    return bytes(int(bits[offset : offset + 8], 2) for offset in range(0, len(bits), 8))


def unpack(raw: bytes, width: int, count: int) -> list[int]:
    expected = (count * width + 7) // 8
    if len(raw) != expected:
        raise PrototypeDecodeError(
            f"bad packed length: got {len(raw)}, expected {expected} for n={count}, w={width}"
        )
    if width == 0:
        return [0] * count
    bits = "".join(f"{byte:08b}" for byte in raw)
    return [int(bits[offset : offset + width], 2) for offset in range(0, count * width, width)]


def atom_code(atom: Atom) -> str:
    try:
        return FIXED_KINDS[atom.kind]
    except KeyError:
        try:
            return PAYLOAD_KINDS[atom.kind]
        except KeyError as exc:
            raise TypeError(f"unknown atom kind {atom.kind!r}") from exc


def atom_token(atom: Atom) -> str:
    """One-line, self-delimiting typed domain entry for a textual header."""
    code = atom_code(atom)
    if atom.kind in FIXED_KINDS:
        return code
    payload = (atom.payload or "").encode("utf-8")
    return f"{code}{len(payload)}:{payload.hex()}"


def parse_atom_token(token: str) -> Atom:
    if not token:
        raise PrototypeDecodeError("empty domain token")
    code = token[0]
    if code not in CODE_TO_KIND:
        raise PrototypeDecodeError(f"unknown domain code {code!r}")
    kind = CODE_TO_KIND[code]
    if kind in FIXED_KINDS:
        if token != code:
            raise PrototypeDecodeError(f"fixed atom has payload: {token!r}")
        return Atom(kind)
    try:
        length_text, hex_payload = token[1:].split(":", 1)
        length = int(length_text)
        payload = bytes.fromhex(hex_payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PrototypeDecodeError(f"invalid typed payload {token!r}") from exc
    if len(payload) != length:
        raise PrototypeDecodeError(f"typed payload length mismatch in {token!r}")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PrototypeDecodeError(f"non-UTF-8 typed payload {token!r}") from exc
    if kind == "integer" and str(int(text)) != text:
        raise PrototypeDecodeError(f"non-canonical integer payload {text!r}")
    if kind == "number":
        try:
            value = float(text)
        except ValueError as exc:
            raise PrototypeDecodeError(f"invalid finite number payload {text!r}") from exc
        if not math.isfinite(value) or repr(value) != text:
            raise PrototypeDecodeError(f"non-canonical finite number payload {text!r}")
    return Atom(kind, text)


def _header_parts(header: bytes, magic: bytes) -> dict[str, str]:
    if not header.startswith(magic + b";"):
        raise PrototypeDecodeError(f"bad magic/header {header!r}")
    parts: dict[str, str] = {}
    for part in header[len(magic) + 1 :].decode("ascii").split(";"):
        if "=" not in part:
            raise PrototypeDecodeError(f"malformed header part {part!r}")
        key, value = part.split("=", 1)
        if key in parts:
            raise PrototypeDecodeError(f"duplicate header key {key!r}")
        parts[key] = value
    return parts


# ------------------------------------------------------------------------- HDOM

def encode_hdom(values: list[object]) -> bytes | None:
    """Header typed-domain + packed index stream; None means bN is inapplicable."""
    source = atoms(values)
    domain = list(dict.fromkeys(source))
    width = width_for(len(domain))
    if width is None:
        return None
    index = {atom: position for position, atom in enumerate(domain)}
    header = (
        HDOM_MAGIC
        + f";n={len(source)};b={width};d=".encode("ascii")
        + ",".join(atom_token(atom) for atom in domain).encode("ascii")
    )
    return header + b"\n" + pack([index[atom] for atom in source], width)


def decode_hdom(blob: bytes) -> list[Atom]:
    try:
        header, body = blob.split(b"\n", 1)
        parts = _header_parts(header, HDOM_MAGIC)
        count, width = int(parts["n"]), int(parts["b"])
    except (KeyError, ValueError) as exc:
        raise PrototypeDecodeError("invalid HDOM header") from exc
    if count < 0 or width not in (0, 1, 2, 4):
        raise PrototypeDecodeError("invalid HDOM count or width")
    domain = [parse_atom_token(token) for token in parts.get("d", "").split(",") if token]
    if not domain or len(set(domain)) != len(domain):
        raise PrototypeDecodeError("HDOM domain must be non-empty and distinct")
    if width_for(len(domain)) != width:
        raise PrototypeDecodeError("HDOM width does not match domain cardinality")
    indices = unpack(body, width, count)
    if any(index >= len(domain) for index in indices):
        raise PrototypeDecodeError("HDOM index outside domain")
    return [domain[index] for index in indices]


# --------------------------------------------------------------------------- HK

def encode_hk(values: list[object]) -> bytes:
    """Header kind-map + packed kind indices + ordinary TCF string payload body."""
    source = atoms(values)
    active_codes = tuple(code for code in CODE_ORDER if any(atom_code(atom) == code for atom in source))
    width = width_for(len(active_codes))
    if width is None:  # Defensive: this prototype has at most nine kinds.
        raise AssertionError("kind registry unexpectedly exceeds b4")
    index = {code: position for position, code in enumerate(active_codes)}
    payloads = [atom.payload or "" for atom in source if atom.kind in PAYLOAD_KINDS]
    payload_body = tcf_encode(payloads).encode("utf-8") if payloads else b""
    header = (
        HK_MAGIC
        + f";n={len(source)};b={width};k={''.join(active_codes)};l={len(payload_body)}".encode("ascii")
    )
    type_body = pack([index[atom_code(atom)] for atom in source], width)
    return header + b"\n" + type_body + payload_body


def decode_hk(blob: bytes) -> list[Atom]:
    try:
        header, rest = blob.split(b"\n", 1)
        parts = _header_parts(header, HK_MAGIC)
        count, width, payload_len = int(parts["n"]), int(parts["b"]), int(parts["l"])
        active_codes = tuple(parts["k"])
    except (KeyError, ValueError) as exc:
        raise PrototypeDecodeError("invalid HK header") from exc
    if count < 0 or payload_len < 0 or width not in (0, 1, 2, 4):
        raise PrototypeDecodeError("invalid HK count, width, or payload length")
    if not active_codes or any(code not in CODE_TO_KIND for code in active_codes):
        raise PrototypeDecodeError("unknown HK kind code")
    if len(set(active_codes)) != len(active_codes) or tuple(sorted(active_codes, key=CODE_ORDER.index)) != active_codes:
        raise PrototypeDecodeError("HK kind codes must be unique and canonical")
    if width_for(len(active_codes)) != width:
        raise PrototypeDecodeError("HK width does not match kind cardinality")
    type_len = (count * width + 7) // 8
    if len(rest) != type_len + payload_len:
        raise PrototypeDecodeError("HK body lengths do not match header")
    indices = unpack(rest[:type_len], width, count)
    if any(index >= len(active_codes) for index in indices):
        raise PrototypeDecodeError("HK index outside kind map")
    try:
        payloads = iter(tcf_decode(rest[type_len:].decode("utf-8"))) if payload_len else iter(())
    except (UnicodeDecodeError, ValueError) as exc:
        raise PrototypeDecodeError("invalid TCF payload body") from exc

    decoded: list[Atom] = []
    for index in indices:
        kind = CODE_TO_KIND[active_codes[index]]
        if kind in PAYLOAD_KINDS:
            try:
                payload = next(payloads)
            except StopIteration as exc:
                raise PrototypeDecodeError("HK payload body ended early") from exc
            decoded.append(parse_atom_token(atom_code(Atom(kind, payload)) + f"{len(payload.encode('utf-8'))}:{payload.encode('utf-8').hex()}"))
        else:
            decoded.append(Atom(kind))
    try:
        next(payloads)
    except StopIteration:
        return decoded
    raise PrototypeDecodeError("HK payload body has extra values")


# ---------------------------------------------------------------- naive proof

def naive_string_domain(values: list[object]) -> tuple[list[str], list[int], dict[str, int]]:
    """The tempting but lossy proposal: stringify specials, then map their index."""
    def spelling(value: object) -> str:
        atom = atom_from_python(value)
        if atom.kind == "null":
            return "null"
        if atom.kind == "nan":
            return "NaN"
        if atom.kind == "pos_inf":
            return "Infinity"
        if atom.kind == "neg_inf":
            return "-Infinity"
        return atom.payload or atom.kind

    strings = [spelling(value) for value in values]
    domain = list(dict.fromkeys(strings))
    index = {value: position for position, value in enumerate(domain)}
    spellings = {
        "null": "null",
        "nan": "NaN",
        "pos_inf": "Infinity",
        "neg_inf": "-Infinity",
    }
    special_refs = {kind: index[text] for kind, text in spellings.items() if text in index}
    return domain, [index[value] for value in strings], special_refs


def leaf_tag_bytes(values: list[object]) -> bytes:
    """Per-occurrence typed tag baseline: no shared header domain or core payload."""
    pieces = [b"#PROTO.V\n"]
    for atom in atoms(values):
        if atom.kind in FIXED_KINDS:
            pieces.append(b"V" + atom_code(atom).encode("ascii") + b"\n")
        else:
            raw = (atom.payload or "").encode("utf-8")
            pieces.append(atom_code(atom).encode("ascii") + str(len(raw)).encode("ascii") + b":" + raw)
    return b"".join(pieces)


def assert_round_trip(label: str, values: list[object]) -> tuple[int | None, int, int]:
    expected = atoms(values)
    hdom = encode_hdom(values)
    if hdom is not None:
        hdom_back = decode_hdom(hdom)
        assert hdom_back == expected, f"HDOM RT failed: {label}"
        assert atoms([atom_to_python(atom) for atom in hdom_back]) == expected, (
            f"HDOM output-adapter RT failed: {label}"
        )
    hk = encode_hk(values)
    hk_back = decode_hk(hk)
    assert hk_back == expected, f"HK RT failed: {label}"
    assert atoms([atom_to_python(atom) for atom in hk_back]) == expected, (
        f"HK output-adapter RT failed: {label}"
    )
    return (len(hdom) if hdom is not None else None, len(hk), len(leaf_tag_bytes(values)))


def write_artifacts(
    results: list[tuple[str, int | None, int, int]], profiles: dict[str, list[object]]
) -> None:
    artifacts = Path(__file__).resolve().parent / "artifacts"
    artifacts.mkdir(exist_ok=True)

    collision = [None, "null", float("nan"), "NaN", math.inf, "Infinity", -math.inf, "-Infinity"]
    domain, indices, refs = naive_string_domain(collision)
    (artifacts / "01-naive-counterexample.txt").write_text(
        "Naive string-domain counterexample\n\n"
        f"input semantic atoms: {atoms(collision)!r}\n"
        f"stringified domain: {domain!r}\n"
        f"per-row indices: {indices!r}\n"
        f"header special refs: {refs!r}\n\n"
        "Both null and literal 'null' point to the same ordinary string-domain index.\n"
        "A header declaration null=<index> cannot recover which occurrences were null.\n"
        "The domain must be typed, or the stream must carry a distinct kind code per occurrence.\n",
        encoding="utf-8",
    )

    sample = [None, "null", float("nan"), "NaN", math.inf, "Infinity", -math.inf, "-Infinity", -0.0, 0.0]
    hdom = encode_hdom(sample)
    assert hdom is not None
    hk = encode_hk(sample)
    (artifacts / "02-hdom-sample.txt").write_text(
        hdom.split(b"\n", 1)[0].decode("ascii")
        + "\nbody-packed-hex="
        + hdom.split(b"\n", 1)[1].hex()
        + "\n",
        encoding="utf-8",
    )
    hk_head, hk_body = hk.split(b"\n", 1)
    (artifacts / "03-hk-sample.txt").write_text(
        hk_head.decode("ascii")
        + "\nbody-kind-and-tcf-hex="
        + hk_body.hex()
        + "\n",
        encoding="utf-8",
    )

    lines = ["profile | hdom typed-domain | hk kind-map + TCF strings | per-leaf tags"]
    for label, hdom_len, hk_len, leaf_len in results:
        hdom_text = str(hdom_len) if hdom_len is not None else "N/A (k>16)"
        lines.append(f"{label} | {hdom_text} | {hk_len} | {leaf_len}")
    (artifacts / "04-bytes-comparison.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # The HK payload is a genuine existing TCF body, not a mock string codec.
    sample_payloads = [atom.payload or "" for atom in atoms(sample) if atom.kind in PAYLOAD_KINDS]
    side_outputs = SideOutputs()
    payload_tcf = tcf_encode(sample_payloads, side_outputs=side_outputs)
    hk_parts = _header_parts(hk_head, HK_MAGIC)
    type_len = (int(hk_parts["n"]) * int(hk_parts["b"]) + 7) // 8
    assert hk_body[type_len:] == payload_tcf.encode("utf-8"), "HK changed the ordinary TCF payload"
    (artifacts / "05-hk-string-payload.tcf.txt").write_text(payload_tcf, encoding="utf-8")
    (artifacts / "06-hk-string-payload-obat-hcc-trace.txt").write_text(
        "HK ordinary payload SideOutputs\n\n"
        f"column_features={side_outputs.column_features!r}\n"
        f"cadence_detected={side_outputs.cadence_detected!r}\n"
        f"cadence_info={side_outputs.cadence_info!r}\n"
        f"min_len={side_outputs.min_len!r}\n"
        f"body_bytes={side_outputs.body_bytes!r}\n"
        f"seq_rle_runs={side_outputs.seq_rle_runs!r}\n\n"
        "OBAT log:\n"
        + (side_outputs.obat_log or "(empty)\n")
        + "\nHCC trace:\n"
        + (side_outputs.hcc_trace or "(empty)\n"),
        encoding="utf-8",
    )

    round_trip_lines = ["profile | HDOM typed-domain | HK kind-map + TCF strings | Python output adapter"]
    for label, hdom_len, _hk_len, _leaf_len in results:
        hdom_status = "OK" if hdom_len is not None else "N/A (k>16)"
        round_trip_lines.append(f"{label} | {hdom_status} | OK | OK")
    (artifacts / "07-roundtrip.txt").write_text("\n".join(round_trip_lines) + "\n", encoding="utf-8")

    profile_lines = ["Synthetic profiles (constructed to falsify collisions, not real-world data).", ""]
    for label, values in profiles.items():
        profile_lines.append(f"{label} (n={len(values)}): {atoms(values)!r}")
    (artifacts / "08-input-profiles.txt").write_text("\n".join(profile_lines) + "\n", encoding="utf-8")


def main() -> None:
    nan = float("nan")
    inf = math.inf
    profiles = {
        "collision-matrix": [None, "null", nan, "NaN", inf, "Infinity", -inf, "-Infinity", -0.0, 0.0, 1, 1.0, "1", True, False],
        "specials-dense-100": [None, nan, inf, -inf] * 25,
        "low-card-mixed-100": ["ok", "null", None, "NaN", nan] * 20,
        "sparse-special-high-card": [f"value-{index:03d}" for index in range(100)] + [None, "null", nan, "NaN", inf, "Infinity"],
        "numbers-and-strings": [1, "1", 1.0, "1.0", -0.0, 0.0, True, False] * 12,
    }

    results = []
    for label, values in profiles.items():
        results.append((label, *assert_round_trip(label, values)))

    # The decisive collision: mapping only a string-domain index cannot distinguish
    # a primitive sentinel from a literal that spells it.
    naive_domain, naive_indices, naive_refs = naive_string_domain([None, "null"])
    assert naive_domain == ["null"] and naive_indices == [0, 0] and naive_refs["null"] == 0

    # Typed alternatives preserve every pair that the DatasetH plan treats as distinct.
    pairs = [
        (None, "null"),
        (nan, "NaN"),
        (inf, "Infinity"),
        (-inf, "-Infinity"),
        (-0.0, 0.0),
        (1, 1.0),
        (1, "1"),
        (True, 1),
    ]
    for left, right in pairs:
        assert atoms([left]) != atoms([right]), f"semantic collision: {left!r} vs {right!r}"
        assert encode_hk([left]) != encode_hk([right]), f"HK wire collision: {left!r} vs {right!r}"
        left_hdom, right_hdom = encode_hdom([left]), encode_hdom([right])
        assert left_hdom != right_hdom, f"HDOM wire collision: {left!r} vs {right!r}"

    # One malformed header check: an index code outside the declared header map must fail loudly.
    try:
        decode_hk(b"#PROTO.HK value;n=1;b=1;k=z;l=0\n\x80")
    except PrototypeDecodeError:
        pass
    else:
        raise AssertionError("HK out-of-range index must fail loudly")

    write_artifacts(results, profiles)
    print("typed-header-domain: all checks PASS")
    print("  naive string-domain: refuted by null vs 'null' counterexample")
    print("  HDOM: typed domain in header + bN indices")
    print("  HK: header kind map + ordinary TCF string payload body")
    for label, hdom_len, hk_len, leaf_len in results:
        hdom_text = str(hdom_len) if hdom_len is not None else "N/A"
        print(f"  {label}: HDOM={hdom_text} HK={hk_len} V={leaf_len}")


if __name__ == "__main__":
    main()