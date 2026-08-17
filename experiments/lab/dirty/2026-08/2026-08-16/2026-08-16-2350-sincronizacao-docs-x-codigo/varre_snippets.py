"""Gate anti-'frase-editada-pela-metade': EXECUTA todo snippet python dos docs vivos.

POR QUE ISSO EXISTE
-------------------
A auditoria de 2026-08-16 consertou 23 afirmacoes usando como regua "procurar o numero
morto conhecido" (1523, 1586, 89616...). A verificacao adversarial de 2026-08-17 achou
mais 54, e o critico de completude identificou a causa: **a regua estava errada**.

As 54 tem UMA assinatura so' -- a frase foi editada pela metade:
  - a tabela de discriminadores foi corrigida no topo, e o fluxograma 175 linhas abaixo ficou
  - `D17a=300` foi corrigido, e `D1-D9=1523` ao lado ficou
  - `{}` foi corrigido, e `[]` na MESMA frase ficou

Procurar string nao pega isso, porque a metade errada nao contem a string procurada.
O que pega e' RODAR o exemplo. Dos 8 achados do critico, 5 vieram de execucao.

Este arquivo e' essa regua. Ele nao sabe nada sobre "o que deveria dar" -- ele so' roda o
que o doc manda rodar e reporta o que quebrou.

O QUE ELE **NAO** FAZ
---------------------
Nao verifica prosa, nao verifica numero solto no texto, e nao sabe conferir a "saida
esperada" quando ela nao esta' num bloco imediatamente adjacente. Ele pega: snippet que
levanta excecao, snippet que importa o que nao existe, e assert do proprio doc que falha.
Um doc que afirma em PROSA algo falso passa por aqui -- por isso ele COMPLEMENTA o run.py,
nao substitui.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]

# Docs VIVOS. Fora: adr/ (imutavel), theory/ + archive/ + workbench/ (log historico),
# old/ e experiments/ (nao sao doc do formato).
ALVOS = [
    "README.md", "README.pt-BR.md", "AGENTS.md", "MAP.md", "ROADMAP.md",
    "docs/tutorials/*.md", "docs/how-to/*.md", "docs/reference/*.md",
    "docs/algorithms/*.md", "docs/*.md",
]
EXCLUI = re.compile(r"(^|[\\/])(adr|theory|archive|workbench|_archive|old)([\\/]|$)")

# Um bloco so' e' executavel se parecer auto-contido. Marcadores de pseudo-codigo:
PULA = re.compile(
    r"^\s*(\.\.\.|#\s*(pseudo|esquema|exemplo conceitual))"
    r"|<[a-z_]+>"          # placeholders tipo <size>
    r"|\.\.\.\s*$",
    re.M | re.I,
)


def blocos_python(texto: str):
    """Devolve (linha_inicial, codigo) de cada ```python ...```."""
    for m in re.finditer(r"^```(?:python|py)\n(.*?)^```", texto, re.M | re.S):
        yield texto[: m.start()].count("\n") + 2, m.group(1)


def executavel(codigo: str) -> tuple[bool, str]:
    """Heuristica conservadora: so' roda o que se sustenta sozinho."""
    if "import" not in codigo and "from " not in codigo:
        return False, "sem import — provavelmente continuacao de outro bloco"
    if PULA.search(codigo):
        return False, "contem placeholder/reticencias — pseudo-codigo"
    try:
        compile(codigo, "<bloco>", "exec")
    except SyntaxError as e:
        return False, f"nao compila ({e.msg}) — trecho ilustrativo"
    return True, ""


def roda(codigo: str, cwd: Path) -> tuple[bool, str]:
    """Roda num subprocesso limpo, com src no path e cwd controlado."""
    prefixo = f"import sys; sys.path.insert(0, {str(RAIZ / 'src')!r})\n"
    p = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", prefixo + codigo],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    if p.returncode == 0:
        return True, (p.stdout or "").strip()
    return False, ((p.stderr or "").strip().splitlines() or ["<sem stderr>"])[-1]


# Um how-to roda SEQUENCIALMENTE: o bloco 2 usa o que o bloco 1 criou (variavel ou
# arquivo). Rodar cada bloco isolado produz falso positivo (NameError/FileNotFoundError)
# que fala do meu harness, nao do doc. Entao acumulo os blocos anteriores DO MESMO
# ARQUIVO e rodo num diretorio temporario proprio -- que e' o que o leitor faz.
def falso_positivo_de_isolamento(erro: str) -> bool:
    return erro.startswith(("NameError:", "FileNotFoundError:")) or "No such file" in erro


