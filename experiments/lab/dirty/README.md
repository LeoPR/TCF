# dirty/ — workbench v0.6

**Reset em 2026-05-10.** Reorganizado em macros em 2026-05-13.

## Index — 4 estados claros

> **Convencao organizacional**: era / foi / e' / sera.
> - **era** (velho): em `Mobsolete/` — pre-reset, NAO canonico
> - **foi** (recente, testado): macros fechados com READMEs
> - **e'** (em curso / deu certo): macros ativos
> - **sera** (proximos passos): registrados em notas + memoria

### Layout

```
dirty/
  Mobsolete/                          (era — blueprints pre-reset)
  M0-fase-exploratoria-inicial/       (era — preparo + algoritmo raiz exp 16)
  M0.5-exploracao-sintaxe-pre-M1/     (foi — variantes de sintaxe pre-macro)
  2026-05-12-M1-marcacao-ambiguidade/         (foi — fechado)
  2026-05-13-M2-redundancia-entre-linhas/     (foi — fechado)
  2026-05-13-M3-encadeamento-declaracoes/     (foi — fechado, dim mapeada)
  notas/                              (transversais, vivas)
  README.md                           (este)
```

## Macros — estado atual

| ID | Estado | Foco | Resultado canonico |
|---|---|---|---|
| **Mobsolete** | era | blueprints pre-reset (26 exps 2026-05-07..25) | NAO canonico — ver `AVISO.md` |
| **M0** | foi | 16 exps que culminaram no algoritmo raiz (exp 16) | `online.py` cristalizado |
| **M0.5** | foi | 12 exps de variantes de sintaxe pre-M1 | Interface `Syntax`, vocabulario |
| **M1** | foi | marcacao de ambiguidade local — 6 micros (A, A', B, C, D, E) + F2 | M1.E base (-10.6% vs M1.A); regra de ouro do agrupamento |
| **M2** | foi | redundancia entre linhas — 1 micro (alias tupla) | M2.A (-1.5% vs M1.E nos canonicos; escala linear com R) |
| **M3** | foi | encadeamento de declaracoes — 2 micros (compartilhado, encadeado) | Net 0; dominado por M1.E estruturalmente |

## O que vem a seguir (sera)

Prototipo a partir de dirty:
- Algoritmo base: `online.py` (do exp 16)
- Sintaxe base: M1.E (range + escape escopo)
- Camada opcional: M2.A (alias de tupla)
- Cleanup: remover `[/]` delimitadores, header formal, sem dependencias do dirty

Detalhes em [`../../docs/workbench/research-notes/2026-05-11-sintese-algoritmos-v06.md`](../../../docs/workbench/research-notes/2026-05-11-sintese-algoritmos-v06.md) (a atualizar).

---

## Convencoes do dirty lab

### Proposito

O dirty lab serve para **verificar comportamento**, nao para "descobrir
algo incrivel". Cada experimento responde a uma destas perguntas:

1. **Esta ferramenta pode ser implementada?** (viabilidade tecnica)
2. **Este algoritmo tem o comportamento esperado?** (consistencia)
3. **Este formato funciona?** (roundtrip, edge cases)
4. **Como este experimento se compara, ponto a ponto, com o anterior?**
   (diferencas, nao juizo)

Analise de escala e complexidade algebrica indica **a possibilidade**
de vantagem em algum cenario. Nao estabelece superioridade.

### Vocabulario — disciplina obrigatoria

**Nao usar** nas notas, READMEs, ou qualquer artefato deste lab:

- "incrivel", "surpreendente", "muito melhor", "suipimpa"
- "onde brilha", "destaque", "vencedor", "campeao"
- "descoberta", "achado importante" (use: "comportamento observado")
- superlativos absolutos sem cenario ("melhor", "otimo", "ideal")

**Usar**:

- "diferenca", "variacao", "delta"
- "comportamento sob X", "no cenario Y"
- "menor/maior em N bytes que A em cenario B"
- "comparavel a / nao comparavel a"

Os dados deste lab sao **sinteticos similares aos reais**, **variados
em formato e quantidade**, e **viesados por construcao**. Frases que
afirmam superioridade fora do cenario sao invalidas por principio.

### Camadas de custo (convencao do dirty v0.6)

Comparacoes entre serializacoes distinguem **quatro camadas** de custo,
em ordem decrescente:

1. **Dados efetivos** — strings e estruturas que precisam estar la'
   para reconstruir o input
2. **Marcadores de referencia** — notacao sintatica que liga ref ao
   referente
3. **Marcadores macro / estruturais** — `<body>`, delimitadores
   (escala pequena, nao medir bytes neles)
4. **Comentarios** — metadados humanos (nao contam)

Comparacoes isolam o que muda em uma camada de cada vez.

### Camadas de redundancia (mapeadas pelos macros M1/M2/M3)

| Camada | Onde aparece | Macro |
|---|---|---|
| 1 — local | dentro da linha (escape, quote, range) | M1 |
| 2 — entre linhas | tuplas de refs repetidas | M2 |
| 3 — declaracao | substrings compartilhadas entre eids | M3 |

### Compressao externa (gzip/bz2)

gzip/bz2 NAO fazem parte do TCF. Servem como sinal de redundancia
oculta — agrupamento sintatico interno (M1.E) compete com gzip externo
pelo mesmo recurso. Medir gzip e' intuicao, nao criterio de descarte.

### Comparacoes — regras

- Comparar dois experimentos exige: mesmos dados, mesma metrica, mesma
  definicao operacional. Caso contrario, declarar incomparavel.
- Diferenca observada num cenario nao generaliza para outros.
- Analise algebrica/complexidade aponta possibilidade, nao vantagem.

### Estrutura por micro (a partir de M3)

```
M<X>-<NN>-<nome>/
  README.md          principio + tecnica
  syntax.py          implementacao
  conclusoes.md      analise pos-rodagem
  output/            TCFs gerados
  decoded/           contra-prova
  debug/             detalhado
```

M1 e M2 ainda usam padrao mais antigo (`resultados/<sintaxe>/`
central). Padrao novo (autocontido por micro) adotado a partir
de M3.

### Notas transversais

Em `notas/` (raiz do dirty): notas conceituais que atravessam
varios macros ou registram direcoes futuras a resgatar.
