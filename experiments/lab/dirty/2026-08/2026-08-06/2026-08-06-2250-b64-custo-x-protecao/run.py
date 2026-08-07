"""Lab 2026-08-06-2250 — a verificação de b64 deve ser ligável/desligável?

    "não sei ainda se ele fica ligado ou desligado para essa verificação. Por um lado é uma
     garantia com integridade, mas gasta processamento; por outro, é suspeitar que o arquivo
     tenha defeitos. Talvez fazer algo como pra transmitir manter desligado, e em arquivo
     ligado."

A pergunta pressupõe um **trade-off**: garantia × processamento. Este lab mede os dois lados
antes de decidir, e mede também uma coisa que a formulação não separava — **quais checagens
protegem VALOR e quais só detectam adulteração**.

Mede:
  A. CUSTO — cada checagem isolada, contra o `decode` inteiro, em 3 escalas
  B. PROTEÇÃO — desligando cada uma, o que passa como **valor errado** e o que passa igual
  C. o cruzamento: a mais cara é a que mais protege, ou a menos?

`src/tcf` intocado — este lab não propõe mudança, informa uma decisão.
"""
import base64
import json
import pathlib
import sys
import timeit

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[4]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.bitpack import unpack_w  # noqa: E402
from tcf.composicional.dominio_bn import _le_grafia  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(parents=True, exist_ok=True)


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


def _partes(wire):
    """`(cab, linhas_do_WIRE_INTEIRO, i_payload, payload, w, n)`.

    As linhas incluem o cabeçalho — remontar sem ele decapitava o wire mutado e **toda**
    sonda saía "rejeita", escondendo a medição. O assert da tabela B pegou.
    """
    ls = wire.rstrip("\n").split("\n")
    cab = ls[0]
    w, n = int(cab[7]), int(cab[8:], 16)
    i = next(j for j, l in enumerate(ls) if j > 0 and l.startswith("="))
    return cab, ls, i, ls[i][1:], w, n


