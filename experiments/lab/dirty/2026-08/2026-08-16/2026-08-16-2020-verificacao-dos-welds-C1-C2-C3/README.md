# Verificação dos welds C1/C2/C3 — a prova vermelho→verde, reproduzível

> **Owner (2026-08-16)**: *"não tenho como acreditar em você... só falar ou falar escondido é
> a mesma coisa que não fazer se não tiver os resultados explícitos para outro conferir, isso
> é o básico do método científico. Não adianta dizer que funcionou, tem que provar que
> funcionou."*

**Ele tem razão, e o furo era real.** Nos três welds eu provei o "vermelho antes" com
`git stash` — **em memória, sem gravar**. A afirmação *"13 dos 16 testes falhavam antes"*
existia só no chat e na mensagem de commit. Isso não é evidência: é a minha palavra.

## O que este lab faz

Materializa o código **PRÉ-WELD direto do git** (`git archive <sha>^ src`) num diretório
temporário e roda o **mesmo repro** em subprocesso contra as duas versões. A comparação é
entre dois interpretadores com duas versões reais do código — **não há afirmação minha no
meio**.

```
python run.py    # sai 0 só se, para CADA weld, o defeito aparecer no PRÉ-weld
                 # e sumir no atual, com o wire byte-idêntico
```

Ele também **prova que extraiu a versão certa**: confere que o marcador do fix está ausente
no código antigo e presente no atual, antes de rodar qualquer repro.

## O resultado (3/3 confirmados)

| weld | ticket | antes | depois |
|---|---|---|---|
| **C2** | `T-META-COLISAO-NOME-POSICIONAL` | decode devolve **2 de 3** colunas; `view` reporta 3 e serve **duplicado** | `ValueError` nos dois |
| **C3** | `T-NATURE-IGNORADA-CALADA` | lista tipada e coluna inexistente **descartadas caladas** | `ValueError` nas duas · contra-prova `list[dict]` **58 B → 58 B, idêntico** |
| **C1** | `T-POLARIDADE-COME-NOME` | `{"obs.": …}` volta como `"obs"`; sweep **48/64** (.8M) e **38/64** (.8H) | volta `"obs."`; **0/64 e 0/64** · single-col polarizado `#TCF.8!` **25 B → 25 B, idêntico** |

## Por que o `git archive` e não `git worktree`

O repo tem caminhos longos em `experiments/` que estouram o limite do Windows num checkout
completo (`Filename too long`). O `git archive <sha>^ src` extrai **só o `src/`** e não
esbarra nisso.

## Onde olhar

| arquivo | o que é |
|---|---|
| `outputs/{C1,C2,C3}-antes.json` | a saída do repro contra o código **pré-weld** |
| `outputs/{C1,C2,C3}-depois.json` | a mesma coisa contra o `src/` atual |
| `outputs/INDEX.md` | a tabela navegável |
| `inputs/{C1,C2,C3}-repro.fonte.json` | o repro literal + o commit + como o antigo foi obtido |

## Vínculo

Welds: `0dec1a06` (C2) · `ec08634c` (C3) · `2464f561` (C1) — Labs irmãos:
[`1330`](../2026-08-16-1330-polaridade-come-nome-de-coluna/) (o lab do C1, com antes/depois
próprio) · [`1450`](../2026-08-16-1450-ordem-de-colunas-no-M/) (onde o C2 foi achado) —
Suíte: `TestPolaridadeComeNome`, `TestMetaColisaoNomePosicional`, `TestNatureIgnoradaCalada`
em `tests/test_f0_boundary_fixes.py`
