"""TCF — string compression algorithm (v0.6).

API publica:

    from tcf import encode, decode

    tcf_text = encode(["abc", "abcd", "abcde"])
    values = decode(tcf_text)
    assert values == ["abc", "abcd", "abcde"]

Componentes (welded de `experiments/lab/dirty/`, 2026-05-17):
- `tcf.core.online`: alg16 / TCF-CORE / OAS — tokenizacao online
  incremental via LCP/LCS. Byte-exato de M0/online.py.
- `tcf.core.syntax_base`: interface Syntax (encode + decode).
- `tcf.composicional.syntax`: M8.A — detector unificado + emit
  composicional (`~` cria ref, `,` concat efemero). Logica byte-exata
  de M8.A canonico (apenas imports adaptados pra package layout).
- `tcf.encoder` / `tcf.decoder`: API publica de alto nivel.

Validado por:
- M11 (alg16 em src/) — RT 9/9 OK, bytes byte-identicos a M9/M10.
- M12 (M8.A em src/) — RT 9/9 OK, bytes byte-identicos a M11.
- M13 (API publica encode/decode) — RT 9/9 OK, bytes byte-identicos
  a M12.

Status v0.6: protótipo welded do dirty lab. Migracao limpa de
ciclo v0.5 (`old/tcf/`) em curso. Multi-column / multi-dataset
sera adicionado em fase posterior.
"""

from tcf.encoder import encode
from tcf.decoder import decode

__all__ = ["encode", "decode"]
