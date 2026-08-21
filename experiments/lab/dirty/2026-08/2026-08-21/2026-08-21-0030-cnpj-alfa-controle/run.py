"""CNPJ alfanumerico — o sintetico de CONTROLE que decide o desenho do conserto.

Pedido do owner (2026-08-21): *"no momento precisamos de um dataset sintetico de
controle so' pra ver os comportamentos pra poder tratar isso agora. isso muda um
pouco a parte da conversao da base, tem que ver ate' onde as letras atendem e como
isso afeta os calculos, pelo que vi o campo de letra sera' tratado como numero de
qualquer forma nao?"*

AS PERGUNTAS (uma coisa de cada vez)
------------------------------------
  A  ATE' ONDE AS LETRAS ATENDEM — o mapeamento legal (ASCII-48), o GAP que ele
     carrega, os extremos do dominio, e a resposta a "letra e' numero?".
  B  A CONVERSAO DA BASE — quantos chars base-80 o corpo passa a exigir, e por que
     o mapeamento DENSO (0-35) ganha 1 char do mapeamento legal usado como base.
  C  A MAQUINA REAL aceita um spec alfanumerico SEM tocar src/tcf? (subclasse no
     lab + porta `nature=` / out-of-band do decode). Onde ela quebraria sem isso.
  D  A TRANSICAO — base numerica REAL (Shaper) recebendo k valores alfanumericos:
     o comportamento de cada mecanismo (split · nature · posicional) em funcao
     de k. E' o comportamento que decide o tratamento, nao o volume.

`src/tcf` INTOCADO. Evidencia obrigatoria + portao anti-orfao. RT em todo wire.


LAB HISTORICO — NAO RODA MAIS (2026-08-21). Mede o comportamento de transição com DOIS specs (`cnpj` + `cnpja`) e um chooser,
superado pelo ADR-0044 no mesmo dia. Quebra porque assert de `encoded_length` que mudou de 7 para 10.
E' registro do caminho; para executar, `git checkout a08abb2b`.
"""

from __future__ import annotations

import json
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                          # noqa: E402
from tcf.natures.templated_checked import (                             # noqa: E402
    BASE94, MARKER_LITERAL, SPEC_CNPJ, TemplatedCheckedSpec, _cnpj_check_fn,
)

N = 2000
DENSO = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"          # indice 0-35 (base da GRAVACAO)
_arquivos: set[Path] = set()


def grava(pasta: Path, nome: str, texto: str) -> None:
    p = pasta / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())


def dv_legal(corpo: str) -> str:
    """O DV da IN 2.229/2024: valores ASCII-48 nos MESMOS pesos de sempre."""
    return "".join(str(d) for d in _cnpj_check_fn([ord(c) - 48 for c in corpo]))


def mascara14(s: str) -> str:
    assert len(s) == 14
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


# ═════════════════════════════════════════════════════════════════════════
# O SPEC ALFANUMERICO — subclasse DE LAB (nada em src/tcf muda)
# ═════════════════════════════════════════════════════════════════════════
_CNPJ_ALFA_RE = re.compile(r"^([0-9A-Z]{2})\.([0-9A-Z]{3})\.([0-9A-Z]{3})/([0-9A-Z]{4})-(\d{2})$")


def _formatter_alfa(vals: list[int]) -> str:
    """list[int] em valores LEGAIS (ASCII-48) -> string formatada.
    A inversa do mapeamento legal e' `chr(v+48)` — '0'<-0 ... '9'<-9, 'A'<-17..."""
    s = "".join(chr(v + 48) for v in vals[:12]) + "".join(str(d) for d in vals[12:])
    return mascara14(s)


