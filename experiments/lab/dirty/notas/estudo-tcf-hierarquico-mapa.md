# Estudo "TCF hierárquico" — mapa do grupo de labs (peças que se juntam) [dispositivo]

**Data**: 2026-07-05 · Ticket-guarda-chuva: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).
Objetivo: pesquisar um **TCF hierárquico** (representar um DatasetH em TCF, textual e reconstruível).
JSON é a primeira fonte/saída de prova, não a definição da hierarquia. Não é 1 lab só — é um **grupo de
peças** que vão se juntar. Este mapa mostra o grupo.

**Plano de pesquisa vigente**: [dataseth-hierarquia-completa-plano.md](dataseth-hierarquia-completa-plano.md)
define o caminho para a estrutura hierárquica completa e registra `null`, `NaN` e infinitos como escalares
em estudo; JSON continua sendo somente uma fonte/saída de prova.

## Como as peças se juntam (a visão do todo)

```
FONTE HIERÁRQUICA (JSON, API, banco, ...)
  │  adaptador de entrada
  ▼
DATASET H
  │  (peça 1) desnormalizar (tabelão) OU normalizar (2+ tabelas)?  → escolha por ramo
   ▼
N TABELAS  ─(peça 2)→ cada uma vira 1 bloco TCF.8, EMPILHADOS um após o outro
   │
   │  (peça 3) CABEÇALHO: hint `#TCF.8 N` + ligação PAI/FILHO entre os blocos
   ▼
ENVELOPE HIERÁRQUICO  ─decode→ reconstrói o DatasetH (RT)
   │
  └─(peças futuras) adaptador de saída JSON/banco · compactar o cabeçalho · leaf multi-col em TCF.8 ·
    link POSICIONAL (repetition level) p/ array-dentro-de-array e N raízes · aninhamento recursivo geral
    · bytes real-world
```

## Peças (labs)

| # | lab | estuda | contribui | estado |
|---|---|---|---|---|
| **1** | [1509-tcf-hierarquico-tabelao-vs-2tabelas](../2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas/) | tabelão (A) vs duas tabelas (B); RLE↔referência | **quando** desnormalizar vs normalizar um ramo; o schema compra reconstrução, não bytes | medido, RT OK |
| **2** | [1543-tcf8-estrutura-aninhada-pessoa-telefones](../2026-07-05-1543-tcf8-estrutura-aninhada-pessoa-telefones/) | 2 TCF.8 empilhados + envelope self-describing (`@tree`) | **prova** que dá pra TCF.8 + aninhar 2 TCFs e decodar | RT OK (draft envelope) |
| **3** | [1608-linking-pai-filho-cabecalho](../2026-07-05-1608-linking-pai-filho-cabecalho/) | **abordagem A**: blocos empilhados + header de ligação pai/filho (hint `#TCF.8 N`) | **como** relacionar TABELAS (faltava); modular/buscável | RT OK (S4+S6) |
| **4** | [1650-multicol-n-hierarquia](../2026-07-05-1650-multicol-n-hierarquia/) | **abordagem B**: 1 multi-col + flag `N` + linha `#H` que reagrupa colunas | reusa o formato atual; complemento barato | RT OK (S4+S6) |
| **5** | [1830-bracket-meta-hierarquia](../2026-07-05-1830-bracket-meta-hierarquia/) | **abordagem C** (mais enxuta): hierarquia em **colchetes no meta**; `M`/`N` e array-vs-objeto **deduzidos** | compacto/implícito; hierarquia opt-in (só p/ reconstruir) | RT OK (S4+S6) |
| **6** | [1840-estudo-notacoes-agrupamento](../2026-07-05-1840-estudo-notacoes-agrupamento/) | **estudo** da NOTAÇÃO de agrupamento (start/end vs contagem vs profundidade) | bytes ~empatam; precisa de 1 **portador de forma**; escolha é parse/stream, não bytes | RT topologia OK |
| **7** | [1906-cardinalidades-inferencia](../2026-07-05-1906-cardinalidades-inferencia/) | **cardinalidade** 1×1/1×N/N×1/N×N deduzida dos dados (FD) → mecânica TCF | **amarra o grupo**: 1:N↔hierarquia (=dual RLE), N:1↔@dict, N:N↔ponte; camada declarativa | dedução OK (4 casos) |
| **8** | [2017-teoria-cardinalidade-forca](../2026-07-05-2017-teoria-cardinalidade-forca/) + [teoria-cardinalidade.md](teoria-cardinalidade.md) | **TEORIA**: força (forte/fraca/quase/induzida) + rápido(RLE)-vs-pleno(OBAT/HCC) + ortogonalidade + cascade | cardinalidade ⊥ compressibilidade; dominância fraca; as 2 vias são um cascade; H-CARD-01..07 | medido (peça 8) |
| **9** | [2328-tcf8-schema-cardinalidade-explicito-implicito](../2026-07-05-2328-tcf8-schema-cardinalidade-explicito-implicito/) | **PONTE header-minimal**: linguagem semântica TCF.8 (cardinalidade/hierarquia) EXPLÍCITA → dedução → MÍNIMA | a forma mínima **converge pra P5**; irredutível = magic+arestas+markers+sizes; custo transmitido ZERO | medido, RT OK |
| 10 | *(futuro)* protótipo formal TCF.8 (arestas explícitas + resto deduzido) + O-FMT-14 derivável | welding (decisão de formato do owner) | src, exige aprovação | **discriminador `H` DECIDIDO** (ADR-0031, 2026-07-09: `H`=multi+hierarquia, especialização de `M`, sem-espaço); **codec** welding ainda aberto/gated |
| 11 | link posicional / N:N (tabela-ponte, repetition level) | array-em-array, N raízes, N:N | o caso que precisa de número, não só forma | **caracterizado (Ciclo 1c)**: B1/B2=def-level (fix provado), B3=rep-level, B4=normalização; welding aberto |
| **R0/R1** | [2026-07-13-dataseth-json-bridge](../2026-07-13-dataseth-json-bridge/) | parser JSON versus intermediário DatasetH; tipos, presença, ordem, vazios e políticas de borda | **separa** fonte, DatasetH e codec; prova JSON↔DatasetH e uma segunda construção Python | POC externo, sem `src/tcf` |