def main() -> int:
    arquivos = []
    for padrao in ALVOS:
        for f in sorted(RAIZ.glob(padrao)):
            rel = f.relative_to(RAIZ).as_posix()
            if not EXCLUI.search(rel) and f.is_file():
                arquivos.append(f)
    arquivos = sorted(set(arquivos))

    total = pulados = ok = falhou = 0
    falhas: list[dict] = []
    pulos: list[dict] = []

    import tempfile
    for f in arquivos:
        rel = f.relative_to(RAIZ).as_posix()
        try:
            texto = f.read_text(encoding="utf-8")
        except Exception:
            continue
        acumulado: list[str] = []      # blocos anteriores DESTE arquivo
        with tempfile.TemporaryDirectory(prefix="tcf-snip-") as tmp:
            sandbox = Path(tmp)        # cwd proprio por arquivo: I/O do doc fica contido
            # Um how-to de CSV assume que o LEITOR traz o arquivo -- ele nunca o cria.
            # Semear o insumo e' mais honesto que pular: o que se quer testar e' a LOGICA
            # do snippet, nao se o repo tem um dados.csv. Qualquer .csv que o doc ABRA
            # pra leitura ganha um insumo generico.
            for nome in set(re.findall(r"open\(['\"]([\w./-]+\.csv)['\"]", texto)):
                alvo = sandbox / nome
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_text(
                    "id,nome,cidade,valor\n"
                    "1,Ana Souza,Sao Paulo,10\n"
                    "2,Bruno Lima,Sao Paulo,20\n"
                    "3,Carla Nunes,Rio de Janeiro,30\n",
                    encoding="utf-8", newline="")
            for linha, codigo in blocos_python(texto):
                total += 1
                pode, motivo = executavel(codigo)
                if not pode:
                    pulados += 1
                    pulos.append({"arquivo": rel, "linha": linha, "motivo": motivo})
                    continue

                passou, saida = roda(codigo, sandbox)
                if not passou and falso_positivo_de_isolamento(saida):
                    # 2a tentativa: com o contexto dos blocos anteriores, como o leitor faz
                    passou, saida = roda("\n".join(acumulado + [codigo]), sandbox)

                if passou:
                    ok += 1
                    acumulado.append(codigo)
                else:
                    falhou += 1
                    falhas.append({
                        "arquivo": rel, "linha": linha, "erro": saida,
                        "codigo": textwrap.shorten(codigo.replace("\n", " ⏎ "), 200),
                    })
                    print(f"  [FALHA] {rel}:{linha}\n          {saida[:150]}")

    print()
    print("=" * 74)
    print(f"blocos python encontrados : {total}")
    print(f"  executados e OK         : {ok}")
    print(f"  FALHARAM                : {falhou}")
    print(f"  pulados (nao auto-contidos, DECLARADO — nao e' 'passou') : {pulados}")
    print("=" * 74)

    (AQUI / "RESULTADO-snippets.md").write_text(
        "\n".join([
            "# Varredura de snippets — docs vivos",
            "",
            "Gerado por `varre_snippets.py`. Re-rode com `python varre_snippets.py`.",
            "",
            f"- blocos encontrados: **{total}**",
            f"- executados e OK: **{ok}**",
            f"- **falharam: {falhou}**",
            f"- pulados (não auto-contidos): {pulados} — **declarados abaixo, não contam como aprovados**",
            "",
            "## Falhas", "",
            *([f"### `{x['arquivo']}:{x['linha']}`\n\n```\n{x['erro']}\n```\n\n`{x['codigo']}`\n"
               for x in falhas] or ["Nenhuma.\n"]),
            "## Pulados (declarados)", "",
            "| arquivo | linha | motivo |", "|---|---|---|",
            *[f"| `{x['arquivo']}` | {x['linha']} | {x['motivo']} |" for x in pulos],
            "",
            "## O que este gate NÃO pega", "",
            "Prosa falsa, número solto no texto, e saída-esperada que não esteja num bloco",
            "adjacente. Ele complementa o `run.py` (que confere afirmações nomeadas), não o substitui.",
        ]) + "\n", encoding="utf-8", newline="")
    print(f"-> {AQUI / 'RESULTADO-snippets.md'}")
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