@dataclass(frozen=True)
class AlfaTemplatedCheckedSpec(TemplatedCheckedSpec):
    """Generaliza os 3 metodos que hoje assumem `\\d`. DOIS mapeamentos convivem:
      - LEGAL (ASCII-48, com gap 10-16): alimenta o check_fn — e' a lei.
      - DENSO (indice 0-35): alimenta a conversao de base — e' a gravacao.
    O check_fn e os pesos sao OS MESMOS do spec numerico."""

    def classify_value(self, v: str) -> str:
        if not v:
            return "empty_value"
        tot = self.body_length + self.check_length
        if len(v) == tot and all(c in DENSO for c in v):
            return "format_unmasked"
        if not self.regex.match(v):
            return "format_mismatch" if len(v) > 5 else "length_wrong"
        chars = [c for c in v if c in DENSO]
        if len(chars) != tot:
            return "length_wrong"
        body_vals = [ord(c) - 48 for c in chars[: self.body_length]]      # LEGAL
        if self.check_fn(body_vals) != [int(c) for c in chars[self.body_length:]]:
            return "check_invalid"
        return "compressible"

    def encode_value(self, v: str) -> tuple[str, str]:
        status = self.classify_value(v)
        if status != "compressible":
            return MARKER_LITERAL + v, status
        chars = [c for c in v if c in DENSO]
        n = 0
        for c in chars[: self.body_length]:
            n = n * 36 + DENSO.index(c)                                   # DENSO
        out = []
        for _ in range(self.encoded_length):
            out.append(BASE94[n % len(BASE94)])
            n //= len(BASE94)
        return "".join(reversed(out)), status

    def decode_value(self, payload: str) -> str:
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        if len(payload) == self.encoded_length and all(c in BASE94 for c in payload):
            n = 0
            for c in payload:
                n = n * len(BASE94) + BASE94.index(c)
            idx = []
            for _ in range(self.body_length):
                idx.append(n % 36)
                n //= 36
            corpo = "".join(DENSO[i] for i in reversed(idx))
            vals = [ord(c) - 48 for c in corpo]                           # LEGAL
            return self.formatter(vals + self.check_fn(vals))
        return payload


SPEC_CNPJ_ALFA = AlfaTemplatedCheckedSpec(
    name="cnpj-alfa",
    regex=_CNPJ_ALFA_RE,
    body_length=12,
    check_length=2,
    check_fn=_cnpj_check_fn,          # OS MESMOS pesos — verificado no lab 2350
    formatter=_formatter_alfa,
    encoded_length=10,                # 36^12 = 4,74e18 <= 80^10 = 1,07e19
    wire_id="cnpja",                  # gramatica ADR-0041 ok; NAO esta' no registry core
)


