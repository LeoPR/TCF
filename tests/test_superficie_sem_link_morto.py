"""A superfície não promete clique no que ninguém consegue abrir.

O dirty lab é **evidência local e não versionada** (`.gitignore`: `experiments/lab/dirty/*`,
com poucas exceções nominais). Isso é decisão do projeto e está certo: o lab é volumoso,
regenerável e carrega dado real. O que não pode é a documentação **linkar** para lá, porque o
link funciona na máquina de quem escreveu e está morto para todo mundo que clona.

Foi assim que o `README.md` passou a citar
`[2026-06-16-staged-and-ordering-brotli/](experiments/lab/dirty/old/refuted/...)` como fonte de
uma afirmação sobre brotli: o caminho existe em disco aqui, tem **zero arquivos rastreados**, e
o diretório ainda por cima se chama `refuted`. Quarenta e quatro links assim, achados de uma
vez em 2026-09-01.

**A regra**: a superfície cita a TEORIA, que é versionada, não a EVIDÊNCIA, que é local. Quando
só existe a evidência, o número entra no texto e a menção vira nome, sem link. O `docs/theory/`,
os ADRs, o `CHANGELOG` e os labs `clean/` estão todos em git e podem ser linkados à vontade.

Duas exclusões, ambas declaradas:

- **`docs/adr/`**: ADR aceito não se edita (regra do projeto), então uma reprovação aqui não
  teria conserto legítimo. Os links antigos deles ficam como registro do que era verdade quando
  a decisão foi tomada.
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


def _rastreados() -> set[str]:
    r = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("git indisponível: este gate depende do índice do repositório")
    return set(r.stdout.replace("\\", "/").split())


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


def _fora_do_git(alvo: str, rastreados: set[str]) -> bool:
    """O alvo não está em git nem é diretório que contenha algo em git."""
    a = alvo.rstrip("/")
    return not (a in rastreados or any(x.startswith(a + "/") for x in rastreados))


def test_nenhuma_pagina_linka_pra_fora_do_git():
    """Um link que só abre na máquina de quem escreveu é pior que nenhum link."""
    rastreados = _rastreados()
    mortos: list[str] = []
    for p in _paginas():
        rel = str(p.relative_to(RAIZ)).replace("\\", "/")
        texto = p.read_text(encoding="utf-8")
        for m in _LINK.finditer(texto):
            destino = m.group(2).split("#")[0].strip()
            if not destino or destino.startswith(("http://", "https://", "mailto:")):
                continue
            try:
                alvo = str((p.parent / destino).resolve().relative_to(RAIZ))
            except ValueError:
                continue                       # aponta pra fora do repo: outro assunto
            if _fora_do_git(alvo.replace("\\", "/"), rastreados):
                linha = texto[:m.start()].count("\n") + 1
                mortos.append(f"{rel}:{linha} [{m.group(1)[:40]}] -> {destino}")
    assert not mortos, (
        f"{len(mortos)} link(s) apontando pra caminho que NAO esta' no git. Quem clonar o "
        f"repositorio nao consegue abrir nenhum deles.\n"
        f"Conserto: cite a TEORIA (docs/theory, ADR, CHANGELOG, labs clean/), que e' versionada, "
        f"ou traga o numero pro texto e deixe a mencao sem link.\n  "
        + "\n  ".join(mortos[:25]))


def test_a_exclusao_dos_adr_e_deliberada_e_tem_tamanho_conhecido():
    """Os ADRs ficam fora do gate, e o teste diz QUANTO isso esconde.

    Sem este número a exclusão vira tapete: alguém acrescenta um ADR com dez links mortos e
    ninguém percebe. Se a conta subir muito, a decisão de excluí-los merece ser revista, não
    o número ajustado.
    """
    rastreados = _rastreados()
    mortos = 0
    for p in sorted((RAIZ / "docs" / "adr").glob("*.md")):
        texto = p.read_text(encoding="utf-8")
        for m in _LINK.finditer(texto):
            destino = m.group(2).split("#")[0].strip()
            if not destino or destino.startswith(("http://", "https://", "mailto:")):
                continue
            try:
                alvo = str((p.parent / destino).resolve().relative_to(RAIZ))
            except ValueError:
                continue
            if _fora_do_git(alvo.replace("\\", "/"), rastreados):
                mortos += 1
    TETO = 67          # MEDIDO em 2026-09-01, nao estimado. Catraca: so' desce.
    assert mortos <= TETO, (
        f"os ADRs acumularam {mortos} links mortos, e o teto medido e' {TETO}. ADR aceito nao "
        f"se edita, entao a saida nao e' consertar os antigos: e' o ADR NOVO nao nascer com "
        f"link pra fora do git. Se o numero subiu, foi um ADR recente que o trouxe, e o "
        f"conserto e' nele, nao neste teto.")
