# 2026-08-22-1200 — auditoria dos READMEs de capa (git + PyPI)

Pedido do owner ao fechar o `.8`: *"revise também a documentação... o README de capa do git e do
pypi, veja se os exemplos estão atualizados, desde o começo do arquivo até o fim."*

É a capa: primeira coisa que se lê no GitHub e a *long description* do PyPI. **4 defasagens reais
achadas e corrigidas**, e o gate que as pegaria antes fica aqui.

## Por que o varredor de snippets não pegava

O [`varre_snippets.py`](../../2026-08/2026-08-16/2026-08-16-2350-sincronizacao-docs-x-codigo/varre_snippets.py)
(2026-08-16) executa todo bloco **python** dos docs vivos, e declara no próprio docstring o que não
faz: *"não verifica prosa, não verifica número solto no texto, e não sabe conferir a 'saída
esperada' quando ela não está num bloco imediatamente adjacente"*.

O README de capa é feito **exatamente disso**: blocos de **wire** (não são python — não executam)
com a contagem de bytes afirmada na **prosa** ao lado. Um wire que envelhece não quebra teste
nenhum; só mente para o leitor. Os 71 blocos python passavam 71/0 enquanto os números da capa
estavam errados.

## As 4 defasagens

| # | onde | doc dizia | real | causa |
|---|---|---|---|---|
| 1 | exemplo aninhado `.8H` | **146 B**, header `fones#:8[`, corpo `*2-1|\2` | **144 B**, `fones#:6[`, corpo `\2` + `\1` | a coluna de tamanhos de array deixou de sair como repetição (`*N-d|`) e virou coluna própria; a **prosa explicava o `*2-1|` em detalhe** |
| 2 | seção de natures | "76 B raw single-col → 39 B (**-49%**)" | **69 B → 39 B (-43%)** | o 76 não corresponde a leitura nenhuma (texto puro = 60 B; `encode()` sem nature = 69 B): número morto |
| 3 | Status | "**861 passed**, 3 skipped" | **1344 passed** | suíte cresceu ~483 testes desde a última edição |
| 4 | Tools shipped | `scripts/shaper/` | `src/shaper/` | movido na reorg de 2026-06-02 |

Todas nos **dois** idiomas. Corrigidas.

## Dois "achados" que eram artefato da régua — declarado

Na primeira passada acusei 7 divergências; **2 eram minhas**:

- **CSV 277 vs 278 B** e **wire flat/nature literal**: um bloco cercado em markdown *sempre* termina
  com LF antes do fence. O wire multi-col real **não** termina em LF
  (`encode(tabela).endswith("\n")` é `False`) — inrepresentável em bloco cercado. A régua final
  compara módulo **um** LF final, com a ressalva escrita no `run.py`.
- Também suspeitei que dois blocos mostrando os mesmos 4 CPFs divergiam (`)K%\7l` vs `)K%7l`).
  **Não divergem**: em single-col o valor é escapado, em coluna raw de multi-col não. Os dois
  blocos estavam certos, cada um no seu contexto. Conferir antes de "corrigir" evitou introduzir
  um erro.

## A régua (reutilizável)

[`run.py`](run.py) **não hardcoda o esperado** — lê o número afirmado no próprio README
(`*(NNN B…)*`), reconstrói o exemplo a partir dos dados que o próprio README mostra (o CSV, o
JSON), roda o `encode` de verdade e compara **bytes e wire literal**. G1 capa flat · G2 aninhado
`.8H` · G3 natures single-col · G4 os 8 valores do `view()` · G5 prosa (suíte) e caminhos citados ·
G6 paridade EN×pt-BR. Sai `1` se divergir.

**19/19 verdes, 0 divergências** após as correções.

## Evidência

[`resultado.json`](resultado.json) · 7 arquivos em [`inputs/`](inputs/) + [`outputs/`](outputs/)
(o CSV e o JSON de entrada; os 5 wires que a capa exibe, gravados como o encoder os emite hoje).
Portão anti-órfão verde.

## Conexões

- Complementa (não substitui): `2026-08-16-2350-sincronizacao-docs-x-codigo` — aquele roda os
  snippets, este confere os números
- [`ADR-0047`](../../../../../../docs/adr/0047-schema-parametro-unico-de-spec.md) — os exemplos já
  migrados para `schema=` foram verificados aqui
- Fechamento do `.8`: `tickets/T-REL-08-CLOSEOUT.md` (F6/DOC-01 é o README)
