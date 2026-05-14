"""Flags compositoriais do TCF v0.5.

Cada flag liga uma feature do encoder/decoder. Combinacoes de flags
formam o "nivel" do arquivo (ex: SRDMA = sort + RLE + dict + auto-discrim
+ alfabeto). Default produção: SRDMA.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Flags:
    """Conjunto de flags ativas no arquivo TCF v0.5.

    Convencao da letra-flag (ver gramatica formal):
      S — sort applied (chaves declaradas em # sort:)
      R — RLE habilitado
      D — dict implicito habilitado (1a aparicao = declaracao)
      M — auto-discriminator (bare em nao-num, marked em num puro)
      A — adaptive alphabet for indices
      delta (δ) — delta encoding por coluna (via # ext:)
      P — prefix elision por coluna (via # ext:)
      Lp (L') — line-RLE layout (alternativo)
      K — count-recycling (streaming)
      I — inline mode (per-column via # layout:)
      Pi (Π) — packed-absolute (per-column via # ext:)
    """
    S: bool = False
    R: bool = False
    D: bool = False
    M: bool = False
    A: bool = False
    delta: bool = False
    P: bool = False
    Lp: bool = False
    K: bool = False
    I: bool = False
    Pi: bool = False

    @classmethod
    def from_string(cls, s: str) -> "Flags":
        """Parseia string de flags como 'SRDMA' ou 'SRDMA+delta+I'.

        Letras unicas mapeadas direto. Para flags multi-char (delta, Lp, Pi),
        aceita tambem variantes: 'd' lowercase = delta, 'L'' = Lp, 'p' lower = Pi.
        """
        out = cls()
        # Normaliza: aceita mistura de letras-flag e tokens separados por '+' ou ' '
        normalized = s.replace("+", " ").replace(",", " ").strip()
        # Primeiro processa letras-flag concatenadas (SRDMA)
        # Detecta tokens multi-char primeiro
        tokens = []
        i = 0
        while i < len(normalized):
            c = normalized[i]
            if c == " ":
                i += 1
                continue
            if c == "L" and i + 1 < len(normalized) and normalized[i + 1] == "'":
                tokens.append("Lp")
                i += 2
            elif c.lower() == "d" and normalized[i:i+5].lower() == "delta":
                tokens.append("delta")
                i += 5
            elif c.lower() == "p" and normalized[i:i+2].lower() == "pi":
                tokens.append("Pi")
                i += 2
            elif c in "SRDMAPKI":
                tokens.append(c)
                i += 1
            else:
                # ignora desconhecido (Greek δ, Π, etc)
                if c == "δ":
                    tokens.append("delta")
                elif c == "Π":
                    tokens.append("Pi")
                i += 1
        for t in tokens:
            if hasattr(out, t):
                setattr(out, t, True)
        return out

    def to_string(self) -> str:
        """Serializa como letras concatenadas: 'SRDMA' (multi-char com sufixo)."""
        out = []
        for f in ["S", "R", "D", "M", "A", "P", "K", "I"]:
            if getattr(self, f):
                out.append(f)
        if self.Lp:
            out.append("L'")
        if self.delta:
            out.append("δ")
        if self.Pi:
            out.append("Π")
        return "".join(out)


# Default produção da v0.5 (SRDMA, conforme PROGRESSO-formato-v05)
DEFAULT_FLAGS = Flags(S=True, R=True, D=True, M=True, A=True)
