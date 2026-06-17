"""natures_compiler — compila definicoes textuais (.dsl) -> natures executaveis (gadget).

    from natures_compiler import compile_file, compile_spec, parse_dsl
    spec = compile_file("examples/cpf.dsl")          # valida round-trip lossless
    from tcf import encode, decode
    decode(encode(cpfs, nature=spec), nature=spec)   # usa como qualquer nature

Nao toca src/tcf (importa os blocos do core e instancia). Ver compiler.py / README.md.
"""
from .compiler import compile_file, compile_spec, parse_dsl, CHECK_FNS

__all__ = ["compile_file", "compile_spec", "parse_dsl", "CHECK_FNS"]
