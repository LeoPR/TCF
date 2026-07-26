"""Lab 2026-07-26-0200 — colunas FORMATADAS: quando o escape é puro desperdício.

Origem: o owner olhou `A-cpf-like-n200` e notou que a coluna tem CPFs quase todos únicos,
**não gera referência nenhuma**, e mesmo assim paga escape em todo dígito.

    "a ideia era gastar o mínimo possível de indicação pra que o CPF não tenha escape em nada.
     mas obviamente precisamos fazer por alguma regra que se aplique de forma dinâmica e não
     se misture."

A regra testada: **se o corpo não emite referência de fragmento, o cabeçalho declara isso e
dentro da declaração todo dígito é literal**. Binário por coluna, decidido pelo encoder — não
se mistura com nada.

Este lab usa formas FORMATADAS (documento, telefone, CEP, placa, cartão, data, IP…) porque é
onde o padrão aparece: valor com máscara fixa, alta unicidade, dígitos em toda parte.

VALIDAÇÃO (lição do lab 0038): o corpo sem-escape é lido por um **leitor independente**
(`le_sem_escape`), não pela inversa da transformação. Circularidade foi o erro daquele lab.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from semescape import (  # noqa: E402
    aplicavel, le_sem_escape, para_sem_escape, perfil, seqrle_quebra,
)

from tcf import decode, encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)


def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


# ---------------------------------------------------------------- formas FORMATADAS
def gera(forma, n, seed=7):
    g = _lcg(seed)
    if forma == "cpf-mascara":
        return [f"{next(g) % 1000:03d}.{next(g) % 1000:03d}.{next(g) % 1000:03d}-{next(g) % 100:02d}"
                for _ in range(n)]
    if forma == "cnpj-mascara":
        return [f"{next(g) % 100:02d}.{next(g) % 1000:03d}.{next(g) % 1000:03d}/0001-{next(g) % 100:02d}"
                for _ in range(n)]
    if forma == "cep":
        return [f"{next(g) % 99999:05d}-{next(g) % 999:03d}" for _ in range(n)]
    if forma == "telefone":
        return [f"({next(g) % 90 + 10}) 9{next(g) % 10000:04d}-{next(g) % 10000:04d}"
                for _ in range(n)]
    if forma == "cartao":
        return ["-".join(f"{next(g) % 10000:04d}" for _ in range(4)) for _ in range(n)]
    if forma == "placa":
        return [f"{chr(65 + next(g) % 26)}{chr(65 + next(g) % 26)}{chr(65 + next(g) % 26)}"
                f"{next(g) % 10}{chr(65 + next(g) % 26)}{next(g) % 100:02d}" for _ in range(n)]
    if forma == "data-iso":
        return [f"20{next(g) % 30 + 10}-{next(g) % 12 + 1:02d}-{next(g) % 28 + 1:02d}"
                for _ in range(n)]
    if forma == "hora":
        return [f"{next(g) % 24:02d}:{next(g) % 60:02d}:{next(g) % 60:02d}" for _ in range(n)]
    if forma == "ip":
        return [".".join(str(next(g) % 256) for _ in range(4)) for _ in range(n)]
    if forma == "moeda":
        return [f"R$ {next(g) % 10000},{next(g) % 100:02d}" for _ in range(n)]
    if forma == "coord":
        return [f"-{next(g) % 90:02d}.{next(g) % 10 ** 6:06d}" for _ in range(n)]
    if forma == "isbn":
        return [f"978-{next(g) % 10}-{next(g) % 10000:04d}-{next(g) % 10000:04d}-{next(g) % 10}"
                for _ in range(n)]
    raise ValueError(forma)


FORMAS = ["cpf-mascara", "cnpj-mascara", "cep", "telefone", "cartao", "placa",
          "data-iso", "hora", "ip", "moeda", "coord", "isbn"]


def _wj(p, obj, compacto=False):
    txt = json.dumps(obj, ensure_ascii=False,
                     separators=(",", ":") if compacto else (", ", ": "),
                     indent=None if compacto else 2)
    p.write_text(txt + ("" if compacto else "\n"), encoding="utf-8")
    return len(txt.encode())


def caso(forma, dados, gravar=True):
    corpo = _encode_column(dados)
    esc, refs = perfil(corpo)
    ok_modo = aplicavel(corpo)
    corpo_se = para_sem_escape(corpo)

    # validação INDEPENDENTE: lê o corpo sem-escape e compara com o decode REAL do normal
    lido = le_sem_escape(corpo_se) if ok_modo else None
    esperado = decode(encode(dados)) if ok_modo else None
    valida = (lido == esperado) if ok_modo else None

    if gravar:
        wire = encode(dados)
        cab = wire.partition("\n")[0]
        (RAIZ / "outputs" / f"{forma}-wire-normal.tcf").write_text(wire, encoding="utf-8")
        (RAIZ / "outputs" / f"{forma}-corpo-sem-escape.tcfp").write_text(
            (cab + "e" if ok_modo else cab) + "\n" + corpo_se, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{forma}-equivalente.json", dados, compacto=True)
        _wj(RAIZ / "outputs" / f"{forma}-dataset.roundtrip.json", decode(wire))
    return {"corpo": len(corpo.encode()), "se": len(corpo_se.encode()),
            "esc": esc, "refs": refs, "modo": ok_modo, "valida": valida,
            "seqrle": seqrle_quebra(corpo, corpo_se)}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# Escape inútil em colunas formatadas (2026-07-26-0200)", "",
           "Regra testada: **se o corpo não emite referência de fragmento**, o cabeçalho "
           "declara isso e, dentro da declaração, todo dígito é literal — sem escape. "
           "Binário por coluna, decidido pelo encoder.", "",
           "Validação por **leitor independente**, não por inversa (lição do lab `0038`).", "",
           "## n = 500", "",
           "| forma | corpo | escapes | refs | seq-RLE quebra | modo vale? | sem-escape | Δ | leitor |",
           "|---|---:|---:|---:|---:|---|---:|---:|---|"]
    linhas = []
    for forma in FORMAS:
        dados = gera(forma, 500)
        _wj(RAIZ / "inputs" / f"{forma}-fonte.json",
            {"forma": forma, "n": 500, "amostra": dados[:4]})
        _wj(RAIZ / "intermediates" / f"{forma}-dataset-consumido.json", dados)
        r = caso(forma, dados)
        linhas.append((forma, r))
        v = {True: "OK", False: "**FALHOU**", None: "—"}[r["valida"]]
        out.append(f"| `{forma}` | {r['corpo']} | {r['esc']} | {r['refs']} | {r['seqrle']} | "
                   f"{'**sim**' if r['modo'] else 'não'} | "
                   f"{r['se'] if r['modo'] else '—'} | "
                   f"{(r['se'] - r['corpo']) if r['modo'] else 0:+} | {v} |")

    vale = [r for _f, r in linhas if r["modo"]]
    ganho = sum(r["se"] - r["corpo"] for r in vale)
    falhou = [f for f, r in linhas if r["valida"] is False]
    out += ["", f"- o modo vale em **{len(vale)} de {len(linhas)}** formas",
            f"- economia somada: **{ganho} B** "
            f"({100 * ganho / sum(r['corpo'] for r in vale):.0f}% do corpo dessas colunas)",
            f"- leitor independente: **{'todas OK' if not falhou else 'FALHOU em ' + str(falhou)}**",
            "", "**Duas razões distintas para o modo não valer**, e a segunda é o achado:",
            "", "1. a coluna **usa referência de fragmento** — aí o escape está fazendo o "
            "trabalho dele, e a regra corretamente recusa;",
            "2. a coluna tem **marcador seq-RLE** — e tirar o escape o quebra em silêncio, "
            "porque ele localiza os dígitos incrementáveis PELO escape.", "",
            "A razão (2) é **o mesmo bloqueador que derrubou o flip** (lab `0038`). Não é "
            "específico do flip: atinge **qualquer** esquema que remova o escape de dígito. "
            "É o obstáculo comum.", ""]

    # ------------------------------------------------ variação por n e por unicidade
    out += ["## Variação — o modo depende de `n` e da unicidade?", "",
            "| forma | n | únicos | refs | modo vale? |", "|---|---:|---:|---:|---|"]
    for forma in ("cpf-mascara", "cep", "telefone", "ip"):
        for n in (20, 100, 500, 2000):
            dados = gera(forma, n)
            r = caso(forma, dados, gravar=False)
            out.append(f"| {forma} | {n} | {len(set(dados))} | {r['refs']} | "
                       f"{'sim' if r['modo'] else 'não'} |")
    out += ["", "É onde a regra mostra o limite: quanto mais valores, mais chance de o HCC "
            "achar composição e emitir referência — e aí o modo deixa de valer. **Não é uma "
            "propriedade do formato do dado, é do conteúdo.** Por isso tem que ser decidido "
            "pelo encoder a cada coluna, não por tipo declarado.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhou else 1


if __name__ == "__main__":
    sys.exit(main())
