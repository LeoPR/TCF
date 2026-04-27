# TCF Opacity Spectrum — do legivel ao opaco

## Conceito

TCF nao e um formato unico — e um **espectro** de compressao que vai
do totalmente legivel (humano e LLM entendem) ao totalmente opaco
(so o decoder programatico reconstroi).

O usuario nao escolhe "level 2" — escolhe **para quem** esta comprimindo.

## Tres perfis de uso

```
                Legibilidade
                    ↑
    LLM-readable    │  ████████████
                    │  ████████████  L0 expanded + STATS
                    │  █████████     L1 RLE (textual)
    Transport       │  ███████       L2 sort+RLE
                    │  █████         L3 dict+sort+RLE
                    │  ███           L4 delta (futuro)
    Archive         │  █             L5 scale+binary (futuro)
                    │
                    └──────────────→ Compressao
```

### Modo LLM-readable (L0-L1)
- **Quem consome:** LLM via prompt text
- **Legibilidade:** alta (texto claro, nomes legíveis, STATS com respostas)
- **Compressao:** moderada (RLE textual comprime repeticoes)
- **Exemplo:** enviar TPC-H orders para GPT perguntar "qual o total?"
- **Config:** `EncodeConfig(mode="llm")` → level=0, stats=True, precision=2
- **Referencia:** findings F80-F94 mostram que STATS sao essenciais aqui

### Modo Transport (L2-L3)
- **Quem consome:** parser programatico (JS, Python, C)
- **Legibilidade:** media (compacto mas parseavel por humano se necessario)
- **Compressao:** alta (sort+RLE+dict, bom apos gzip)
- **Exemplo:** API REST retornando 1000 rows — substituir JSON
- **Config:** `EncodeConfig(mode="transport")` → level=2, stats=False
- **Referencia:** F70-F73 mostram TCF+gzip 29% menor que CSV+gzip

### Modo Archive (L3+ futuro)
- **Quem consome:** so decoder TCF
- **Legibilidade:** baixa (indices, deltas, possivelmente binario)
- **Compressao:** maxima (delta, scale factor, binary encoding)
- **Exemplo:** guardar dados em disco por meses, espaco minimo
- **Config:** `EncodeConfig(mode="archive")` → level=3+, stats=False
- **Referencia:** H-advanced-encodings.md propoe L4-L6

## Implicacao para o encoder

### Hoje (implementado)

```python
EncodeConfig(level=2)  # controle numerico manual
```

O usuario precisa saber que L0=expanded, L2=sort+RLE, etc.

### Futuro (proposta, nao implementado)

```python
EncodeConfig(mode="llm")        # semantico — encoder escolhe o melhor L0/L1
EncodeConfig(mode="transport")  # semantico — encoder escolhe L2/L3
EncodeConfig(mode="archive")    # semantico — encoder escolhe L3+
EncodeConfig(level=2)           # manual — compatibilidade total
```

`mode` seria um **preset** que configura level, stats, precision.
`level` manual continua existindo para controle fino.

### Futuro avancado: column hints

```python
EncodeConfig(
    mode="transport",
    column_hints={
        "c_name": "readable",     # nao aplicar dict nesta coluna
        "l_comment": "omit",      # excluir coluna (irrelevante)
        "l_extendedprice": "compact",  # usar scale factor
    }
)
```

Permite controle **per-column** do espectro. Nao e prioridade para v1.

## Evidencia empirica do espectro

### Onde LLMs param de entender

Dados dos nossos findings com dados legacy (retail_sales):

| Level | Accuracy gemma3 | O que muda |
|-------|-----------------|-----------|
| L0 (expanded) | 88% | Texto claro, STATS legiveis |
| L2 (sort+RLE) | 75% | `3*Ana` legivel, ordem mudou |
| L3 (dict+indices) | ~53%* | `0 1 0 2` em vez de nomes |

*Dado de G21, v0.1 dataset — precisa revalidar com dados canonicos

### Onde a compressao melhora

| Level | Tamanho TCF | Tamanho apos gzip | Ratio vs CSV+gzip |
|-------|-------------|-------------------|-------------------|
| L0 | ~= CSV | ~= CSV+gzip | ~1.0x |
| L2 | 0.8x CSV | 0.85x CSV+gzip | melhora |
| L3 | 0.5x CSV | 0.71x CSV+gzip | **29% menor** (F70) |

O ponto otimo depende do **consumidor**:
- Se LLM: L0 (legibilidade > compressao)
- Se API: L2-L3 (compressao > legibilidade, mas parseavel)
- Se disco: L3+ (compressao maxima)

## Relacao com tickets existentes

| Ticket (frozen) | Onde se encaixa no espectro |
|-----------------|---------------------------|
| H-token-friendly-format | Otimizar L0/L1 para menos tokens |
| H-advanced-encodings | L4-L6 (archive mode) |
| H-streaming-encoder | Transport mode (chunked, baixa latencia) |
| P-rle-vs-gzip | RLE e para legibilidade (LLM) ou compressao (transport)? |
| E-prompt-presentation | Como explicar o formato para LLM ler melhor |
| H-smart-rounding | Compressao de numericos com perda (transport/archive) |

## Decisao para agora

**Nao implementar modos semanticos na Fase 2.**
O `level=0..3` ja cobre os 3 perfis implicitamente.

**Para o paper v1:** documentar o espectro como conceito, mostrar evidencia
empirica de onde LLMs param de entender, e propor modos semanticos como
extensao futura.

**Para o encoder refatorado:** o `EncodeConfig` atual e suficiente.
`mode="llm"` seria acucar sintatico sobre `level=0, stats=True`.

## Conexao com o que o usuario disse

> "O TCF ficar facil de interpretar em LLM sem segmentar demais"

Traduzido: o modo LLM-readable (L0+STATS) deve ser o **default para LLMs**.
O usuario nao precisa saber de levels — pede `mode="llm"` e o TCF faz o melhor.

> "Ate que ponto uma LLM consegue ler"

Traduzido: o espectro tem um **ponto de corte** por modelo e por nivel.
gemma3 entende L0 mas nao L3. qwen3 entende L0 e L2. Isso e mensuravel
e e o que nossos experimentos validam.

> "Criptografia do dado / quase ilegivel"

Traduzido: modo Archive (L5+) onde delta+scale+binary tornam o texto
incompreensivel para humanos e LLMs, mas maximo compacto. So o decoder
programatico reconstroi. Futuro trabalho.
