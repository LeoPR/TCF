"""natures_compiler — compila uma DEFINICAO TEXTUAL de filtro -> nature executavel.

Gadget AUXILIAR (scripts/, **NAO toca src/tcf**). Gera instancias de
`TemplatedCheckedSpec` / `TemplatedPaddedSpec` (de `src/tcf/natures/`) a partir de um
arquivo `.dsl` declarativo, e VALIDA reversibilidade (round-trip lossless) no compile-time.
A unica parte "codigo" (check_fn) vem de uma biblioteca FECHADA nomeada (reusa as do core;
zero codigo do usuario, zero eval).

DSL (flat `chave: valor`, sem dependencia de YAML):

    name: cpf
    template: NNN.NNN.NNN-DD      # N/D = digito; resto = literal
    body_length: 9
    check_length: 2
    check_algorithm: mod11-cpf    # mod11-cpf | mod11-cnpj | none

    # check_algorithm: none (TemplatedPaddedSpec) usa padding_slots + separator:
    # padding_slots: [3, 3, 3, 3]
    # separator: .

Limitacao conhecida (achado 2026-06-16): so' cobre o que os specs atuais suportam —
inteiros canonicos (sem zero a esquerda) no padded e digitos+mod11 no checked. CEP
(zeros a esquerda significativos) e MAC (hex) exigem um spec NOVO em src/tcf -> futuro.
"""
from __future__ import annotations

import math
import random
import re
import sys
from pathlib import Path

# importa os blocos do core SEM modifica-lo
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from tcf.natures import BASE94  # noqa: E402
from tcf.natures.templated_checked import (  # noqa: E402
    TemplatedCheckedSpec, _cpf_check_fn, _cnpj_check_fn,
)
from tcf.natures.templated_padded import TemplatedPaddedSpec  # noqa: E402

# biblioteca FECHADA de check-fns nomeadas (reusa as do core; nada de codigo do usuario)
CHECK_FNS = {"mod11-cpf": _cpf_check_fn, "mod11-cnpj": _cnpj_check_fn, "none": None}
_CHECK_LEN = {"mod11-cpf": 2, "mod11-cnpj": 2, "none": 0}


def parse_dsl(text: str) -> dict:
    """Parser flat `chave: valor` (# comentario; [a, b] lista de int; int; string)."""
    d: dict = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        key, sep, val = line.partition(":")
        if not sep:
            raise ValueError(f"linha DSL invalida (esperado 'chave: valor'): {raw!r}")
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            d[key] = [int(x) for x in val[1:-1].split(",") if x.strip()]
        elif val.lstrip("-").isdigit():
            d[key] = int(val)
        else:
            d[key] = val.strip("'\"")
    return d


def _tokens(template: str):
    """Tokeniza o template em runs de digito ('d', k) e literais ('l', char)."""
    toks, i = [], 0
    while i < len(template):
        if template[i] in "ND":
            j = i
            while j < len(template) and template[j] in "ND":
                j += 1
            toks.append(("d", j - i)); i = j
        else:
            toks.append(("l", template[i])); i += 1
    return toks


def _regex_from_tokens(toks) -> str:
    parts = ["^"]
    for kind, v in toks:
        parts.append(f"(\\d{{{v}}})" if kind == "d" else re.escape(v))
    parts.append("$")
    return "".join(parts)


def _make_formatter(toks):
    def fmt(digits):
        s = "".join(str(d) for d in digits)
        out, pos = [], 0
        for kind, v in toks:
            if kind == "d":
                out.append(s[pos:pos + v]); pos += v
            else:
                out.append(v)
        return "".join(out)
    return fmt


def compile_spec(dsl: dict):
    """DSL dict -> spec executavel (TemplatedChecked/PaddedSpec), validado por round-trip."""
    name = dsl.get("name")
    algo = dsl.get("check_algorithm", "none")
    if not name:
        raise ValueError("DSL sem 'name'")
    if algo not in CHECK_FNS:
        raise ValueError(f"check_algorithm desconhecido: {algo!r} (use {sorted(CHECK_FNS)})")

    if algo == "none":
        if "padding_slots" not in dsl or "separator" not in dsl:
            raise ValueError("check_algorithm: none requer 'padding_slots' + 'separator'")
        slots = tuple(dsl["padding_slots"]); sep = dsl["separator"]
        body = dsl.get("body_length")
        if body is not None and sum(slots) != body:
            raise ValueError(f"sum(padding_slots)={sum(slots)} != body_length={body}")
        regex = re.compile("^" + re.escape(sep).join(f"(\\d{{1,{w}}})" for w in slots) + "$")
        spec = TemplatedPaddedSpec(name, regex, slots, sep)
        _roundtrip_padded(spec, slots, sep)
        return spec

    # checked (com digito verificador)
    for k in ("template", "body_length", "check_length"):
        if k not in dsl:
            raise ValueError(f"check_algorithm {algo} requer '{k}'")
    template, body, check = dsl["template"], dsl["body_length"], dsl["check_length"]
    if check != _CHECK_LEN[algo]:
        raise ValueError(f"check_length={check} incoerente com {algo} (espera {_CHECK_LEN[algo]})")
    toks = _tokens(template)
    ndig = sum(v for kind, v in toks if kind == "d")
    if ndig != body + check:
        raise ValueError(f"template tem {ndig} digitos, mas body_length+check_length={body + check}")
    B = len(BASE94)
    enc_len = dsl.get("encoded_length") or math.ceil(body * math.log(10) / math.log(B))
    if B ** enc_len < 10 ** body:
        raise ValueError(f"encoded_length={enc_len} insuficiente (base{B}^{enc_len} < 10^{body})")
    spec = TemplatedCheckedSpec(
        name=name, regex=re.compile(_regex_from_tokens(toks)),
        body_length=body, check_length=check, check_fn=CHECK_FNS[algo],
        formatter=_make_formatter(toks), encoded_length=enc_len,
    )
    _roundtrip_checked(spec, body, CHECK_FNS[algo])
    return spec


def _roundtrip_checked(spec, body_length, check_fn, n=64):
    rng = random.Random(0)
    for _ in range(n):
        body = [rng.randint(0, 9) for _ in range(body_length)]
        value = spec.formatter(body + check_fn(body))
        enc, status = spec.encode_value(value)
        if status != "compressible":
            raise ValueError(f"round-trip: amostra {value!r} nao e' compressible ({status})")
        back = spec.decode_value(enc)
        if back != value:
            raise ValueError(f"round-trip FALHOU: {value!r} -> {enc!r} -> {back!r}")


def _roundtrip_padded(spec, slots, sep, n=64):
    rng = random.Random(0)
    for _ in range(n):
        value = sep.join(str(rng.randint(0, 10 ** w - 1)) for w in slots)  # canonico
        enc, _status = spec.encode_value(value)
        back = spec.decode_value(enc)
        if back != value:
            raise ValueError(f"round-trip FALHOU: {value!r} -> {enc!r} -> {back!r}")


def compile_file(path):
    return compile_spec(parse_dsl(Path(path).read_text(encoding="utf-8")))
