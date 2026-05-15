# dirty/ — workbench v0.6

**Reset em 2026-05-10.** Reorganizado em macros em 2026-05-13.

> **Verdade canonica**: este e' o **dirty lab v0.6**. Para narrativa
> completa, ver
> [`notas/historia-dirty-lab.md`](notas/historia-dirty-lab.md).
> Para hipoteses futuras: [`notas/roadmap-hipoteses.md`](notas/roadmap-hipoteses.md).

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
  2026-05-13-M2-redundancia-entre-linhas/     (foi — fechado; M2.A dominado em M5)
  2026-05-13-M3-encadeamento-declaracoes/     (foi — fechado, dim mapeada)
  2026-05-13-M4-desfragmentacao-arvore/       (foi — fechado; M4.C1' core do prototipo)
  2026-05-14-M5-pilha-M2A-M4C1p/              (foi — M2.A subsumido por M4.C1')
  2026-05-14-M6-sintaxe-composicional/        (foi — M6.C composicional supera M4.C1')
  2026-05-15-M7-refactor/                     (foi — M7.A == M6.C bytes; refactor + nova estrutura debug)
  2026-05-16-M8-virtual-refs-clean-output/    (foi — M8.A detector unificado -8.4%; convencao output sem brackets/CRLF)
  2026-05-17-M9-stress-adversarial/           (foi — M8.A em 9 datasets; ratio medio 54.3%)
  2026-05-17-M10-datasets-elevation/          (foi — smoke test: M8.A leitura de datasets/synthetic/; byte-identico a M9)
  2026-05-17-M11-welding-step1-alg16-src/     (foi — welding 1: alg16 copiado para src/tcf/core/; byte-identico a M10/M9)
  2026-05-17-M12-welding-step2-m8a-src/       (foi — welding 2: M8.A copiado para src/tcf/composicional/; byte-identico a M11)
  2026-05-17-M13-welding-step3-api-publica/   (foi — welding 3: API publica `from tcf import encode, decode`; byte-identico a M12)
  notas/                              (transversais, vivas; ver historia-dirty-lab.md)
  README.md                           (este)
```

## Macros — estado atual

| ID | Estado | Foco | Resultado canonico |
|---|---|---|---|
| **Mobsolete** | era | blueprints pre-reset (26 exps 2026-05-07..25) | NAO canonico — ver `AVISO.md` |
| **M0** | foi | 16 exps que culminaram no algoritmo raiz (exp 16) | `online.py` cristalizado (= **TCF-CORE / OAS**, nome formal proposto) |
| **M0.5** | foi | 12 exps de variantes de sintaxe pre-M1 | Interface `Syntax`, vocabulario |
| **M1** | foi | marcacao de ambiguidade local — 6 micros (A, A', B, C, D, E) + F2 | M1.E base (-10.6% vs M1.A); regra de ouro do agrupamento |
| **M2** | foi | redundancia entre linhas — 1 micro (alias tupla) | M2.A subsumido em M5; nao vai pro protótipo |
| **M3** | foi | encadeamento de declaracoes — 2 micros (compartilhado, encadeado) | Net 0; dominado por M1.E estruturalmente |
| **M4** | foi | desfragmentacao da arvore — A (instrumentacao) + C1 (runs) + C1' (subseq) | M4.C1' (-5.9% vs M1.E); superado por M6.C |
| **M5** | foi | pilha M2.A + M4.C1' (teste ortogonalidade) | Conclusao revisada apos M6 (M2.A preambulo era regressao) |
| **M6** | foi | sintaxe composicional — `~` cria ref auto-nomeado | M6.C (-8.4% vs M1.E); subsume M4.C1' por R bytes/composicao |
| **M7** | foi | refactor M6.C + nova estrutura debug (tokens/, detector_trace/, redes/) | M7.A == M6.C bytes (619); codigo melhor estruturado |
| **M8** | foi | detector unificado (refs atomicos + virtuais mesma fila) + convencao output (sem brackets, LF) | **M8.A 574 bytes** (-15.1% vs M1.E apos 2 rodadas refinamento); captura pairs (atom, alias) com check body-order de resolution; convencao oficial protótipo |
| **M9** | foi | stress 9 datasets adversariais (D1-D4 canonicos + D5-D9 novos) | RT 9/9 OK; ratio medio 54.3%; D8 cabeca-cauda atinge 26% (otimo); D6 timestamps mostra pre-tx delta como direcao |
| **M10** | foi | smoke test: M8.A le datasets de `datasets/synthetic/` (canonico) | RT 9/9 OK; byte-identico a M9; valida abstracao do dataset path |
| **M11** | foi | welding step 1: alg16 copiado para `src/tcf/core/online.py` | RT 9/9 OK; byte-identico a M10; valida copia byte-exata do alg16 |
| **M12** | foi | welding step 2: M8.A composicional para `src/tcf/composicional/syntax.py` (imports adaptados) | RT 9/9 OK; byte-identico a M11; valida package layout funcional |
| **M13** | foi | welding step 3: API publica `from tcf import encode, decode` | RT 9/9 OK; byte-identico a M12; **encode/decode formalmente em src/** |

## Sintaxes ativas vs dominadas (triagem 2026-05-13)

| Sintaxe | Bytes canonicos | vs M1.E | Status |
|---|---:|---:|---|
| **M1.E** | **676** | base | **ativa (base)** |
| **M8.A virtual refs** | **574** | **-15.1%** | **ativa** (detector unificado + check body-order; convencao output limpa; core do prototipo) |
| M7.A composicional | 619 (com brackets) / 603 (clean) | -8.4% / -10.8% | superada por M8.A |
| M6.C atual | 619 | -8.4% | superada (estrutura velha) |
| M4.C1' atual | 636 | -5.9% | dominada (close marker redundante; subsumida por M6.C/M7.A) |
| M6.A (M2.A inline) | 664 | -1.8% | dominada (detector sufix-only; coverage restrita) |
| M2.A (preambulo) | 666 | -1.5% | dominada (preambulo regressao; ver M6) |
| M1.A | 756 | +11.8% | dominada |
| M1.A' | 744 | +10.1% | dominada (M1.E e' superset) |
| M1.B | 753 | +11.4% | dominada (nicho estreito) |
| M1.D | 728 | +7.7% | estruturalmente pior |
| M1.C | 676 | 0 | empate (regra de ouro do agrupamento) |
| M3.A / M3.B | 676 | 0 | empate (M1.E ocupa o nicho) |
| M4.C1 v1 | 666 | -1.5% | dominada (mesmo regime que M2.A) |
| M5.A (pilha) | 636 | -5.9% | == M4.C1' (revisado em M6) |

Dominadas mantidas em disco para referencia (nao deletar). Apenas
desativadas dos `SINTAXES_REGISTRADAS` para reduzir ruido em
matrizes futuras.

## O que vem a seguir (sera)

**Dirty fechado**: M8 entregou detector unificado (refs atomicos +
virtuais no mesmo espaco) e convencao output (sem brackets, LF only).
M8.A captura pairs (atom, alias) e (alias, alias) — virtuais
participam naturalmente das sub-tuplas. -13.6% vs M1.E.

**Direcoes registradas** (ficam pro prototipo ou macros futuros):
- Detector permitindo multiplos virtuais (binarization right-assoc).
- Pre-emit aliases standalone para usar final ids inline em positions.
- Detector global (nao greedy) — busca otima.
- Nos pos-construcao com literal+ref (ver `notas/marcadores-multiplo-proposito.md`).

**Protótipo a partir de dirty**:
- Algoritmo base: **TCF-CORE** (alg16 intocado de
  `M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py`)
- Sintaxe core: **M1.E + M8.A virtual refs** (canonico)
- Convencao output: ver `notas/convencao-output-tcf.md` (sem brackets, LF)
- Camada de pre-tx opcional: delta, estrutural — ver
  `notas/comparacao-modular-camadas.md`

Detalhes em [`../../docs/workbench/research-notes/2026-05-11-sintese-algoritmos-v06.md`](../../../docs/workbench/research-notes/2026-05-11-sintese-algoritmos-v06.md) (a atualizar quando dirty fechar).

## Direcoes futuras registradas (notas transversais, nao acionaveis no dirty)

- [`notas/comparacao-modular-camadas.md`](notas/comparacao-modular-camadas.md) —
  comparacao no TCF-CORE pode virar parametro modular
  (literal/delta/estrutural/aproximado); pre-tx ortogonal ao
  protótipo
- [`notas/quebra-de-linha-como-marcador.md`](notas/quebra-de-linha-como-marcador.md) —
  quebras como marcadores opcionais
- [`notas/2026-05-11-tipos-com-estrutura.md`](notas/2026-05-11-tipos-com-estrutura.md) —
  CPF/UUID/IP via mascara estrutural
- [`notas/2026-05-11-comparacoes-nao-literais.md`](notas/2026-05-11-comparacoes-nao-literais.md) —
  delta lossless como pre-tx
- [`notas/2026-05-11-marcadores-compactos.md`](notas/2026-05-11-marcadores-compactos.md) —
  sintaxe ultra-compacta + inferida por ordem

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
