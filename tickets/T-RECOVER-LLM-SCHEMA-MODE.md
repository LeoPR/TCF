---
title: T-RECOVER-LLM-SCHEMA-MODE — Gadget LLM (schema + SQL gen, formato LLM-binary)
status: deferred
priority: P3
created: 2026-05-27
updated: 2026-06-15 (PARK pos-0.7 / spin-off; escopo refinado 2026-05-27: gadget paralelo, formato LLM-binary, alertas only)
blocked-by: []
related:
  - tickets/T-RECOVER-SCHEMA-MULTI-TABLE.md  (gadget irmao, coleta schema/stats)
  - src/tcf/side_outputs.py  (framework efeito colateral consumido em paralelo)
  - docs/findings/  (Phase 1 LLM Q01-Q38 historic v0.5 — infra reutilizavel)
---

# T-RECOVER-LLM-SCHEMA-MODE — Gadget LLM auxiliar

> **Fechamento 0.7 (2026-06-15) — PARK (spin-off) pos-0.7**: gadget EXTERNO de foco
> filosofico oposto ao TCF (machine-readable LLM-binary vs human-readable); zero
> impacto em bytes/formato; NAO toca `src/tcf`. Fase 0 recomenda Opcao A (pacote
> separado `tcf-llm-tools`). Retomar como spin-off quando o owner priorizar.

## Contexto + ESCOPO (refinado 2026-05-27)

**Gadget AUXILIAR EXTERNO ao TCF**, paralelo ao schema gadget, **NAO
arruma nada**. Pacote separado recomendado (spin-off).

Owner reforcou (2026-05-27):
> "A outra ferramenta de LLM tambem e' paralela e nao e' do projeto em
> si. Tambem e' um tool que permita uma coleta do schema dos dados,
> estrutura e statisticas, alem de permitir que seja possivel formatar
> pra melhor performance possivel pra que as LLMs entendam — ou seja,
> fica num formato mais 'binario de LLM', sem ter compromisso de agradar
> humanos. E assim ela pode gerar consultas SQL que, funcionando bem,
> permitem que uma consulta baseada em uma pergunta de negocio seja
> feita na fonte de dados, a query responda e essa resposta ai sim
> pode ir pro TCF de fato."

## Proposta — gadget pequeno, foco em "LLM-binary format"

Tres responsabilidades:
1. **Coleta de schema + estrutura + estatisticas** de dados (pode reusar
   output do schema gadget irmao)
2. **Formatacao em "LLM-binary"**: representacao token-otimizada do
   schema/stats, deliberadamente NAO human-friendly. Foco: maximo signal
   por token consumido pelo modelo. Filosofia OPOSTA da do TCF
   (TCF e' human-explainable; LLM-binary aqui e' machine-explainable).
3. **Geracao de SQL** a partir de pergunta de negocio + schema LLM-binary
4. **Execucao** da query em SQLite/DuckDB; output e' dado limpo + ordenado

Fluxo:
```
fonte de dados  ────► schema/stats (gadget irmao OU coleta propria)
                          │
                          ▼
                     formata "LLM-binary"
                          │
                          ▼
   pergunta negocio ───► LLM (com schema LLM-binary)
                          │
                          ▼
                       SQL gerado
                          │
                          ▼
                     executa em DB
                          │
                          ▼
                     dados (response)
                          │
                          ▼
                        encode(data)  ← TCF entra aqui (agnostic)
```

## "Formato LLM-binary" — explicacao

NAO e' binario no sentido tradicional (bytes opacos). E' um formato textual
otimizado pra **economia de tokens LLM** + **alta densidade semantica pro
modelo**, abandonando legibilidade humana:
- Schemas como tuplas compactadas (sem labels longos)
- Stats em notacao cifrada estavel
- Vocabulario controlado de termos curtos
- Pode incluir hints de FK/relacionamentos do schema gadget

Filosofia: **dialogo eficiente com LLM, nao com pessoa**. Quase o oposto
de TCF (que prioriza explicabilidade humana).

## Integracao com SideOutputs (framework existente)

Igual ao schema gadget irmao: este pode consumir SideOutputs em paralelo
pra extrair stats sem custo adicional. Especialmente uteis pro prompt LLM:
- column_features (cardinality, is_numeric, sample) → tipos pro LLM inferir
- multi_info → estrutura de tabela
- per_col → distribuicao por coluna

## Estado atual

- **Existe (em old/tcf/ + docs/findings/)**: Phase 1 LLM benchmark Q01-Q38,
  qualified models, Ollama client. Marcado historic, funcional.
- **Existe**: `pip install -e ".[eval]"` (requests pra Ollama, extra
  opcional)
- **NAO existe**: nem coleta unificada de schema/stats em "LLM-binary",
  nem geracao SQL schema-aware, nem execucao integrada.

## Plano (futuro)

### Fase 0 — Decisao arquitetural
- **Onde vive este gadget?**:
  - Opcao A (RECOMENDADA): pacote totalmente separado `tcf-llm-tools`
    ou nome neutro como `schema-llm-bridge`
  - Opcao B: extra `pip install tcf[llm]` (mas em src/, isolado)
  - Opcao C: scripts/ standalone

### Fase 1 — Coletor + formatador LLM-binary
- Le schema (do gadget irmao ou diretamente)
- Le SideOutputs (se disponivel)
- Formata em "LLM-binary": tuple compacta, vocabulario controlado, sem
  redundancia legivel

### Fase 2 — Prompt + LLM call
- Template: "{schema_llm_binary}\n\nIntent: {business_question}\n\nSQL:"
- Reuso de qualified models do Phase 1 se estaveis (sem requalification)

### Fase 3 — Validador SQL → schema
- Parse SQL gerado, valida que projecoes/joins fazem sentido pro schema
- Feedback loop se invalido

### Fase 4 — Execucao + handoff
- Roda SQL em SQLite/DuckDB
- Output: dict[str, list[str]] pronto pra `encode()`
- **NAO chama TCF** — usuario decide o que fazer com o output

## Conexao

- **NAO toca** src/tcf/
- **Paralelo** ao schema gadget (T-RECOVER-SCHEMA-MULTI-TABLE) — pode
  consumir output dele OU fazer propria coleta
- Reuso de infra v0.5 (old/tcf + docs/findings) respeitando: NUNCA
  importar de old/tcf em src/tcf
- TCF e' agnostico de origem — recebe qualquer dict[str, list[str]]

## Filosofia

- **Gadget pequeno e focado** (nao platform play)
- **So' gera e executa, NAO arruma**: SQL errado e' alerta, nao auto-fix
- **Formato LLM-binary**: oposto explicito da filosofia TCF — TCF e'
  human-friendly; este gadget e' LLM-friendly
- **Zero custo via SideOutputs**: aproveita stats que TCF compute

## Riscos

- Mission creep: TCF e' lib de compressao, nao plataforma de query
- Mitigation: **spin-off como pacote separado** (Opcao A)
- Ollama dependency adiciona setup-friction → opt-in resolve
- "LLM-binary" pode virar dialeto proprietario — manter especificacao
  curta + documentada

## Status

**De prontidao** (registrado 2026-05-27, escopo refinado). Atacar quando
owner decidir; **NAO bloqueia roadmap TCF**.
