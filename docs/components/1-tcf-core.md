---
title: Componente 1 — TCF Core (formato + compressão)
date: 2026-04-23
type: component
status: v0.2 estável; roadmap v0.3 (blocos/streaming)
---

# 1. TCF Core — formato textual columnar com compressão

## Invariantes arquiteturais (não violar)

**TCF Core é ingênuo por design.** Estes invariantes garantem que o componente
permanece pequeno, testável e reusável fora deste projeto:

1. **TCF não importa Shaper.** Shaper é ferramenta de extração; quem chama
   Shaper e entrega `dict[table, list[dict]]` para TCF é o orquestrador (test
   runner ou aplicação cliente).

2. **TCF não importa DatasetReader, DB drivers, ou qualquer ferramenta de
   ingestão.** TCF assume que o cliente já tem dados em memória.

3. **TCF não valida FKs, não detecta tabelas órfãs, não opina sobre qualidade
   do schema.** Confia no input. Falha rápida se o input for malformado.

4. **TCF tem zero dependências externas no core** (`src/tcf/`). Apenas stdlib.
   Cliente Ollama, Pandas, Polars vivem em `experiments/eval/llm_eval/` e
   `scripts/`, nunca em `src/tcf/`.

**Por que esta arquitetura:**
- Permite uso standalone (qualquer dev com CSV/JSON pode comprimir)
- Falha clara — dado errado entra, saída errada sai (sem mascaramento)
- Componibilidade Unix — TCF, Shaper, Qualifier são irmãos coordenados pelo
  orquestrador, não filhos um do outro
- TCF resistente a complexidade de ambiente porque **não tenta** lidar com ela

Se o desenvolvedor não souber preparar dados para TCF, ele tem ferramentas
auxiliares disponíveis (Shaper para extração estratificada de DB, futuro
Schema Qualifier para detectar problemas). Mas TCF em si nunca cresce para
absorver essas responsabilidades.

## O que é

TCF é um formato de serialização textual **orientado a colunas** com
compressão RLE, dict e sort. Reversível, determinístico, stdlib-only.

```
# TCF v0.2 level=2
## vendas n=509 sorted_by=pessoa
# STATS total: n=509 sum=147445.47 min=9.01 max=759.8 avg=289.68
pessoa:
8*Ana
12*Bruno
15*Carla
...
produto:
Caneta
3*Lapis
...
```

- **Orientação columnar:** valores de cada coluna agrupados
- **RLE textual:** `N*val` = val repetido N vezes
- **4 níveis de compressão:** L0 expanded → L3 dict + sorted + RLE
- **STATS opcionais:** hints pré-computados no topo

## Spec e código

- Spec completa: [../article/03-tcf-format.md](../article/03-tcf-format.md)
- Apêndice A (formal): [../article/appendices/A-tcf-spec.md](../article/appendices/A-tcf-spec.md)
- Encoder: `src/tcf/encoder_v02.py`
- Decoder: `src/tcf/decoder_v02.py`
- Compressão: `src/tcf/compression.py`
- Schema parser: `src/tcf/schema.py`

## Capacidades atuais

| Capacidade | Estado |
|-----------|--------|
| Encode/decode 4 níveis L0-L3 | Estável |
| Reversibilidade byte-exata em L0 | 100% (112 testes) |
| Compressão 40-65% vs CSV em L3 | Confirmado (F-Q3, F70-F73) |
| STATS hints embutidos | Estável |
| Multi-tabela + FK hints | Estável |
| CLI (encode/decode/info) | Estável |
| API Python (import tcf) | Estável |

## Achados científicos relacionados

- **Compressão:** TCF L3 comprime 40-65% vs CSV em dados reais; com gzip, 29% menor que CSV+gzip
- **Tokens:** L3 usa 40-50% menos tokens que CSV para mesma informação (relevante para contexto de LLM)
- **RLE notation:** F-Q13 `{A}` — notação `N val` (espaço) ligeiramente superior a `N*val` em alguns modelos, mas diferença pequena; adotado `N*val` como canônico por compacidade

Ver [../methodology/F-findings.md](../methodology/F-findings.md) para catálogo.

## Roadmap — TCF v0.3: blocos, prioridades e streaming

Objetivo: habilitar **transmissão em streaming com decodificação incremental**.
Útil em cenários onde o payload é grande e o receptor quer começar a usar
dados antes de receber tudo.

### Design preliminar

**Block structure:**
```
# TCF v0.3 blocks=4 priority=true
# BLOCK 1 priority=schema
## vendas columns=[pessoa, produto, total] types=[str, str, float]
# STATS ...
# /BLOCK

# BLOCK 2 priority=high column=pessoa
pessoa:
8*Ana
12*Bruno
...
# /BLOCK

# BLOCK 3 priority=medium column=produto
produto:
...
# /BLOCK

# BLOCK 4 priority=low column=total
total:
...
# /BLOCK
```

**Princípios:**
1. **Cada bloco é self-contained** — pode ser decodificado sem os outros
2. **Schema sempre primeiro** — receptor sabe a estrutura antes de receber dados
3. **Prioridade por coluna** — LLM pode usar colunas high-priority sem esperar low
4. **Ordering hint** — encoder marca colunas que devem chegar primeiro
5. **Retrocompatível:** decoder v0.3 lê arquivos v0.2 sem blocos

### Casos de uso

- **Streaming para LLM com contexto limitado:** enviar schema + primeiras N colunas, completar sob demanda
- **Transmissão incremental em rede lenta:** UX "começa a responder enquanto baixa"
- **Decode paralelo:** blocos independentes podem ser decodificados em threads
- **Cache parcial:** armazenar apenas blocos high-priority em memória rápida

### Questões de design em aberto

1. **Como prioridades são atribuídas?** Heurística (cardinalidade inversa → high) ou manual via EncodeConfig?
2. **Bloqueio de decode parcial:** se chega bloco-column B antes do bloco-schema, como o decoder lida?
3. **Checksum por bloco:** detecção de corrupção em transmissão?
4. **Ordering vs priority:** são o mesmo conceito ou distintos?

### Status

Design pré-formal. Não há código ainda. Próximo passo: escrever spec v0.3
preliminar e validar com use case de streaming (enviar schema TCF ao LLM
enquanto dados completos ainda chegam).

## Testes

```bash
python -m pytest tests/ -v    # 112 passed em ~15s
```

Cobrem: roundtrip todos os níveis, 12 cenários sintéticos, benchmark
compressão, infra (metrics, GT, parsers).
