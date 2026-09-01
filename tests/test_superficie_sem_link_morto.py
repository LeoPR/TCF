"""A superfície não promete clique no que ninguém consegue abrir.

O dirty lab é **evidência local e não versionada** (`.gitignore`: `experiments/lab/dirty/*`,
com poucas exceções nominais). Isso é decisão do projeto e está certo: o lab é volumoso,
regenerável e carrega dado real. O que não pode é a documentação **linkar** para lá, porque o
link funciona na máquina de quem escreveu e está morto para todo mundo que clona.

Foi assim que o `README.md` passou a citar
`[2026-06-16-staged-and-ordering-brotli/](experiments/lab/dirty/old/refuted/...)` como fonte de
uma afirmação sobre brotli: o caminho existe em disco aqui, o `.gitignore` o cobre, e o
diretório ainda por cima se chama `refuted`. Quarenta e quatro links assim, achados de uma vez
em 2026-09-01.

**A regra**: a superfície cita a TEORIA, que é versionada, não a EVIDÊNCIA, que é local. Quando
só existe a evidência, o número entra no texto e a menção vira nome, sem link. O `docs/theory/`,
os ADRs, o `CHANGELOG` e os labs `clean/` estão todos em git e podem ser linkados à vontade.

**A pergunta que o gate faz** é *"quem clonar consegue abrir?"*, e não *"está rastreado?"*. A
diferença importa: um arquivo recém-criado e ainda não commitado passa, porque ele vai para o
git; um dentro de `experiments/lab/dirty/` não passa nunca, mesmo existindo no disco de quem
escreveu. A primeira versão deste teste perguntava pelo índice e reprovou a primeira página
nova que eu escrevi depois dele.

Duas exclusões, ambas declaradas:

- **`docs/adr/`**: ADR aceito não se edita (regra do projeto), então uma reprovação aqui não
  teria conserto legítimo. Os links antigos deles ficam como registro do que era verdade quando
  a decisão foi tomada. O segundo teste mede quanto isso esconde, para a exceção não virar
  tapete.
- **`docs/archive/`**: o commit `6338ba0c` moveu o material em bloco e declarou o trade-off por
  escrito. Não está no caminho de quem lê para usar.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Só links relativos: `http`, `mailto` e âncoras puras não são deste teste.
_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

_NUL = chr(0)


def _ignorados(alvos: list[str]) -> set[str]:
    """Quais destes caminhos o `.gitignore` cobre, perguntando ao git num lote só.

    O `-z` não é detalhe de estilo. Sem ele o git **cita** a saída (`core.quotepath`) e
    devolve `"experiments/lab/.../caminho com acento"`, com aspas e escapes: nada casava com
    a entrada, a interseção dava zero, e o teste **passava por engano**. Com `-z` a entrada e
    a saída são separadas por NUL e vêm literais.
    """
    if not alvos:
        return set()
    r = subprocess.run(["git", "check-ignore", "-z", "--stdin"], cwd=RAIZ,
                       input=_NUL.join(alvos) + _NUL, capture_output=True, text=True)
    if r.returncode not in (0, 1):     # 0 = achou ignorados, 1 = nenhum, outro = erro
        pytest.skip("git indisponível: este gate depende do `check-ignore`")
    return {x.replace("\\", "/") for x in r.stdout.split(_NUL) if x}


def _inalcancavel(alvo: str, ignorados: set[str]) -> bool:
    """Quem clonar o repositório não consegue abrir isto."""
    a = alvo.rstrip("/")
    if a in ignorados:
        return True                    # o `.gitignore` cobre: nunca chega no clone
    return not (RAIZ / a).exists()     # nem existe: link quebrado comum


def _paginas() -> list[Path]:
    fora = ("docs/archive/", "docs/adr/")
    todas = [RAIZ / n for n in ("README.md", "README.pt-BR.md", "README.pypi.md",
                                "CONTRIBUTING.md", "CONTRIBUTING.pt-BR.md",
                                "STATUS.md", "ROADMAP.md", "MAP.md", "AGENTS.md",
                                "CLAUDE.md", "CHANGELOG.md")]
    todas += sorted((RAIZ / "docs").rglob("*.md"))
    vistas, saida = set(), []
    for p in todas:
        if not p.is_file():
            continue
        rel = str(p.relative_to(RAIZ)).replace("\\", "/")
        if rel in vistas or any(rel.startswith(x) for x in fora):
            continue
        vistas.add(rel)
        saida.append(p)
    return saida


def _links(paginas: list[Path]) -> list[tuple[str, str, int, str, str]]:
    """`(alvo, pagina, linha, rotulo, destino)` de cada link relativo."""
    out = []
    for p in paginas:
        rel = str(p.relative_to(RAIZ)).replace("\\", "/")
        texto = p.read_text(encoding="utf-8")
        for m in _LINK.finditer(texto):
            destino = m.group(2).split("#")[0].strip()
            if not destino or destino.startswith(("http://", "https://", "mailto:")):
                continue
            try:
                alvo = str((p.parent / destino).resolve().relative_to(RAIZ))
            except ValueError:
                continue               # aponta pra fora do repo: outro assunto
            out.append((alvo.replace("\\", "/"), rel,
                        texto[:m.start()].count("\n") + 1, m.group(1)[:40], destino))
    return out


def test_o_proprio_gate_enxerga_o_gitignore():
    """Guarda do guarda: um caminho que o `.gitignore` cobre TEM de ser detectado.

    Sem isto o teste principal vira decoração. Ele já passou verde uma vez com o conjunto de
    ignorados vazio, porque a saída do git vinha citada e nenhuma comparação casava.
    """
    alvo = "experiments/lab/dirty/old/refuted/2026-06-16-staged-and-ordering-brotli"
    if not (RAIZ / alvo).exists():
        pytest.skip("o lab de referência não está nesta cópia de trabalho")
    ignorados = _ignorados([alvo])
    assert alvo in ignorados, (
        "o `check-ignore` não devolveu um caminho que o `.gitignore` cobre. Provável causa: "
        "a saída voltou CITADA (`core.quotepath`), e a comparação por string falhou calada.")
    assert _inalcancavel(alvo, ignorados)


def test_nenhuma_pagina_linka_pra_fora_do_git():
    """Um link que só abre na máquina de quem escreveu é pior que nenhum link."""
    achados = _links(_paginas())
    ignorados = _ignorados([a for a, *_ in achados])
    mortos = [f"{rel}:{ln} [{rot}] -> {d}"
              for alvo, rel, ln, rot, d in achados if _inalcancavel(alvo, ignorados)]
    assert not mortos, (
        f"{len(mortos)} link(s) apontando pra caminho que nao chega em quem clona.\n"
        f"Conserto: cite a TEORIA (docs/theory, ADR, CHANGELOG, labs clean/), que e' "
        f"versionada, ou traga o numero pro texto e deixe a mencao sem link.\n  "
        + "\n  ".join(mortos[:25]))


def test_a_exclusao_dos_adr_e_deliberada_e_tem_tamanho_conhecido():
    """Os ADRs ficam fora do gate, e o teste diz QUANTO isso esconde.

    Sem este número a exclusão vira tapete: alguém acrescenta um ADR com dez links mortos e
    ninguém percebe. Se a conta subir, foi um ADR recente que a trouxe, e o conserto é nele,
    não neste teto.
    """
    achados = _links(sorted((RAIZ / "docs" / "adr").glob("*.md")))
    ignorados = _ignorados([a for a, *_ in achados])
    mortos = sum(1 for alvo, *_ in achados if _inalcancavel(alvo, ignorados))
    TETO = 67          # MEDIDO em 2026-09-01, não estimado. Catraca: só desce.
    assert mortos <= TETO, (
        f"os ADRs acumularam {mortos} links mortos, e o teto medido e' {TETO}. ADR aceito nao "
        f"se edita, entao a saida nao e' consertar os antigos: e' o ADR NOVO nao nascer com "
        f"link pra fora do git.")
