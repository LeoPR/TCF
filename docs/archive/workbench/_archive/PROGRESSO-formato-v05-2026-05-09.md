# Progresso — formato TCF v0.5 (consolidação 2026-05-09)

Estado do trabalho de design feito ao longo das mesas de maio/2026 na
pasta `experiments/lab/dirty/`.

---

## Estado atual: formato base fechado

A linguagem do TCF v0.5 tem **gramática formal**, **regra única
matematicamente dominante**, e **flags compositoriais** para extensões.
Cabe em uma página de regras. Próxima fase: protótipo + validação em
escala.

---

## Decisões maduras (prontas para implementação)

| Decisão | Mesa de origem | Status |
|---|---|---|
| Layout column-major | herança v0.4 | mantido |
| Regra unificada (RLE+dict por linha) | `2026-05-08-rle-dict-unificado/` | dominante; substitui L0/L1/L2/L3 monolíticos |
| Auto-discriminação bare/marcado por coluna | `2026-05-07-combinatoria-simples/` (C11) | flag M default |
| Sort multi-chave declarado em header | `2026-05-08-multisort-e-cabecalho/` | flag S |
| Alfabeto adaptativo (letras p/ colunas numéricas) | `2026-05-08-indices-alfabeto/` | flag A default |
| Delta como pré-transformação por coluna | `2026-05-09-delta-datas/` | flag δ opt-in |
| Empacotamento de absolutos por tipo | `2026-05-09-gramatica-densidade/` | flag Π opt-in |
| Inline mode (eliminar `\n` em tokens auto-delimitados) | `2026-05-09-gramatica-densidade/` | flag I opt-in |
| Shorthand `*+` e `*-` para RLE de ±1 | `2026-05-09-gramatica-densidade/` | regra implícita |
| Hierarquia Lxxx baseada em flags | `2026-05-08-sintese-formato/` | substituiu níveis discretos |
| Gramática formal consolidada | `2026-05-09-gramatica-densidade/04-gramatica-formal.md` | ~50 linhas decoder |

**Default produção:** `flags=SRDMA` (sort + RLE + dict + auto-discrim +
alfabeto). Ganho ≥ 0 sempre vs CSV; -54% no dataset de teste.

**Default produção otimizada:** `SRDMA + δ + Π + I` quando características
do dataset justificam.

---

## Decisões deferidas (precisam de mais pesquisa)

| Item | Razão de deferimento | Ticket / Local |
|---|---|---|
| Compressão por representação de índice (densificação alfabeto, bit-packing) | ganho marginal em datasets pequenos; precisa cardinalidade alta | `tickets/open/S-representacao-de-indice.md` |
| Prefix elision (flag P) | precisa dataset com padrão `INV-001`, `usr_42` etc. | mesa futura quando dataset existir |
| Line-RLE (flag L', layout alternativo) | precisa dataset com linhas duplicadas inteiras (logs) | mesa futura |
| Count-recycling (flag K) | específico de streaming de longa duração; conceito desenhado em C12 | aplicar quando entrar mesa de chunks/transport |
| Tempo/frações com multi-escala | em mesa ativa | `experiments/lab/dirty/2026-05-09-tempo-fracoes/` |
| Validação H-δ5 (delta em datas aleatórias) | precisa dataset com datas embaralhadas | ticket dedicado pendente |

---

## Próximos passos priorizados

1. **Mesa tempo/frações** — em andamento. Refinamento da flag δ para
   timestamps com múltiplas precisões.
2. **Protótipo Python do encoder** — implementar `SRDMA + δ + Π + I`
   ativáveis. Validar bytes manuais contra implementação real.
3. **Validação em escala** — rodar encoder protótipo em TPC-H ou
   similar. Confirmar dominância das flags em N grande.
4. **Voltar à mesa de transporte** (`2026-05-07-hipoteses-transporte/`) —
   agora com base estável, discutir chunks/prioridade/paralelismo.
5. **Mesas P, L', K** — quando datasets justificarem.
6. **Migração v0.4 → v0.5** — documento de migração quando o protótipo
   provar estabilidade.

---

## Referências cruzadas (para os próximos)

### Mesas concluídas (referência)

```
experiments/lab/dirty/
├── 2026-05-07-hipoteses-transporte/     ← chunks/prioridade (pausada, retomar depois)
├── 2026-05-07-combinatoria-simples/     ← C1-C12 explorados
├── 2026-05-07-mesa-compressao-maxima/   ← multi-sort em dataset rico
├── 2026-05-08-multisort-e-cabecalho/    ← H1+H2 (multi-sort + cabeçalho)
├── 2026-05-08-rle-dict-unificado/       ← regra unificada provada dominante
├── 2026-05-08-sintese-formato/          ← Lxxx hierarquia, descarte de variantes
├── 2026-05-08-indices-alfabeto/         ← flag A (auto-alfabeto)
├── 2026-05-09-delta-datas/              ← flag δ
├── 2026-05-09-gramatica-densidade/      ← flags Π, I, shorthand, gramática formal
└── 2026-05-09-tempo-fracoes/            ← em andamento (refinamento de δ p/ timestamps)
```

### Tickets relacionados

```
docs/workbench/tickets/open/
├── S-representacao-de-indice.md         ← deferido (alfabeto/packing avançado)
└── (outros tickets pré-existentes)
```

---

## Princípios destilados (para próximas iterações)

1. **Compressão por repetição** ≠ **compressão por representação**.
   Eixos ortogonais — atacar separadamente.
2. **Per-coluna sempre vence per-arquivo.** Encoder decide local.
3. **Densificação só vale quando frequência > 30%** dos tokens.
4. **Flags compositoriais > níveis discretos.** Cada flag soma ~5 linhas
   no decoder.
5. **Gramática primeiro, otimização depois.** A linguagem precisa estar
   coerente antes de eliminar redundâncias.
6. **Auto-detecção pelo decoder > declaração no header**, exceto para
   ambiguidades fundamentais.
7. **Pré-transformações** (δ, P, L') compõem cleanly com a regra
   unificada — não competem com ela.
