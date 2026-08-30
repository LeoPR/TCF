"""Gera `tickets/ESTADO.md`: o estado de cada ticket, lido do frontmatter.

O problema que ele resolve: `tickets/` tem dezenas de arquivos e o estado de cada um só
existe DENTRO dele. Olhando a pasta não dá para saber o que está aberto, o que fechou e o
que está bloqueado, e o `README.md` da pasta é uma tabela curada de tema, não um mapa de
situação.

Por que um arquivo gerado, e não prefixo no nome nem subpasta: as duas alternativas fazem o
estado viajar no CAMINHO, e o caminho é citado por dezenas de links em docs, ADRs e nos
próprios tickets. Mover um ticket ao fechá-lo quebraria esses links toda vez. O índice
gerado custa uma execução e não move nada.

Uso:
    python scripts/ticket_index.py            # grava tickets/ESTADO.md
    python scripts/ticket_index.py --check    # falha se o arquivo estiver desatualizado

O `--check` é o que o pre-commit roda: ele não regrava, só denuncia, para o índice nunca
divergir do frontmatter sem alguém ver.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TICKETS = RAIZ / "tickets"
SAIDA = TICKETS / "ESTADO.md"

# Os estados que o repo usa, na ordem em que interessam a quem abre o arquivo, com o
# rótulo que agrupa cada família. `status:` livre é aceito: qualquer valor desconhecido
# cai em "outros", visível, em vez de sumir.
# `blocked-by` só classifica quem ainda está de pé: o campo costuma ficar preenchido
# depois que o ticket fecha, e ali ele é histórico, não impedimento.
FAMILIAS = [
    ("bloqueado", "Bloqueados", lambda s, b: bool(b) and not s.startswith("closed")),
    ("in-progress", "Em curso", lambda s, b: s.startswith("in-progress")),
    ("aberto", "Abertos", lambda s, b: s.startswith("open")),
    ("fechado", "Fechados", lambda s, b: s.startswith("closed")),
    ("parado", "Parados", lambda s, b: s.startswith(("parked", "parado", "adiado",
                                                     "deferred"))),
]
ORDEM_PRIO = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _campo(texto: str, nome: str) -> str:
    """Lê um campo escalar do frontmatter. Devolve '' quando ausente."""
    m = re.search(rf"^{nome}:\s*(.*?)\s*$", texto, re.M)
    if not m:
        return ""
    return m.group(1).strip().strip("\"'")


def _blocked(texto: str) -> str:
    """`blocked-by:` aceita lista inline (`[]`, `[a, b]`) e lista em bloco."""
    m = re.search(r"^blocked-by:\s*(.*)$", texto, re.M)
    if not m:
        return ""
    inline = m.group(1).strip()
    if inline and inline != "[]":
        return inline.strip("[]").strip()
    # forma em bloco: linhas `  - algo` logo abaixo
    resto = texto[m.end():].split("\n")
    itens = []
    for linha in resto[1:] if inline == "" else resto:
        if re.match(r"^\s+-\s+\S", linha):
            itens.append(linha.strip()[2:].strip())
        elif linha.strip() and not linha.startswith(" "):
            break
    return ", ".join(itens)


def coleta() -> list[dict]:
    fora = []
    for p in sorted(TICKETS.glob("*.md")):
        if p.name in ("README.md", SAIDA.name):
            continue
        cabeca = p.read_text(encoding="utf-8", errors="replace")[:1500]
        fora.append({
            "arquivo": p.name,
            "titulo": _campo(cabeca, "title") or p.stem,
            "status": _campo(cabeca, "status") or "?",
            "prio": _campo(cabeca, "priority") or "",
            "atualizado": _campo(cabeca, "updated") or _campo(cabeca, "created") or "",
            "bloqueado_por": _blocked(cabeca),
        })
    return fora


def _linha(t: dict) -> str:
    titulo = t["titulo"]
    if ":" in titulo:                       # o título repete o ID; a coluna do link já o dá
        titulo = titulo.split(":", 1)[1].strip()
    if "," in titulo and titulo.startswith(t["arquivo"][:-3]):
        titulo = titulo.split(",", 1)[1].strip()
    bloq = f" · **bloqueado por** {t['bloqueado_por']}" if t["bloqueado_por"] else ""
    prio = f"`{t['prio']}` " if t["prio"] else ""
    return (f"| [{t['arquivo'][:-3]}]({t['arquivo']}) | {prio}{t['status']} | "
            f"{t['atualizado']} | {titulo[:96]}{bloq} |")


def rende(tickets: list[dict]) -> str:
    def chave(t):
        return (ORDEM_PRIO.get(t["prio"], 9), t["arquivo"])

    out = [
        "# Estado dos tickets",
        "",
        "> **Arquivo gerado.** Não editar à mão: a fonte é o `status:` do frontmatter de cada",
        "> ticket. Regenerar com `python scripts/ticket_index.py`. O `README.md` desta pasta é",
        "> outra coisa: lá a curadoria é por TEMA e carrega o histórico do projeto; aqui é só",
        "> a situação de cada um, para quem abre a pasta e precisa saber o que está de pé.",
        "",
    ]
    usados = set()
    for _chave, rotulo, teste in FAMILIAS:
        grupo = [t for t in tickets
                 if t["arquivo"] not in usados and teste(t["status"], t["bloqueado_por"])]
        for t in grupo:
            usados.add(t["arquivo"])
        if not grupo:
            continue
        out += [f"## {rotulo} ({len(grupo)})", "",
                "| ticket | estado | mexido | assunto |", "|---|---|---|---|"]
        out += [_linha(t) for t in sorted(grupo, key=chave)]
        out.append("")
    sobra = [t for t in tickets if t["arquivo"] not in usados]
    if sobra:
        out += [f"## Outros ({len(sobra)})", "",
                "> `status:` fora do vocabulário conhecido. Aparecem aqui em vez de sumir.",
                "", "| ticket | estado | mexido | assunto |", "|---|---|---|---|"]
        out += [_linha(t) for t in sorted(sobra, key=chave)]
        out.append("")
    out += ["---", "", f"{len(tickets)} tickets no total."]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    novo = rende(coleta())
    if "--check" in argv:
        atual = SAIDA.read_text(encoding="utf-8") if SAIDA.exists() else ""
        if atual != novo:
            print(f"{SAIDA.relative_to(RAIZ)} está desatualizado. "
                  f"Rode: python scripts/ticket_index.py", file=sys.stderr)
            return 1
        return 0
    SAIDA.write_text(novo, encoding="utf-8", newline="")
    print(f"{SAIDA.relative_to(RAIZ)}: {len(coleta())} tickets")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
