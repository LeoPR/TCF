"""Interface entre algoritmo de compressao (tokens) e formato textual (TCF).

O algoritmo em `online.py` produz uma lista de tokens
(TokLit, TokRefPref, TokRefSuf) por string. Uma `Syntax` define:

1. Como esses tokens viram texto serializado (encode)
2. Como esse texto vira de volta as linhas originais (decode)

Algoritmo e sintaxe sao **ortogonais**. Trocar a sintaxe nao
muda o algoritmo. Cada sintaxe e auto-contida: contem encoder +
decoder na mesma classe para garantir consistencia.

Contrato de roundtrip:

    syn.decode(syn.encode(linhas, unicas, tokens, header)) == linhas

Esta interface e propositadamente simples — para suportar
experimentos com sintaxes radicalmente diferentes (verbose,
compacta, binaria com textual, hibrida, etc.) sem que o algoritmo
precise saber qualquer coisa sobre o formato.
"""

from abc import ABC, abstractmethod

# Welding step 2 adaptation (2026-05-17): import path adaptado de
# `from online import Token` (dirty lab sibling) para package import.
# Logica permanece byte-exata.
from tcf.core.online import Token


class Syntax(ABC):
    """Contrato abstrato. Subclasses implementam encode + decode."""

    name: str = "abstract"  # cada subclass deve sobrescrever

    @abstractmethod
    def encode(self,
                linhas_originais: list[str],
                strings_unicas: list[str],
                tokens_por_string: list[list[Token]],
                header: str) -> str:
        """Converte input + tokens em texto TCF.

        Parametros:
            linhas_originais: lista de strings na ordem do CSV (com
                repeticoes preservadas para RLE).
            strings_unicas: lista de strings unicas na ordem de
                primeira aparicao (= ordem dos `tokens_por_string`).
            tokens_por_string: para cada string unica (na mesma
                ordem), a lista de tokens que a reconstroi.
            header: nome da coluna (caso a sintaxe queira usar).

        Retorna texto TCF completo (com newlines internos).
        """
        ...

    @abstractmethod
    def decode(self, tcf_text: str) -> list[str]:
        """Reconstroi a lista de linhas originais a partir do TCF.

        Deve garantir: decode(encode(...)) == linhas_originais.
        """
        ...
