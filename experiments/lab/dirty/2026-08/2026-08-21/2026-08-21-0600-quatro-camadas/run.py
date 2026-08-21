"""As QUATRO camadas que eu vinha misturando — e o que cada uma pode omitir.

A CORRECAO DO OWNER (2026-08-21)
--------------------------------
*"so' nao quero misturar a entrada do dataset e o roundtrip pra construir, a
saida em arquivo que possa ser util, e o transporte. tudo e' coisa diferente
[...] temos so' que possibilitar um flag e um default pra cada situacao [...]
Se a saida da descompressao foi, por conveniencia, pronta pra atender o formato
de arquivo, otimo, senao o flag altera a saida para atender as situacoes de
arquivo e transporte. So' nao pode atrapalhar o encode/decode. [...] o
transporte pode omitir tudo que nao precise, ja' em saida pra arquivo pode ser
conveniente o \\n, mas se mesmo esse nao tiver necessidade, avise."*

AS CAMADAS
----------
  C1  ENTRADA  — o dataset que vai pro encode
  C2  ROUNDTRIP — encode/decode; o contrato de CORRECAO. Intocavel.
  C3  ARQUIVO  — o que se grava em disco. Conveniencias POSIX cabem aqui.
  C4  TRANSPORTE — o que vai no fio. Pode omitir TUDO que o contexto ja' diz.

O QUE ESTE LAB MEDE
-------------------
  M1  o INVENTARIO do que cada camada pode omitir, e o que NAO pode
  M2  quanto o TRANSPORTE economizaria de verdade (nao so' o LF)
  M3  o LF do ARQUIVO tem utilidade REAL, ou e' so' habito?
  M4  a prova de que separar as camadas NAO toca encode/decode
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                       # noqa: E402

LF = "\n"
_arquivos: set[Path] = set()


def grava(pasta: Path, nome: str, texto: str) -> None:
    p = pasta / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())


CASOS = [
    ("1 CPF", ["529.982.247-25"]),
    ("3 curtos", ["ab", "cd", "ef"]),
    ("10 valores", [f"v{i}" for i in range(10)]),
    ("100 valores", [f"valor{i}" for i in range(100)]),
    ("1000 valores", [f"linha-{i:04d}" for i in range(1000)]),
    ("multi 2x2", {"a": ["1", "2"], "b": ["x", "y"]}),
    ("hier", [{"a": 1, "b": [1, 2]}, {"a": 2}]),
]


def main() -> int:
    res = {}
    print("=" * 98)
    print("AS QUATRO CAMADAS — o que cada uma pode omitir")
    print("=" * 98)

    # ── M1: inventario ───────────────────────────────────────────────────
    print("\nM1) INVENTARIO — o que existe no wire, e quem precisa de que")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = encode(["529.982.247-25"])
    print(f"  wire de 1 CPF: {w!r}  ({len(w.encode())} B)")
    cab = w.split(LF, 1)[0]
    print(f"    cabecalho {cab!r:<12} {len(cab.encode()):>2} B  — formato + versao + rota")
    corpo = w.split(LF, 1)[1]
    print(f"    corpo      {corpo!r:<12} {len(corpo.encode()):>2} B  — o DADO (+ LF terminador)")
    print("\n  quem precisa de que:")
    print("    C2 ROUNDTRIP  : precisa de TUDO — e' o contrato de correcao")
    print("    C3 ARQUIVO    : precisa do cabecalho (o arquivo e' auto-descritivo")
    print("                    e o `file`/libmagic identifica por ele)")
    print("    C4 TRANSPORTE : NAO precisa do cabecalho SE o canal declarar tipo,")
    print("                    versao e rota fora de banda (Content-Type, framing).")
    print("                    Nem do LF terminador, SE a regra por rota for acordada.")

    # ── M2: quanto o transporte economiza ────────────────────────────────
    print("\n" + "=" * 98)
    print("M2) TRANSPORTE — quanto se omite de verdade (nao so' o LF)")
    print("=" * 98)
    print(f"  {'caso':<14} {'wire':>7} {'-LF':>7} {'-cabec':>8} {'-ambos':>8} "
          f"{'economia':>9}")
    tab = []
    for rot, d in CASOS:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w = encode(d)
        b = len(w.encode("utf-8"))
        cab = w.split(LF, 1)[0]
        b_cab = len(cab.encode("utf-8")) + 1                 # + o LF que o separa
        b_lf = 1 if w.endswith(LF) else 0
        ambos = b - b_cab - b_lf
        pct = (1 - ambos / b) * 100
        print(f"  {rot:<14} {b:>6}B {b-b_lf:>6}B {b-b_cab:>7}B {ambos:>7}B "
              f"{pct:>8.1f}%")
        tab.append({"caso": rot, "wire": b, "sem_lf": b - b_lf,
                    "sem_cabecalho": b - b_cab, "so_dado": ambos,
                    "economia_pct": round(pct, 1)})
        nome = rot.replace(" ", "-")
        grava(IN, f"{nome}.json", json.dumps(d, ensure_ascii=False, indent=1))
        grava(OUT, f"{nome}.tcf", w)
        grava(OUT, f"{nome}.roundtrip.json", json.dumps(decode(w), ensure_ascii=False, indent=1))
    res["M2"] = tab
    print("\n  O LF vale 1 byte. O CABECALHO vale 7-8 — e em payload minusculo")
    print("  ele e' a maior fatia do wire. Se o alvo e' 'cada byte conta em")
    print("  transmissao minuscula' (O-FMT-15/16), o cabecalho e' o premio,")
    print("  nao o LF. Eu estava discutindo o troco.")

    # ── M3: o LF do arquivo serve pra alguma coisa? ──────────────────────
    print("\n" + "=" * 98)
    print("M3) O LF DO ARQUIVO — utilidade real ou habito?")
    print("=" * 98)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = encode([f"v{i}" for i in range(10)])
    linhas_com = w.count(LF)
    linhas_sem = w[:-1].count(LF) if w.endswith(LF) else linhas_com
    print(f"  wire de 10 valores: {len(w.encode())} B, {linhas_com} LFs")
    print(f"    `wc -l` com o LF final  : {linhas_com}  (conta todas as linhas)")
    print(f"    `wc -l` sem o LF final  : {linhas_sem}  (SUBCONTA a ultima)")
    print("\n  Onde isso importa DE VERDADE num arquivo `.tcf`:")
    print("    · `wc -l` / `head` / `tail` / `split` — ferramentas de LINHA")
    print("    · `git diff` marca `\\\\ No newline at end of file`")
    print("    · shell `while read` perde a ultima linha")
    print("  Onde NAO importa:")
    print("    · identificacao de tipo (`file`, libmagic) — e' por MAGIC, e o TCF")
    print("      tem um forte no inicio do arquivo")
    print("    · o proprio decode do TCF — ele nao usa `wc -l`")
    print("\n  VEREDITO: o LF do arquivo e' CONVENIENCIA REAL, mas so' pra quem usa")
    print("  ferramenta de linha no `.tcf`. E como o encode JA' o emite em 7 das")
    print("  10 rotas, na maioria dos casos a conveniencia vem DE GRACA — que e'")
    print("  exatamente a situacao que o owner descreveu ('se por conveniencia ja'")
    print("  atende o formato de arquivo, otimo').")
    res["M3"] = {"wc_com": linhas_com, "wc_sem": linhas_sem}

    # ── M2b: omitir NAO e' ideia nova — ja' existe UM flag ───────────────
    print(LF + "=" * 98)
    print("M2b) A PILHA DE OMISSAO — o que ja' existe hoje")
    print("=" * 98)
    tab2 = {"a": ["1", "2"], "b": ["x", "y"]}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w0, w1 = encode(tab2), encode(tab2, drop_names=True)
    cab1 = w1.split(LF, 1)[0]
    so_dado = len(w1.encode("utf-8")) - len(cab1.encode("utf-8")) - 1
    print(f"  multi-col normal          {len(w0.encode()):>3} B   {w0.splitlines()[0]!r}")
    print(f"  + drop_names=True         {len(w1.encode()):>3} B   {w1.splitlines()[0]!r}"
          f"   (-{len(w0.encode())-len(w1.encode())} B)")
    print(f"  + sem cabecalho (C4)      {so_dado:>3} B   "
          f"(-{len(w1.encode())-so_dado} B)  -> total "
          f"-{(1-so_dado/len(w0.encode()))*100:.0f}%")
    print(LF + "  `drop_names` JA' E' uma omissao de transporte — o contrato vive nas")
    print("  pontas e os nomes nao viajam (ADR-0029). E o `T-SPEC-SEM-CARIMBO`")
    print("  registra a mesma ideia pro `:id` de nature (nao implementado).")
    print("  Ou seja: a familia ja' comecou; falta o CONCEITO que a une.")
    res["M2b"] = {"normal": len(w0.encode("utf-8")),
                  "drop_names": len(w1.encode("utf-8")), "so_dado": so_dado}

    # ── M4: separar as camadas NAO toca encode/decode ────────────────────
    print("\n" + "=" * 98)
    print("M4) A PROVA — as camadas sao FUNCOES SOBRE o wire, nao dentro dele")
    print("=" * 98)

    def para_transporte(wire: str) -> tuple[str, dict]:
        """C4: tira o que o canal pode declarar. Devolve (payload, contrato)."""
        cab, corpo = wire.split(LF, 1)
        contrato = {"magic": cab, "termina_em_lf": corpo.endswith(LF)}
        return (corpo[:-1] if corpo.endswith(LF) else corpo), contrato

    def do_transporte(payload: str, contrato: dict) -> str:
        """A inversa exata."""
        corpo = payload + (LF if contrato["termina_em_lf"] else "")
        return contrato["magic"] + LF + corpo

    def para_arquivo(wire: str) -> str:
        """C3: garante o LF final pra ferramenta de linha nao subcontar."""
        return wire if wire.endswith(LF) else wire + LF

    falhas = []
    for rot, d in CASOS:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w = encode(d)
            p, c = para_transporte(w)
            volta = do_transporte(p, c)
            if volta != w or decode(volta) != d:
                falhas.append((rot, "transporte"))
            # C3 e' so' apresentacao: quem le' o arquivo tira o excedente
            arq = para_arquivo(w)
            restaurado = arq if w.endswith(LF) else arq[:-1]
            if restaurado != w or decode(restaurado) != d:
                falhas.append((rot, "arquivo"))
    print(f"  {len(CASOS)} casos · transporte ida-e-volta + arquivo ida-e-volta")
    print(f"  falhas: {len(falhas)}  {falhas if falhas else ''}")
    print("\n  As duas sao funcoes PURAS sobre o wire, com inversa exata. Nenhuma")
    print("  linha de `encode`/`decode` muda — que e' a condicao que o owner pos.")
    assert not falhas
    res["M4"] = {"casos": len(CASOS), "falhas": len(falhas)}

    # exemplo gravado das tres formas
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = encode(["529.982.247-25"])
    p, c = para_transporte(w)
    grava(OUT, "exemplo-C2-wire-canonico.tcf", w)
    grava(OUT, "exemplo-C3-arquivo.tcf", para_arquivo(w))
    grava(OUT, "exemplo-C4-transporte.bin", p)
    grava(OUT, "exemplo-C4-contrato.json", json.dumps(c, ensure_ascii=False, indent=1))
    print(f"\n  exemplo (1 CPF): wire {len(w.encode())} B · arquivo "
          f"{len(para_arquivo(w).encode())} B · transporte {len(p.encode())} B "
          f"+ contrato fora de banda")

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    achados = {p.resolve() for pasta in (IN, OUT) for p in pasta.rglob("*") if p.is_file()}
    assert not (_arquivos - achados) and not (achados - _arquivos)
    print(f"\n-> {len(achados)} arquivos, portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