> **P3 (A), P4 (B) e P5 (C) são ALTERNATIVAS** do mesmo passo ("como ligar as tabelas"), do mais
> explícito ao mais implícito: A = blocos separados + header de arestas (modular/buscável); B = um
> multi-col + marcador `N` + `#H`; **C = hierarquia em colchetes no meta, com M/N e cardinalidade
> deduzidos** (o mais próximo de "compacto e implícito"). Decidir qual (ou híbrido) é a peça 6.

## Consolidação (v0 clean + pesquisa DatasetH)

### Pesquisa R0/R1 — DatasetH antes do codec

O primeiro artefato executável source-agnostic é o lab
[2026-07-13-dataseth-json-bridge](../2026-07-13-dataseth-json-bridge/). Ele fixa apenas o mínimo para
pesquisa: um root único formado por objeto, array ou folha; objetos como sequência ordenada de campos;
arrays como sequência ordenada de itens; folhas tipadas (`string`, `integer`, `number`, `boolean`,
`null`). Ausência é campo inexistente, distinta de `null`; objetos/arrays vazios são valores presentes;
chaves duplicadas são rejeitadas pelo adaptador JSON. A representação não pertence ao core e ainda não é
o contrato final do TCF.H.

O POC testa `JSON -> DatasetH -> JSON` e uma construção equivalente por Python, sem chamar `encode`.
Isso separa três perguntas que antes estavam misturadas: se o parser lê a árvore, se o DatasetH preserva
a semântica escolhida e se o codec TCF consegue transportar essa estrutura. A próxima etapa é testar o
segundo elo com um codec externo, não promover o POC diretamente para `src/tcf`.

- **Protótipo CLEAN**: [EXP-015](../../clean/EXP-015-tcf-hierarquico-csv-json/report.md) — codec CSV↔JSON
  em formato **TCF.8H** (`#TCF.8H <colchete-meta>\n<bodies>`), RT-exato S4/S6/C1. É evidência histórica
  de notação, não o contrato DatasetH nem a implementação do core. Consolida P1-P9.
- **Checklist do cabeçalho** (tudo que o header aborda, em 5 camadas: explícito → inferências →
  always-win → by-choice → cobertor-curto): [tcf8h-header-checklist](tcf8h-header-checklist.md).
- **Tickets abertos**: [T-FMT-TCF8H-HEADER](../../../../tickets/T-FMT-TCF8H-HEADER.md) (estrutural),
  [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) (hex-default + dedução),
  [T-FLOW-…-TELEMETRY](../../../../tickets/T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md) (speed/mem S1/S2/S3).
- **Caminho-feliz "fechar TCF.8" — Ciclo 1 (funcionalidade), FECHADO**: [1a tipos](../2026-07-06-2221-tcf8h-fidelidade-tipos/result.md)
  (RT lossless) · [1b tipo A/B/C + formas](../2026-07-06-2238-tcf8h-escala-formas-e-tipos/result.md)
  (C-híbrida default) · [1c fronteira link posicional](../2026-07-06-2246-tcf8h-fronteira-link-posicional/result.md)
  (B1/B2 fix provado, B3/B4 deferido). Checklist: [tcf8h-header-checklist](tcf8h-header-checklist.md).
  Próximo: Ciclo 2 (fluxo S1/S2/S3) · Ciclo 3 (inferências/implicitude) · Ciclo N (spec + welding gated).

## Inventário de hipóteses — exaustão (2026-07-14)

[hierarquia-inventario-hipoteses.md](hierarquia-inventario-hipoteses.md) consolida a EXAUSTÃO da questão
(workflow: recupera as peças + 30 hipóteses + crítico). Achados-chave: (1) **"TCFs concatenados" = já
provado** (P2/P3) pra classe coberta (raiz única, contenção, objeto⊃objeto, array-folha) — inclui
heterogêneo pais/filhos/netos de estruturas diferentes SOB uma raiz, zero mudança de gramática, child-side
append-only; (2) **taxonomia settled**: contenção → presença(def-level) → repetição(rep-level, o único
primitivo faltante = um NÚMERO posicional) → normalização(N:N/snowflake = FK, não contenção); (3)
assimetria de SEGURANÇA: envelope falha-loud fora da classe, tabelão-integrado corrompe calado em
array-em-array (mitigado no lab 2325 pelo self-verify); (4) próximo = **corrida de 3 vias real-world**
(envelope vs tabelão vs union-rectangle) — precisa de 1 payload de API real.

## Convenção do grupo

- Cada peça = 1 lab dirty com nome **`YYYY-MM-DD-HHMM-descrição`** (ordenável) + `artifacts/NN-*`
  (entrada→tradução→tcf→decode) + `run.py` reproduzível + `README`/`result`/`provenance`. Ver
  [dirty-lab-convencoes](dirty-lab-convencoes.md).
- Todas as peças linkam este mapa e o ticket-guarda-chuva.
- Extrair a IDEIA de cada peça; o proto formal (welding em `src/tcf`) é OUTRO passo, só quando o
  conjunto fechar.
