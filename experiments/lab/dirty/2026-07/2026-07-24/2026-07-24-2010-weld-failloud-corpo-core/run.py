"""Lab 2026-07-24-2010 — verificacao do weld FAIL-LOUD no corpo core.

Roda contra o `src/tcf` REAL (nao prototipo). Tres propriedades SEPARADAS:

  A. BYTE-NEUTRO  — o weld e' caminho-de-erro; wire valido decoda identico e o encode
                    nao muda 1 byte (gates byte-canonicos, pinados ANTES do weld).
  B. FAIL-LOUD    — bateria de corrupcao: nenhuma excecao CRUA (KeyError/IndexError/
                    TypeError/AttributeError) sobrevive; tudo vira ValueError.
  C. ACEITE-CALADO— varredura dedicada da classe que era PIOR que crash: `^N` com N fora
                    de faixa caindo em indice negativo do Python.

Fluxo §3.2: inputs/<ID>-fonte.json -> intermediates/<ID>-dataset-consumido.json
            -> outputs/<ID>-wire.tcf (REAL) -> outputs/<ID>-dataset.roundtrip.json
"""
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]   # .../2026-07-24-2010 -> 2026-07-24 / 2026-07 / dirty / lab / experiments / TCF
sys.path.insert(0, str(REPO / "src"))

from tcf import encode, decode  # noqa: E402

CRUAS = (KeyError, IndexError, TypeError, AttributeError, ZeroDivisionError)

# --------------------------------------------------------------------------- datasets
# Sinteticos mas REALISTAS (feedback validacao-e-dados: dados realistas, nao caos
# artificial). Cada um exercita um mecanismo distinto do corpo core.
FONTES = {
    "A-repetidos":   {"nota": "ref de linha '^N' (valores repetidos)",
                      "dados": ["ativo", "inativo", "ativo", "pendente", "ativo", "inativo"]},
    "B-run":         {"nota": "RLE '*N|' (run adjacente)",
                      "dados": ["ok"] * 40 + ["falha"] * 3},
    "C-prefixo":     {"nota": "fragmento/composicao (prefixo comum)",
                      "dados": [f"pedido-2026-{i:04d}" for i in range(30)]},
    "D-bool":        {"nota": "ramo TIPADO (#TCF.8b) sobre o mesmo core",
                      "dados": [i % 3 == 0 for i in range(24)]},
    "E-bordas":      {"nota": "strings vazias e unitarias",
                      "dados": ["", "a", "", "bb", ""]},
}


def _enc(dados):
    """Encode no DEFAULT — que desde o ADR-0034 ja' e' COM cabecalho em 100% dos casos.

    Historico: nas rodadas 1-2 este helper precisava de `stamp=True` porque o codigo fazia o
    inverso (`list[str]` saia orfao por default). Foi este lab que expos a divergencia — o
    primeiro a codificar `list[str]` pura; todos os anteriores usavam .8H/.8M, que ja' tinham
    header. O owner revisou e o default foi corrigido no src, entao o helper virou passthrough."""
    return encode(dados)


