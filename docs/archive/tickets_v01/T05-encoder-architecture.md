# T05 — Arquitetura do Encoder/Decoder

**Status:** EM PROGRESSO  
**Tipo:** Implementação  
**Deps:** T01, T02, T03

## Pergunta
Como estruturar o encoder e decoder TCF em código?

## Componentes

```
Input (CSV + metadata.json)
        │
        ▼
┌─────────────────┐
│  SchemaReader   │  lê metadata.json → descobre PKs, FKs, tipos
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RelationMapper │  constrói grafo: vendas.id_pessoa → pessoas.id
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ColumnAnalyzer │  detecta tipo de cada coluna:
│                 │    - PK (chave, pode virar índice)
│                 │    - FK (referência a outra tabela)
│                 │    - categorical (dict encoding)
│                 │    - numeric (raw ou bins)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DictBuilder    │  para cada coluna categorical/FK:
│                 │    - ordena por frequência
│                 │    - atribui símbolo base-36
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TCFSerializer  │  gera string TCF final
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TCFDeserializer│  lê TCF → reconstrói DataFrames originais
└─────────────────┘
```

## Interface Proposta (CLI)

```bash
# Encoder: CSV + schema → TCF
python -m tcf encode --meta metadata.json --out data.tcf

# Decoder: TCF → CSV
python -m tcf decode data.tcf --out-dir ./restored/

# Info: estatísticas do TCF
python -m tcf info data.tcf

# Eval: roda perguntas no Ollama
python -m tcf eval data.tcf --model gemma3:12b --questions T04
```

## Estrutura de Arquivos

```
tcf/
├── __init__.py
├── schema.py       # SchemaReader, RelationMapper
├── analyzer.py     # ColumnAnalyzer (detecta tipos)
├── encoder.py      # DictBuilder, TCFSerializer
├── decoder.py      # TCFDeserializer
├── cli.py          # Ponto de entrada CLI
└── eval/
    ├── questions.py   # Perguntas + ground truth
    ├── runner.py      # Ollama client
    └── scorer.py      # Comparação resposta vs ground truth
```

## Critério de Aceitação
- `encode` → `decode` → comparar com original: zero diferença nos dados
- TCF de `vendas` cabe em menos de 500 chars (vs ~1500 chars do CSV)
- `eval` retorna JSON com accuracy por pergunta e por formato

## Questões em Aberto
- [ ] Manter compatibilidade com `metadata.json` atual ou redesenhar schema?
- [ ] Encoder deve ser stateless (sem `vocab.json`) ou salvar artefatos?
- [ ] Como lidar com tabelas que não têm FK (apenas categorias livres)?
