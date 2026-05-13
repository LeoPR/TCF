---
title: Avaliar rename do projeto — TCF e o nome certo?
type: review
status: OPEN
priority: MEDIUM
created: 2026-04-27
origin: Conversa de reorganizacao (apos M-Acomm + M-schema-scope concluidos)
user_quote: "até revisar o nome por exemplo"
see_also:
  - README.md (raiz)
  - pyproject.toml (name = "tcf")
  - docs/article/03-tcf-format.md
---

# Avaliar rename do projeto — TCF e o nome certo?

## Motivacao

"TCF" (Textual Columnar Format) eh descritivo mas:
- "TCF" como sigla colide com varios outros nomes (Trusted Compute
  Framework, Total Cost of Failure, etc.)
- Generico: "textual columnar format" descreve uma classe de formatos,
  nao um especifico
- Perde o diferencial — nao captura RLE+STATS, nao captura "para LLM",
  nao captura schema-aware vs business-aware
- Nao e memorável (acronimo neutro)
- TOON e sibling com nome mais marcante (Token-Oriented Object Notation)
- SEO ruim — busca por "TCF" retorna resultados nao relacionados

## Criterios para um bom nome (proposta)

1. **Curto**: 1-3 palavras ou 4-6 chars sigla
2. **Memoravel**: associativo, sonoro
3. **Searchable**: termo unico (test em Google)
4. **Descritivo**: sugere o dominio (LLM/tabular/compressao)
5. **Sem colisao**: nao colide com produto existente
6. **Pronunciavel**: em PT-BR e EN
7. **Disponivel**: pip name, github org, dominio .ai/.dev

## Candidatos para brainstorm

(Apenas para discussao — nao decididos)

| Candidato | Significado | Pros | Cons |
|-----------|-------------|------|------|
| **TCF** (atual) | Textual Columnar Format | familiar, descritivo, ja no paper | colisao SEO, generico |
| **Tabula** | Tabula rasa, tabela | sonoro, descritivo | pip ocupado (PDF tools) |
| **Colu** | Columnar | curto, marcante | muito generico |
| **TablLM** | Table + LLM | foco LLM explicito | pode confundir TabLLM (Hegselmann 2023) |
| **Squeeze** | Compressao com sentido | catchy | nao descritivo |
| **CoLEM** | Columnar LLM Encoding | sigla unica | pouco intuitiva |
| **TCFmt** | TCF mas com sufixo | mantem brand | nao resolve issues |
| **CTL** / **CTM** | Columnar Tabular Language | curto | conflitos potenciais |
| **TabLeaf** | Table + leaf (RLE alusao) | memoravel | meio infantil |
| **LLMtab** | LLM-table | direto | nao e elegante |

(Adicionar mais candidatos durante a avaliacao)

## Passos para decisao

1. **Pesquisar prior art**: cada candidato em Google + GitHub +
   PyPI + paper search
2. **Test de pronunciabilidade**: dizer 5 vezes em PT-BR e EN
3. **Entrevistar 2-3 colegas**: qual lembra mais facilmente?
4. **Avaliar custo de rename**:
   - Codigo: `src/tcf/` → `src/<novo>/` + atualizar imports
   - Paper: rebrand completo em todos os capitulos
   - README + docs: rebrand
   - Pip publishing: nome final no pyproject.toml
5. **Decisao final** documentada aqui com justificativa

## Custo estimado de rename

- Code: 2-4 horas (find/replace + testes)
- Docs: 4-6 horas (todos os arquivos)
- Paper: 1-2 dias (revisao completa)
- Branding: domains + GitHub setup se for publicar

## Quando fazer

**Recomendacao tentativa**: ANTES da publicacao do paper. Renomear
depois e desconfortavel — papers acadcmicos costumam manter o nome
do primeiro release.

Se decidir manter "TCF": adicionar nota em README + paper explicando
diferenciais vs outras coisas chamadas "TCF" (alternativa: usar
"TCF-LLM" ou "TCF for tabular reasoning").

## Criterio de aceite

- [ ] 5-10 candidatos avaliados
- [ ] Top 3 pesquisados (prior art, pronunciabilidade)
- [ ] Decisao final documentada (manter ou trocar)
- [ ] Se trocar: tickets filhos para code/docs/paper rebrand

## Dependencias

- Nenhuma tecnica. Decisao bloqueia paper finalization se for trocar.

## Impacto estimado

- Avaliacao + decisao: 1-2 dias
- Rebrand completo (se trocar): 2-3 dias

## Notas de revisao futura

Caso queira voltar a este ticket:
- Snapshot do estado "TCF" em git tag `tcf-final` antes de qualquer rename
- pyproject.toml e ponto unico para o pip name; mudar la primeiro
- Considerar manter "TCF" como sigla interna do paper mesmo com nome
  publico diferente (precedent: "MapReduce" o paper, "Hadoop" o produto)