def _w(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# =========================================================== A. BYTE-NEUTRO + RT
def parte_a():
    linhas, falhas = [], 0
    for eid, meta in FONTES.items():
        dados = meta["dados"]
        _w(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": meta["nota"], "dados": dados})
        _w(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", dados)

        wire = _enc(dados)
        (RAIZ / "outputs" / f"{eid}-wire.tcf").write_text(wire, encoding="utf-8")
        volta = decode(wire)
        _w(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", volta)

        ok = volta == dados
        falhas += not ok
        linhas.append((eid, len(dados), len(wire.encode()), "OK" if ok else "FALHOU",
                       repr(wire.split("\n", 1)[0][:14])))
    return linhas, falhas


def gates_byte_canonicos():
    """Os baselines foram pinados ANTES deste weld -> passar = byte-neutro (evidencia real,
    nao auto-afirmacao: se o encode mudasse 1 byte, estes testes quebrariam)."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_regression_v1_baseline.py", "tests/test_real_world_snapshots.py"],
        cwd=REPO, capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout else "?"


# =========================================================== B. FAIL-LOUD (corrupcao)
def _mutacoes(wire):
    """Mutacoes DETERMINISTICAS (nao aleatorias): corpo truncado, char trocado por digito
    (fabrica referencia pendente), '^' injetado, contador RLE corrompido."""
    fora = []
    # Rodada 3: com `stamp=True` TODO wire do lab tem cabecalho. O ramo `else` fica como rede
    # (a rodada 2 tratava a 1a linha de DADOS como header e a blindava das mutacoes).
    if wire.startswith("#TCF."):
        cab, sep, corpo = wire.partition("\n")
        if not sep:
            return fora
        cab += "\n"
    else:
        cab, corpo = "", wire
    for k in range(len(corpo)):
        for novo in ("9", "^", "*", "0"):
            fora.append(corpo[:k] + novo + corpo[k + 1:])
    for corte in (1, 2, 3):
        if len(corpo) > corte:
            fora.append(corpo[:-corte])
    fora += ["^0\n", "^99\n", "^-1\n", "*|x\n", "*x|y\n", "9\n", "0..99\n", "1~77\n",
             "*~2\n", "~x\n"]   # <- classe LOOP INFINITO (achado desta rodada)
    return [cab + c for c in fora]


# Teto do LAB (nao do formato): os counts legitimos destes datasets sao <= 43, entao 1000 e'
# folgado. Rodada 1 usou 100k e o lab estourou 400s — milhares de mutacoes x listas de 100k.
TETO_RLE = 1_000


def _bomba(wire):
    """True se a mutacao declara contador RLE absurdo. ACHADO da rodada 1: rodar essas
    mutacoes travava o lab — `*999999999|y` em 15 B materializa 1e9 elementos (parte D).
    Aqui sao DESVIADAS e contadas a parte, nao escondidas."""
    for linha in wire.split("\n"):
        if linha.startswith("*") and "|" in linha:
            campo = linha[1:linha.find("|")]
            # digitos INICIAIS: cobre tanto '*N|' (core) quanto '*N+M|' (seq-RLE do HCC).
            # Rodada 2 do lab so' olhava campo.isdigit() e a forma '*N+M|' escapava —
            # '*99999999+1|' amplificava igual (dataset C travava).
            i = 0
            while i < len(campo) and campo[i].isdigit():
                i += 1
            if i and int(campo[:i]) > TETO_RLE:
                return True
    return False


def parte_b():
    total = cruas = valerr = aceitou = bombas = 0
    exemplos_crus = []
    for eid, meta in FONTES.items():
        wire = _enc(meta["dados"])
        for mut in _mutacoes(wire):
            total += 1
            if _bomba(mut):
                bombas += 1           # classe AMPLIFICACAO (parte D), nao roda
                continue
            try:
                decode(mut)
                aceitou += 1          # decodou: outro wire valido (sem checksum, esperado)
            except ValueError:
                valerr += 1           # fail-loud: o comportamento desejado
            except CRUAS as e:
                cruas += 1
                if len(exemplos_crus) < 5:
                    exemplos_crus.append((eid, repr(mut[:40]), type(e).__name__, str(e)[:40]))
    return total, valerr, aceitou, cruas, bombas, exemplos_crus


# =========================================================== D. AMPLIFICACAO (achado NOVO)
def parte_d():
    """Amplificacao do contador RLE. FECHADO: virou o weld `max_length` (owner aprovou o
    teto default + override; nome roubado do zlib/bz2/lzma). Aqui a medicao ORIGINAL e'
    preservada com `max_length=0` (sem teto) e, ao lado, o veredito do teto default —
    evidencia dos dois lados, nao so' 'agora barra'."""
    import time
    linhas = []
    for d in ("999", "99999", "9999999", "999999999"):
        w = f"x\n*{d}|y\n"
        t = time.time()
        n = len(decode(w, max_length=0))            # medicao original (sem teto)
        dt = time.time() - t
        try:
            decode(w)                                # teto DEFAULT
            veredito = "passa"
        except ValueError:
            veredito = "**barrado**"
        linhas.append((len(w.encode()), n, n * 2 // len(w.encode()), dt, veredito))
    return linhas


# =========================================================== C. ACEITE-CALADO (^N)
def parte_c():
    """A classe que era PIOR que crash: '^0' -> nos_decl[-1] devolvia o ULTIMO no', calado.
    Varre N fora de faixa em corpos de tamanhos variados e exige ValueError em TODOS."""
    linhas, falhas = [], 0
    for n_decl in (1, 2, 5):
        # valores SEM digito: 'v0'/'v1' fariam o '0'/'1' virar REFERENCIA de fragmento e o
        # proprio corpo-base ja' seria invalido (bug da rodada 2 deste lab, nao do produto).
        base = "".join(chr(ord("a") + i) * 2 + "\n" for i in range(n_decl))
        for n in (-1, 0, n_decl + 1, n_decl + 9, 999):
            wire = base + f"^{n}\n"
            try:
                r = decode(wire)
                verdito, det = "ACEITOU-CALADO", repr(r)
                falhas += 1
            except ValueError as e:
                verdito, det = "fail-loud", str(e)[:44]
            except CRUAS as e:
                verdito, det = f"CRU:{type(e).__name__}", str(e)[:40]
                falhas += 1
            linhas.append((n_decl, n, verdito, det))
        # controle POSITIVO: a faixa valida 1..n_decl tem que continuar funcionando
        for n in range(1, n_decl + 1):
            try:
                decode(base + f"^{n}\n")
            except Exception as e:
                linhas.append((n_decl, n, "REGRESSAO-FAIXA-VALIDA", str(e)[:40]))
                falhas += 1
    return linhas, falhas


# =========================================================== relatorio
def main():
    import time as _t
    _m = lambda s, t0: print(f"[lab] {s}: {_t.time()-t0:.1f}s", file=sys.stderr, flush=True)
    _0 = _t.time()
    a_linhas, a_falhas = parte_a(); _m("A", _0); _0 = _t.time()
    gate_ok, gate_txt = gates_byte_canonicos(); _m("gates", _0); _0 = _t.time()
    b_total, b_val, b_ace, b_cruas, b_bombas, b_ex = parte_b(); _m("B", _0); _0 = _t.time()
    c_linhas, c_falhas = parte_c(); _m("C", _0); _0 = _t.time()
    d_linhas = parte_d(); _m("D", _0)

    out = ["# Resultado — weld FAIL-LOUD no corpo core (2026-07-24-2010)", ""]
    out += ["## A. BYTE-NEUTRO + roundtrip", "",
            "| id | n | wire (B) | RT | cabecalho |", "|---|---:|---:|---|---|"]
    out += [f"| {e} | {n} | {b} | {s} | `{h}` |" for e, n, b, s, h in a_linhas]
    out += ["", f"RT: **{len(a_linhas) - a_falhas}/{len(a_linhas)}** ok.",
            f"Gates byte-canonicos (pinados ANTES do weld): "
            f"**{'PASSOU' if gate_ok else 'FALHOU'}** — `{gate_txt}`", ""]

    out += ["## B. FAIL-LOUD sob corrupcao", "",
            f"- mutacoes deterministicas: **{b_total}**",
            f"- `ValueError` (fail-loud): **{b_val}**",
            f"- decodou p/ outro dado: **{b_ace}** — esperado, o formato nao tem checksum",
            f"- desviadas p/ classe AMPLIFICACAO: **{b_bombas}** (parte D)",
            f"- **excecao CRUA: {b_cruas}** <- a metrica do weld (alvo: 0)", ""]
    if b_ex:
        out += ["Exemplos crus remanescentes:", ""] + [f"- {x}" for x in b_ex] + [""]

    out += ["## C. Aceite-calado (`^N` fora de faixa)", "",
            "| decl | ^N | veredito | detalhe |", "|---:|---:|---|---|"]
    out += [f"| {d} | {n} | {v} | {t} |" for d, n, v, t in c_linhas]
    out += ["", f"Falhas: **{c_falhas}** (inclui controle positivo da faixa valida).", ""]

    out += ["## D. Amplificacao do contador RLE — FECHADO pelo weld `max_length`", "",
            "| wire (B) | elementos (sem teto) | amplificacao | tempo | teto default |",
            "|---:|---:|---:|---:|---|"]
    out += [f"| {b} | {n:,} | {r:,}x | {t:.2f}s | {v} |" for b, n, r, t, v in d_linhas]
    out += ["", "A coluna 'sem teto' e' a medicao ORIGINAL (`max_length=0`), preservada como "
            "evidencia do problema; a ultima coluna e' o veredito do teto default. Nome "
            "`max_length` e a convencao `0 == sem teto` vem do zlib/bz2/lzma — nada "
            "reinventado. Unidade = ELEMENTOS (e' o que a bomba aloca), por coluna, no funil "
            "unico `_decode_column` (protege single/multi/view/hierarquico).", ""]

    ok = a_falhas == 0 and gate_ok and b_cruas == 0 and c_falhas == 0
    out += ["## Veredito", "",
            f"**{'APROVADO' if ok else 'REPROVADO'}** — "
            f"A={a_falhas} falhas, gates={'ok' if gate_ok else 'QUEBROU'}, "
            f"B={b_cruas} cruas, C={c_falhas} falhas."]
    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