def le_parcial(wire, quais):
    """Decodifica aplicando SÓ as checagens de `quais` — para isolar o que cada uma segura."""
    _cab, ls, i, b64, w, n = _partes(wire)
    dom = [_le_grafia(s) for s in _decode_column("\n".join(ls[1:i]) + "\n")]
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4), validate=("validate" in quais))
    if "recod" in quais and base64.b64encode(raw).decode().rstrip("=") != b64:
        raise ValueError("nao-canonico")
    if "tamanho" in quais and len(raw) != -(-n * w // 8):
        raise ValueError("tamanho")
    return [dom[k] for k in unpack_w(raw, w, n)]


SONDAS = {
    "char-invalido": lambda p: p[:5] + "!" + p[5:],
    "quatro-invalidos": lambda p: p[:5] + "!!!!" + p[5:],
    "caixa-trocada": lambda p: p[:-1] + ("a" if p[-1].isupper() else "A"),
    "padding-extra": lambda p: p.rstrip("=") + "==",
    "extensao-zero": lambda p: p.rstrip("=") + "AAAA",
    "truncado": lambda p: p[:-4],
}
CONJUNTOS = {
    "nenhuma": set(),
    "só validate": {"validate"},
    "validate+tamanho": {"validate", "tamanho"},
    "as três": {"validate", "recod", "tamanho"},
}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# A verificação de b64: ligada ou desligada? (2026-08-06-2250)", "",
           "A pergunta pressupõe um **trade-off** — garantia × processamento. Este lab mede "
           "os dois lados, e separa uma coisa que a formulação juntava: **quais checagens "
           "protegem VALOR e quais só detectam adulteração**.", "",
           "## A — o custo, medido", "",
           "| n | payload | `b64decode` | `+validate` | re-codifica | `decode` inteiro | as 3 = |",
           "|---:|---:|---:|---:|---:|---:|---:|"]

    custos = []
    for n in (200, 20_000, 200_000):
        dados = [f"v{i % 3}" for i in range(n)]
        w = encode(dados)
        _cab, _ls, _i, b64, _w, _n = _partes(w)
        raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
        R = 200 if n <= 20_000 else 20
        t_sem = timeit.timeit(lambda: base64.b64decode(b64 + "=" * (-len(b64) % 4)),
                              number=R) / R
        t_val = timeit.timeit(
            lambda: base64.b64decode(b64 + "=" * (-len(b64) % 4), validate=True), number=R) / R
        t_re = timeit.timeit(
            lambda: base64.b64encode(raw).decode("ascii").rstrip("=") == b64, number=R) / R
        Rd = max(3, R // 20)
        t_dec = timeit.timeit(lambda: decode(w), number=Rd) / Rd
        extra = max(0.0, t_val - t_sem) + t_re
        pct = extra / t_dec * 100
        custos.append((n, pct))
        out.append(f"| {n} | {len(b64)} ch | {t_sem * 1e6:.1f} µs | {t_val * 1e6:.1f} µs | "
                   f"{t_re * 1e6:.1f} µs | {t_dec * 1e6:.0f} µs | **{pct:.2f}%** |")
    out += ["", "O `tamanho exato` é uma subtração — não aparece na tabela porque não é "
            "mensurável. O `validate=True` é um **flag em C**: nas escalas grandes some no "
            "ruído.", "",
            f"**As três juntas custam {min(p for _n, p in custos):.2f}%–"
            f"{max(p for _n, p in custos):.2f}% do `decode`.** O trade-off que a pergunta "
            "pressupõe não existe nesta escala.", ""]

    # ---------------------------------------------------------------- B: proteção
    out += ["## B — o que cada checagem realmente segura", "",
            "Desligando por conjunto e vendo o que **passa como valor errado**:", "",
            "| sonda | " + " | ".join(f"`{c}`" for c in CONJUNTOS) + " |",
            "|---|" + "|".join([":-:"] * len(CONJUNTOS)) + "|"]

    dados = [f"v{i % 3}" for i in range(200)]
    w = encode(dados)
    ok = decode(w)
    _cab, ls, i, pay, _w, _n = _partes(w)
    _wj(RAIZ / "inputs" / "coluna-fonte.json", {"n": 200, "k": 3, "amostra": dados[:5]})
    _wj(RAIZ / "intermediates" / "coluna-dataset-consumido.json", dados)
    (RAIZ / "outputs" / "coluna-valido.tcf").write_text(w, encoding="utf-8")
    _wj(RAIZ / "outputs" / "coluna-dataset.roundtrip.json", ok)

    achados = []
    for nome, fn in SONDAS.items():
        l2 = list(ls)
        l2[i] = "=" + fn(pay)
        mut = "\n".join(l2) + "\n"
        (RAIZ / "outputs" / f"sonda-{nome}.tcf").write_text(mut, encoding="utf-8")
        cels = []
        for conj, quais in CONJUNTOS.items():
            try:
                r = le_parcial(mut, quais)
                if r == ok:
                    cels.append("passa (igual)")
                else:
                    cels.append("**VALOR ERRADO**")
                    achados.append((nome, conj))
            except Exception:
                cels.append("rejeita")
        out.append(f"| `{nome}` | " + " | ".join(cels) + " |")

    out += ["", "`passa (igual)` = o wire foi adulterado e o decode aceita, **mas devolve os "
            "valores certos**. `VALOR ERRADO` = devolve dado diferente, em silêncio.", ""]

    # ---------------------------------------------------------------- C: o cruzamento
    out += ["## C — o cruzamento que decide", "",
            "| checagem | custo | protege VALOR? | o que segura sozinha |",
            "|---|---|:-:|---|",
            "| `validate=True` | ~0 (flag em C) | **não** | chars fora do alfabeto — que "
            "sem ela são **descartados** e o payload segue |",
            "| tamanho exato | ~0 (subtração) | **não** | extensão com bytes zero e "
            "truncamento |",
            "| **re-codifica** | ~0,17% | **SIM** | a **caixa trocada** — a única sonda que "
            "muda valores |", "",
            "**A intuição se inverte.** A checagem com custo mensurável é a única que fica "
            "entre um wire adulterado e **dado silenciosamente errado**. As duas gratuitas "
            "só detectam adulteração que devolveria valores corretos.", "",
            "Se alguma fosse opcional, seriam as **gratuitas** — o que não faz sentido.", ""]

    # ---------------------------------------------------------------- a proposta transmissão×arquivo
    out += ["## Sobre \"desligado na transmissão, ligado em arquivo\"", "",
            "O raciocínio tem base: TCP e TLS já carregam checksum/MAC, então corrupção de "
            "**transporte** já é pega uma camada abaixo. Um arquivo em disco não tem essa "
            "garantia no nível da aplicação.", "",
            "Mas a re-codificação **não protege contra corrupção de transporte** — ela "
            "protege contra uma propriedade do **próprio base64**: o último char de um "
            "payload que não fecha em grupo de 3 bytes carrega bits mortos, e existem várias "
            "grafias para os mesmos dados. Isso não vem do canal; vem de quem **produziu** o "
            "wire — encoder com bug, biblioteca de terceiro, ou adulteração deliberada. O "
            "TLS entrega intacto exatamente aquilo que o outro lado mandou, inclusive se o "
            "outro lado mandou uma grafia não-canônica.", "",
            "E há o argumento inverso do streaming: quem lê incremental quer falhar **cedo**, "
            "não depois de já ter emitido metade dos valores.", "",
            "## Recomendação", "",
            "**Manter as três ligadas, sem toggle.** Não porque toggle seja ruim — porque "
            "aqui ele não compra nada:", "",
            "- o custo total é **< 1%**, e as duas que sobrariam ligadas num toggle "
            "\"barato\" são justamente as que **não** protegem valor;",
            "- desligar a re-codificação é aceitar **duas grafias para o mesmo dado**, que é "
            "exatamente o invariante S1.2 que o formato trava no cabeçalho (ADR-0036) e no "
            "modo denso. Um decoder leniente faria `canônico` deixar de ser propriedade do "
            "formato e virar política do leitor.", "",
            "**Se um dia o custo importar** (payload muito grande, CPU crítica), a saída "
            "barata não é desligar: é trocar a re-codificação por uma checagem dos **bits "
            "mortos do último char** — mesma garantia, O(1) em vez de O(n). Fica registrado "
            "como `T-B64-BITS-MORTOS`, não medido aqui.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
