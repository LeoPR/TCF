"""registry — F1.5: lookup de nature por NOME (gadget, zero src/tcf).

Mantem um dicionario nome -> spec. Semeado com os specs canonicos do core
(cpf/cnpj/ip) e populavel com specs compilados de `.dsl` (compile_file). O usuario
resolve o nome e passa o OBJETO pra API atual:

    from natures_compiler import registry
    from tcf import encode, decode
    spec = registry.get("cpf")
    decode(encode(cpfs, nature=spec), nature=spec)

A API publica de `tcf` fica INALTERADA (continua recebendo o objeto spec). O lookup
por nome e' conveniencia do gadget — nao toca src/tcf.
"""
from __future__ import annotations

from pathlib import Path

from tcf.natures import SPEC_CPF, SPEC_CNPJ, SPEC_IP

from .compiler import compile_file

_REGISTRY: dict[str, object] = {}


def register(name: str, spec, *, override: bool = False) -> None:
    if not override and name in _REGISTRY:
        raise ValueError(f"nature '{name}' ja' registrada (use override=True ou outro nome)")
    _REGISTRY[name] = spec


def get(name: str):
    if name not in _REGISTRY:
        raise KeyError(f"nature '{name}' nao registrada (tem: {sorted(_REGISTRY)})")
    return _REGISTRY[name]


def names() -> list[str]:
    return sorted(_REGISTRY)


def load_dir(path) -> list[str]:
    """Compila todos os .dsl de um diretorio e registra por nome (override). Retorna os nomes."""
    loaded = []
    for f in sorted(Path(path).glob("*.dsl")):
        spec = compile_file(f)
        register(spec.name, spec, override=True)
        loaded.append(spec.name)
    return loaded


# semeia com os specs canonicos welded do core (fonte da verdade pra cpf/cnpj/ip)
register("cpf", SPEC_CPF)
register("cnpj", SPEC_CNPJ)
register("ip", SPEC_IP)