# ═════════════════════════════════════════════════════════════════════════
def parte_a() -> dict:
    print("=" * 100)
    print("A) ATE' ONDE AS LETRAS ATENDEM — o mapeamento legal e seus limites")
    print("=" * 100)
    print("  mapeamento LEGAL (IN 2.229/2024): valor = ASCII(c) - 48")
    print("    '0'..'9' -> 0..9   ·   GAP 10..16 = ':' ';' '<' '=' '>' '?' '@' (NAO usados)")
    print("    'A'..'Z' -> 17..42")
    print("  => SIM: no calculo do DV a letra E' tratada como numero — nos MESMOS pesos")
    print("     e no MESMO modulo 11 de sempre. Digito converte pra ele mesmo, entao a")
    print("     regra nova e' IDENTICA a antiga no dominio numerico (retrocompat estrutural).")

    extremos = ["000000000000", "999999999999", "A00000000000", "ZZZZZZZZZZZZ",
                "12ABC34501DE"]
    print("\n  extremos do dominio (DV sempre 2 digitos decimais, por construcao do mod 11):")
    reg = []
    for corpo in extremos:
        d = dv_legal(corpo)
        soma1 = sum((ord(c) - 48) * w for c, w in zip(corpo, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
        print(f"    {corpo}  ->  DV {d}   (soma1={soma1})")
        assert len(d) == 2 and d.isdigit()
        reg.append({"corpo": corpo, "dv": d, "soma1": soma1})
    assert dv_legal("12ABC34501DE") == "35", "exemplo publicado nao fecha"
    print("    teto da soma: corpo 'Z'*12 -> soma1=2436 (finita, sem overflow possivel)")
    print("\n  EMISSAO x VALIDACAO (pesquisa): a IN define o FORMATO como [0-9A-Z]; a")
    print("  estrategia de EMISSAO divulgada pelo Serpro tende a consoantes (ha' fontes")
    print("  secundarias citando exclusao de I,O,U,Q,F — nao confirmado na IN). O spec")
    print("  valida o FORMATO ([0-9A-Z]); emissao mais restrita so' encolhe o subespaco")
    print("  ocupado — nunca invalida um valor que a regra do DV aceita.")
    return {"mapeamento": "ASCII-48", "gap": "10-16 (':'..'@')", "extremos": reg}


def parte_b() -> dict:
    print("\n" + "=" * 100)
    print("B) A CONVERSAO DA BASE — o que muda na gravacao")
    print("=" * 100)
    linhas = [
        ("numerico (hoje)", 10 ** 12, SPEC_CNPJ.encoded_length),
        ("alfanumerico, base DENSA 0-35", 36 ** 12, 10),
        ("alfanumerico, ASCII-48 como base (43)", 43 ** 12, 11),
    ]
    print(f"  {'dominio do corpo':<38} {'tamanho':>12} {'chars base-80':>14}")
    for rot, dom, k in linhas:
        assert 80 ** k >= dom > 80 ** (k - 1), f"{rot}: encoded_length errado"
        print(f"  {rot:<38} {dom:>12.3e} {k:>14}")
    print("  => DOIS mapeamentos convivem: o LEGAL (ASCII-48) so' pro DV; o DENSO (0-35)")
    print("     so' pra base. Usar o legal como base desperdicaria o GAP: 43^12 > 80^10")
    print("     e o corpo pagaria 11 chars em vez de 10. 1 char/valor = ~5,5% do valor.")
    print(f"  alfabeto de gravacao: BASE94 tem {len(BASE94)} simbolos utilizaveis (=80).")
    return {"encoded_length": {"numerico": SPEC_CNPJ.encoded_length,
                               "denso36": 10, "ascii48_como_base": 11}}


def parte_c(reais: list[str]) -> dict:
    print("\n" + "=" * 100)
    print("C) A MAQUINA REAL aceita o spec alfanumerico? (subclasse de lab, src intocado)")
    print("=" * 100)
    print("  onde a maquina de hoje assume digito (o mapa do weld):")
    print("    classify_value  ->  v.isdigit() / c.isdigit() / int(d)")
    print("    encode_value    ->  int(digits_str[:body])           (base 10 implicita)")
    print("    decode_value    ->  str(n).zfill(body) + formatter(list[int] 0-9)")
    print("  a subclasse re-generaliza EXATAMENTE esses 3 metodos; check_fn/pesos intactos.")

    rng = random.Random(2026)

    def alfa(n: int) -> list[str]:
        corpo = lambda: "".join(rng.choice(DENSO) for _ in range(12))     # noqa: E731
        return [mascara14(c + dv_legal(c)) for c in (corpo() for _ in range(n))]

    col_alfa = alfa(N)
    col_mista = reais[: N // 2] + col_alfa[: N - N // 2]

    resultados = []
    for cid, col, spec in (("c1-alfa-puro", col_alfa, SPEC_CNPJ_ALFA),
                           ("c2-misto-50-50", col_mista, SPEC_CNPJ_ALFA),
                           ("c3-numerico-spec-alfa", reais, SPEC_CNPJ_ALFA),
                           ("c4-numerico-spec-hoje", reais, SPEC_CNPJ)):
        w = encode(col, nature=spec)
        rt = decode(w, nature=spec)
        assert rt == col, f"{cid}: RT quebrou"
        b = len(w.encode("utf-8"))
        raw = len("\n".join(col).encode("utf-8"))
        header = w.split("\n", 1)[0]
        grava(IN, f"{cid}.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
        grava(OUT, f"{cid}.tcf", w)
        grava(OUT, f"{cid}.roundtrip.json", json.dumps(rt[:40], ensure_ascii=False, indent=1))
        print(f"  {cid:<24} {b:>8,} B  vs raw {(b/raw-1)*100:>+7.2f}%   header={header!r}")
        resultados.append({"caso": cid, "spec": spec.name, "bytes": b, "raw": raw,
                           "vs_raw_pct": round((b / raw - 1) * 100, 2), "header": header,
                           "rt": True})

    # o contrato: sem o spec out-of-band, o decode falha ALTO (id fora do registry core)
    w1 = (OUT / "c1-alfa-puro.tcf").read_text(encoding="utf-8")
    try:
        decode(w1)
        raise AssertionError("decode sem spec deveria falhar alto")
    except ValueError as e:
        msg = str(e)
    print(f"\n  fail-loud sem o spec (contrato H-NAT-MARK-01 core-only):")
    print(f"    ValueError: {msg[:96]}...")
    assert "cnpja" in msg
    grava(OUT, "c5-fail-loud-sem-spec.txt", msg)

    d = {"casos": resultados, "fail_loud": msg}
    c3 = next(x for x in resultados if x["caso"] == "c3-numerico-spec-alfa")
    c4 = next(x for x in resultados if x["caso"] == "c4-numerico-spec-hoje")
    print(f"\n  COEXISTENCIA: a MESMA coluna numerica custa {c4['bytes']:,} B no spec de hoje")
    print(f"  (7 chars) e {c3['bytes']:,} B no spec alfa (10 chars) = "
          f"{(c3['bytes']/c4['bytes']-1)*100:+.1f}%. Um id UNICO sempre-alfa taxaria todo")
    print("  o legado; DOIS wire_ids (`cnpj` 7 · `cnpja` 10) deixam o FLOOR escolher.")
    return d


def parte_d(reais: list[str]) -> dict:
    print("\n" + "=" * 100)
    print("D) A TRANSICAO — k valores alfanumericos numa coluna real de 2000")
    print("=" * 100)
    rng = random.Random(31)

    def um_alfa() -> str:
        corpo = "".join(rng.choice(DENSO) for _ in range(12))
        # garante >=1 LETRA (senao seria um numerico legitimo)
        if corpo.isdigit():
            corpo = "A" + corpo[1:]
        return mascara14(corpo + dv_legal(corpo))

    tabela = []
    print(f"  {'k':>5}  {'.8M (split/…)':>16} {'mec':<6} {'nature-alfa':>13} "
          f"{'posicional':>12}")
    for k in (0, 1, 3, 20, 200, 1000, 2000):
        col = list(reais)
        posicoes = rng.sample(range(N), k)
        for i in posicoes:
            col[i] = um_alfa()

        # (1) a rota .8M de hoje — onde vive o split
        w1 = encode({"cnpj": col})
        assert decode(w1)["cnpj"] == col
        b1 = len(w1.encode("utf-8"))
        disc = w1[7] if len(w1) > 7 else "?"
        mec = {"!": "raw", "@": "dict", "%": "split"}.get(disc, "core")

        # (2) a nature alfanumerica (per-value, opt-in)
        w2 = encode(col, nature=SPEC_CNPJ_ALFA)
        assert decode(w2, nature=SPEC_CNPJ_ALFA) == col
        b2 = len(w2.encode("utf-8"))

        # (3) a decomposicao posicional (18 colunas; o "grupo" sem marcador ainda)
        pos = {f"p{i:02d}": [s[i] for s in col] for i in range(18)}
        w3 = encode(pos)
        v3 = decode(w3)
        assert ["".join(v3[f"p{i:02d}"][j] for i in range(18)) for j in range(N)] == col
        b3 = len(w3.encode("utf-8"))

        grava(IN, f"d-k{k:04d}.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
        for rot, w in (("m8", w1), ("nat", w2), ("pos", w3)):
            grava(OUT, f"d-k{k:04d}-{rot}.tcf", w)
        grava(OUT, f"d-k{k:04d}-m8.roundtrip.json",
              json.dumps(decode(w1)["cnpj"][:40], ensure_ascii=False, indent=1))
        grava(OUT, f"d-k{k:04d}-nat.roundtrip.json",
              json.dumps(decode(w2, nature=SPEC_CNPJ_ALFA)[:40], ensure_ascii=False, indent=1))
        grava(OUT, f"d-k{k:04d}-pos.roundtrip.json",
              json.dumps(["".join(v3[f"p{i:02d}"][j] for i in range(18))
                          for j in range(40)], ensure_ascii=False, indent=1))

        print(f"  {k:>5}  {b1:>14,} B  {mec:<6} {b2:>11,} B {b3:>10,} B")
        tabela.append({"k": k, "m8_bytes": b1, "m8_mecanismo": mec,
                       "nature_bytes": b2, "posicional_bytes": b3, "rt": True})

    raw = len("\n".join(reais).encode("utf-8"))
    print(f"\n  (raw da coluna ~{raw:,} B; n={N})")
    m0, m1 = tabela[0], tabela[1]
    print(f"  LEITURA: o split morre em k={'1' if m1['m8_mecanismo'] != 'split' else '?'} — "
          f"de {m0['m8_bytes']:,} B ({m0['m8_mecanismo']}) para {m1['m8_bytes']:,} B "
          f"({m1['m8_mecanismo']}) com UM valor novo.")
    print("  A nature e' per-VALUE: quem nao casa vira literal e o resto continua ganhando —")
    print("  a curva fica quase plana em k. O posicional degrada suave (por posicao).")
    return {"n": N, "raw": raw, "tabela": tabela}


def main() -> int:
    from shaper import Shaper, ShapeRequest
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj", volume=N, seed=11,
                                    stratify_by="uf"))
    rows = r.tables[list(r.tables)[0]]
    reais = [str(x["cnpj"]) for x in rows][:N]
    assert all(len(s) == 18 for s in reais), "fonte ja' vem formatada (licao do lab 2350)"

    res = {"A": parte_a(), "B": parte_b(), "C": parte_c(reais), "D": parte_d(reais)}

    (AQUI / "resultado.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    achados = {p.resolve() for pasta in (IN, OUT) for p in pasta.rglob("*") if p.is_file()}
    assert not (_arquivos - achados), f"EVIDENCIA FALTANDO: {_arquivos - achados}"
    assert not (achados - _arquivos), f"EVIDENCIA ORFA: {achados - _arquivos}"
    print(f"\n-> {len(achados)} arquivos (inputs+outputs), portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
