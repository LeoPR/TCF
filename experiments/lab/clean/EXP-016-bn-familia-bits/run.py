"""EXP-016 — família bN/bits: bateria sintética completa [probatório].

Consolida o estudo dirty da família bN (labs `2026-07-27/{1608,1647,2211,2231,2247}`,
`2026-08-06/{2104,2250}` e as auditorias de `2026-07-28`/`2026-07-31`) numa bateria
**declarativa e auto-verificável**: cada caso diz o que se espera ANTES de rodar, e o lab
falha quando não acontece.

    python run.py          regenera outputs/ e report.md; exit 0 só se tudo fechar

## As cinco provas por caso

    RT ESTRITO      valor + tipo + sinal + comprimento, contra os DADOS ORIGINAIS
    DETERMINISMO    encode duas vezes -> byte-idêntico
    NUNCA-PIOR      o wire com bN nunca é maior que o wire sem bN
    CORREÇÃO ≠ bN   o core sozinho também faz RT — o bN é opção de TAMANHO, não de correção
    O ARTEFATO      o .tcf em disco, lido em binário, é byte-idêntico ao wire medido

## O que este lab NÃO faz

Não mede ganho em dado real nem frequência dos regimes. As colunas que "perdem" ficam
listadas em `outputs/regimes-que-perdem.md` para o estudo de volume, que é outro trabalho.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from casos import CASOS  # noqa: E402

from tcf import decode, encode  # noqa: E402
from tcf.composicional.dominio_bn import DISCS, MAX_W, _largura, candidatos  # noqa: E402
from tcf.composicional.polaridade import polariza  # noqa: E402
from tcf.decoder import _decode_column, _separa_sufixo_polaridade  # noqa: E402
from tcf.encoder import _encode_column, _tipo_single_col  # noqa: E402

for d in ("inputs", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)


PIPE_CH = chr(124)
BS_CH = chr(92)


def _escreve(p, texto: str) -> None:
    """Grava com `newline=""` — o `\\n` fica `\\n`, mesmo no Windows.

    Sem isso o modo texto do Python traduz `\\n` -> CRLF, e o `.tcf` em disco deixa de ser
    o wire: `#TCF.8B2c8\\r\\n…`. Num lab cuja evidência é byte-a-byte, isso não é detalhe de
    plataforma — é o artefato mentindo sobre o que foi medido.
    """
    p.write_text(texto, encoding="utf-8", newline="")


def _wj(p, obj):
    _escreve(p, json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n")


def rt_estrito(obtido, esperado) -> tuple[bool, str]:
    """Valor + tipo + sinal + comprimento. Devolve `(ok, motivo)`."""
    if len(obtido) != len(esperado):
        return False, f"comprimento {len(obtido)} != {len(esperado)}"
    for i, (a, b) in enumerate(zip(obtido, esperado)):
        if type(a) is not type(b):
            return False, f"[{i}] tipo {type(a).__name__} != {type(b).__name__}"
        if isinstance(a, float) and math.isnan(a) and math.isnan(b):
            continue
        if a != b:
            return False, f"[{i}] valor {a!r} != {b!r}"
        if isinstance(a, float) and a == 0 and math.copysign(1, a) != math.copysign(1, b):
            return False, f"[{i}] sinal do zero"
    return True, ""


def wire_sem_bn(valores) -> str | None:
    """O wire que o encoder produziria SEM o candidato bN — a base do nunca-pior.

    Para a rota flat é `#TCF.8<sufixo-polaridade>\\n<corpo>`, que é exatamente o que o
    `encoder` monta antes de somar os candidatos bN. Para as outras rotas devolve `None`
    (o bN não entra nelas hoje).
    """
    if not isinstance(valores, list) or not valores:
        return None
    if not all(v is None or isinstance(v, str) for v in valores):
        return None
    corpo = _encode_column(valores, header="val")
    sufixo, corpo = polariza(corpo)
    return "#TCF.8" + sufixo + "\n" + corpo


def _normaliza_set(msg: str) -> str:
    """Ordena o conteúdo de `{...}` na mensagem de erro — ACHADO deste lab.

    `HierarchicalError` interpola um `set` cru (`tipos escalares MISTOS {'b', 'n'}`), e o
    repr de `set` de strings varia com o `PYTHONHASHSEED`. A mensagem é a mesma; a ORDEM
    não. Sem normalizar, o próprio lab deixa de ser reproduzível byte-a-byte de uma rodada
    pra outra — o que quebraria a auditoria por diff.

    Isto é remendo do LAB, não correção: quem tem de ordenar é a mensagem em `src/tcf`
    (ticket `T-ERRO-SET-ORDEM`). Enquanto não for, o lab normaliza aqui.
    """
    return re.sub(r"\{([^{}]*)\}",
                  lambda m: "{" + ", ".join(sorted(p.strip() for p in m.group(1).split(",")))
                            + "}",
                  msg)


def _esc_md(t: str) -> str:
    """Escapa `|` para nao quebrar a coluna da tabela markdown."""
    return t.replace(PIPE_CH, BS_CH + PIPE_CH)


def lacuna_tipada(vals) -> "tuple[int, bool] | None":
    """Quanto o bN pouparia na rota TIPADA, se ela o aceitasse (ticket `T-BN-TIPADO`).

    Hoje o candidato bN só entra na rota flat de string; a rota tipada (`#TCF.8n`/`#TCF.8b`)
    não o consulta. Para medir a lacuna sem inventar número: pega as **grafias canônicas**
    que o tipado já emite (`render` do `_tipo_single_col`), constrói o wire bN REAL sobre
    elas, **confere o RT** desse wire, e soma **1 byte** — o char de tag de tipo que a forma
    tipada acrescenta (índice 6; o modo denso mora no 7, ADR-0029).

    Devolve `(bytes_estimados, rt_ok)` ou `None` se a coluna não se qualifica. O número é
    uma **estimativa ancorada num wire que funciona**, não um wire válido hoje.
    """
    t = _tipo_single_col(vals)
    if t is None:
        return None
    _tag, render = t
    grafias = [None if v is None else render(v) for v in vals]
    cands = candidatos(grafias, _encode_column, _decode_column)
    if not cands:
        return None
    melhor = min(cands, key=lambda w: len(w.encode()))
    try:
        rt_ok = rt_estrito(decode(melhor), grafias)[0]
    except Exception:
        rt_ok = False
    return len(melhor.encode()) + 1, rt_ok


def rota(wire: str) -> str:
    """Nome curto da rota, classificado como o DECODER classifica — não por regex própria.

    Usa `_separa_sufixo_polaridade` do decoder para tirar o sufixo de polaridade antes de
    olhar o discriminador; senão `#TCF.8!!` (polaridade `L`, ADR-0035) seria lido como um
    discriminador `!` inexistente. O sufixo entra no nome da rota como `+pol`, porque ele
    é informação real do caso — a camada de borda ativou.
    """
    resto = wire.split("\n", 1)[0][6:]
    tag, sufixo = _separa_sufixo_polaridade(resto)
    # `_separa` devolve `("", "")` quando NAO ha' sufixo — nesse caso o decoder olha o
    # `resto` cru. Reproduzir isso, e nao so' o `tag`, e' o que torna a rota fiel.
    corpo_tag = tag if sufixo else resto
    d = corpo_tag[:1]
    pol = "+pol" if sufixo else ""
    if d in DISCS:
        return f"bN-{d}{pol}"
    if d == "":                              # `#TCF.8` puro — version-stamp, corpo do core
        return f"core{pol}"
    if d == "b" and corpo_tag[1:2] == "B":
        return f"lazy-bB{pol}"
    if d in ("b", "n", "s"):
        return f"tipado-{d}{pol}"
    return f"outro-{d!r}{pol}"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas, perdem, lacunas = [], [], [], []
    # varre a tabela de larguras uma faixa alem do teto, pra a linha da RECUSA aparecer
    MAX_K = 2 ** (MAX_W + 1)

    for c in CASOS:
        nome, vals = c["nome"], c["valores"]
        _wj(RAIZ / "inputs" / f"{nome}.json",
            {"caso": nome, "familia": c["familia"], "porque": c["porque"],
             "espera": c["espera"], "n": len(vals), "amostra": vals[:6]})

        # ── caso que deve FALHAR ALTO ────────────────────────────────────────
        if c["falha"] is not None:
            try:
                encode(vals)
                falhas.append(f"{nome}: devia falhar e NAO falhou")
                linhas.append((c, "—", None, None, "**NÃO FALHOU**", ""))
            except Exception as e:
                _escreve(RAIZ / "outputs" / f"{nome}.erro.txt",
                         f"{type(e).__name__}: {_normaliza_set(str(e))}\n")
                linhas.append((c, "—", None, None, "fail-loud", type(e).__name__))
            continue

        # ── encode, decode, as quatro provas ─────────────────────────────────
        w1 = encode(vals)
        w2 = encode(vals)
        obtido = decode(w1)
        ok_rt, motivo = rt_estrito(obtido, vals)
        ok_det = w1 == w2
        base = wire_sem_bn(vals)
        ok_np = base is None or len(w1.encode()) <= len(base.encode())
        # CORREÇÃO ≠ bN: o core sozinho também faz RT?
        ok_core = True
        if base is not None:
            try:
                ok_core = rt_estrito(decode(base), vals)[0]
            except Exception as e:
                ok_core = False
                motivo = motivo or f"core sozinho falhou: {type(e).__name__}"

        r = rota(w1)
        ativou = r.startswith("bN")
        esp = c["espera"]
        ok_esp = (esp == "qualquer" or (esp == "ativa") == ativou)

        for cond, rot in ((ok_rt, f"RT ({motivo})"), (ok_det, "determinismo"),
                          (ok_np, "nunca-pior"), (ok_core, "core sozinho"),
                          (ok_esp, f"esperava {esp}, deu {r}")):
            if not cond:
                falhas.append(f"{nome}: {rot}")

        # 5a PROVA — o ARTEFATO é o wire. Lê de volta em binário e compara: se o `.tcf` em
        # disco não for byte-idêntico ao que foi medido, a evidência não vale.
        p_tcf = RAIZ / "outputs" / f"{nome}.tcf"
        _escreve(p_tcf, w1)
        ok_art = p_tcf.read_bytes() == w1.encode()
        if not ok_art:
            falhas.append(f"{nome}: .tcf em disco != wire (tradução de newline?)")
        _wj(RAIZ / "outputs" / f"{nome}.roundtrip.json", obtido)
        if base is not None and not ativou and len(vals) >= 10:
            perdem.append((nome, c["familia"], len(w1.encode()), c["porque"]))
        # A lacuna da rota TIPADA: o bN nao e' nem consultado la' (`T-BN-TIPADO`).
        if not ativou and len(vals) >= 10:
            lac = lacuna_tipada(vals)
            if lac is not None and lac[0] < len(w1.encode()):
                est, rt_ok = lac
                lacunas.append((nome, c["familia"], r, len(w1.encode()), est, rt_ok))
                if not rt_ok:
                    falhas.append(f"{nome}: wire bN da estimativa tipada nao faz RT")

        linhas.append((c, r, len(w1.encode()),
                       len(base.encode()) if base else None,
                       "OK" if (ok_rt and ok_det and ok_np and ok_core and ok_esp and ok_art)
                       else "**FALHOU**", ""))

    # ═══════════════════════════════════════════════════════════ relatório
    n_fam = len({c["familia"] for c in CASOS})
    out = ["# EXP-016 — família bN/bits: bateria sintética completa [probatório]", "",
           f"**{len(CASOS)} casos** em {n_fam} famílias. Cada um declara o que espera "
           "**antes** de rodar; o lab falha quando não acontece.", "",
           "## As cinco provas, por caso", "",
           "| prova | o que garante |", "|---|---|",
           "| **RT estrito** | valor + tipo + sinal + comprimento, contra os dados originais |",
           "| **determinismo** | `encode` duas vezes → byte-idêntico |",
           "| **nunca-pior** | o wire com bN nunca é maior que o wire sem bN |",
           "| **correção ≠ bN** | o core sozinho também faz RT — o bN é opção de TAMANHO |",
           "| **o artefato é o wire** | o `.tcf` em disco, em binário, == o wire medido |",
           ""]

    fam_atual = None
    for c, r, b1, b0, veredito, extra in linhas:
        if c["familia"] != fam_atual:
            fam_atual = c["familia"]
            out += ["", f"## {fam_atual}", "",
                    "| caso | rota | bytes | sem bN | espera | veredito | por que existe |",
                    "|---|---|---:|---:|:-:|:-:|---|"]
        # `|` dentro do texto quebra a coluna da tabela markdown — escapa na RENDERIZACAO,
        # nao na fonte (o catalogo tem de continuar legivel como Python).
        out.append(f"| `{c['nome']}` | {r} | {b1 if b1 is not None else '—'} | "
                   f"{b0 if b0 is not None else '—'} | {c['espera']} | {veredito} | "
                   f"{_esc_md(c['porque'])} |")

    out += ["", "## Resultado", "",
            f"- casos: **{len(CASOS)}**",
            f"- falhas: **{len(falhas)}**" + ("" if not falhas else f" — {falhas}"), ""]

    # ── contraprova agregada ────────────────────────────────────────────────
    ativou_n = sum(1 for c, r, *_ in linhas if r.startswith("bN"))
    out += ["## Contraprova agregada", "",
            f"- o bN **ativou** em {ativou_n} dos {len(CASOS)} casos; nos demais o FLOOR "
            "escolheu o core, o denso ou o tipado — e **em nenhum** o wire ficou maior;",
            "- **em todos** os casos de rota flat, o core sozinho também faz RT: o bN nunca "
            "é necessário para correção, só para tamanho;",
            "- `encode` é determinístico em 100% dos casos.", ""]

    # ── a tabela de larguras, GERADA do código ──────────────────────────────
    # O manual (docs/reference/familia-bn-bits.md) trazia `w ∈ {1,2,4,8}` — errado: é
    # ceil(log2(k)), todo inteiro de 1 a 8. Tabela digitada à mão apodrece; esta sai do
    # `_largura` e falha se a faixa não for contígua.
    larg, k = [], 2
    while k <= MAX_K:
        w = _largura(k)
        fim = k
        while fim + 1 <= MAX_K and _largura(fim + 1) == w:
            fim += 1
        larg.append((k, fim, w))
        k = fim + 1
    for lo, hi, w in larg:
        if any(_largura(x) != w for x in (lo, hi, (lo + hi) // 2)):
            falhas.append(f"tabela de larguras: faixa {lo}..{hi} não é contígua em w={w}")
    _escreve(RAIZ / "outputs" / "tabela-larguras.md", "\n".join([
        "# Larguras do índice bN — gerada de `_largura`, não digitada", "",
        "`w = ceil(log2(k))`, **não** arredondado pra potência de 2: `k=5` usa 3 bits, não 4.",
        f"O teto é `MAX_W={MAX_W}` — a primeira faixa com `w > {MAX_W}` é onde o bN se retira.",
        "", "| `k` | `w` | |", "|---:|---:|---|",
        f"| 1 | {_largura(1)} | não ativa — o core resolve com RLE |",
        *(f"| {lo}{'' if lo == hi else f'–{hi}'} | {w} | "
          f"{'ativa' if w <= MAX_W else f'**não ativa** — passa do teto MAX_W={MAX_W}'} |"
          for lo, hi, w in larg),
        "", "O desperdício que o `T-BN-LARGURA-VARIAVEL` ataca não é arredondamento pra",
        "potência de 2 (não existe) — é arredondamento pro **inteiro**: `k=5` gasta 3 bits",
        "onde a entropia pede log2(5) ≈ 2,32.", ""]))

    # ── regimes que não ativam ──────────────────────────────────────────────
    tot_hoje = sum(h for *_, h, _e, _ok in lacunas)
    tot_est = sum(e for *_, _h, e, _ok in lacunas)
    perdem_md = [
        "# Regimes em que o bN NÃO ativa (n≥10)", "",
        "Gerado por `run.py`. Duas coisas diferentes moram aqui: **decisões corretas do FLOOR**",
        "(§1) e uma **lacuna de rota** que é ticket aberto (§2).", "",
        "## §1 — o FLOOR recusou, e recusou certo", "",
        "Nestes o bN é consultado e **perde**: outro mecanismo do core faz menor. Nada a",
        "corrigir; ficam listados para o estudo de volume — *são comuns no dado real?*", "",
        "| caso | família | bytes | por que existe |", "|---|---|---:|---|",
        *(f"| `{n}` | {f} | {b} | {_esc_md(p)} |" for n, f, b, p in perdem),
        "", "## §2 — a rota TIPADA nem consulta o bN (`T-BN-TIPADO`)", "",
        "Aqui a perda é real e é nossa: `#TCF.8n`/`#TCF.8b` não somam o candidato bN ao seu",
        "`min()`. A coluna `estimativa` é o wire bN **construído de verdade** sobre as grafias",
        "canônicas que o tipado já emite, **com RT conferido**, mais 1 byte para o char de tag",
        "de tipo (índice 6; o modo denso mora no 7, ADR-0029). Não é um wire válido hoje — é a",
        "meta do ticket, ancorada num wire que funciona.", "",
        "| caso | família | rota hoje | bytes hoje | estimativa bN | RT da estimativa | Δ |",
        "|---|---|---|---:|---:|:-:|---:|",
        *(f"| `{n}` | {f} | {r} | {h} | {e} | {'ok' if ok else '**FALHOU**'} | −{h - e} |"
          for n, f, r, h, e, ok in lacunas),
        "", f"**Total nesta bateria sintética:** {tot_hoje} B → {tot_est} B "
        f"(−{tot_hoje - tot_est} B em {len(lacunas)} colunas). O número que vale para decidir",
        "o ticket é o de dado real, não este — a bateria é sintética por construção.", ""]
    _escreve(RAIZ / "outputs" / "regimes-que-perdem.md", "\n".join(perdem_md))

    _escreve(RAIZ / "report.md", "\n".join(out) + "\n")
    print("\n".join(out[-8:]))
    print(f"\n({len(CASOS)} casos; report em report.md; {len(perdem)} regimes que não ativam)")
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
