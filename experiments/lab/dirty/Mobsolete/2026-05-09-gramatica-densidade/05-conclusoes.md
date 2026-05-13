# Conclusões — gramática consolidada e impacto na hierarquia Lxxx

---

## O que foi decidido nesta mesa

### 1. Empacotar valores absolutos

Aceitar como flag `Π` opt-in por coluna. Ganho real apenas quando há
muitos absolutos (sem δ ou em chunks). Default = formato canônico do
tipo (ISO 8601 para datas, etc.).

Sintaxe: `# ext: <col>=packed`

### 2. Modo inline (eliminar `\n` quando possível)

Aceitar como flag `I` opt-in por coluna. Funciona bem em tipos
auto-delimitados (datas ISO, deltas, RLE de delta). Falha em refs bare
ou strings genéricas (precisa marcador ou separador).

Sintaxe: `# layout: <col>=inline`

Default = line-mode.

### 3. Shorthand para delta dominante

Aceitar `*+` = `*+1` e `*-` = `*-1` quando dentro de RLE. Justificado
pela frequência (>30% dos deltas em dados temporais são `+1`).

Sem header novo — é regra do parser de delta.

### 4. Tudo o resto fica fora

- `*X` (default 2x) — rejeitado por ambiguidade
- "Delta de delta" — fora do escopo
- Empacotamento de inteiros/decimais — não há ganho real

---

## Hierarquia Lxxx final (com adições desta mesa)

| Flag | Significado | Custo decoder | Status |
|---|---|---|---|
| S | Sort aplicado | 0 (transparente) | default produção |
| R | RLE | ~3 linhas | default produção |
| D | Dict implícito | ~5 linhas | default produção |
| M | Auto-discrim | ~4 linhas | default produção |
| A | Alfabeto adaptativo | ~3 linhas | default produção |
| **Π** | **Empacotar absolutos** | **~4 linhas** | **opt-in** |
| **I** | **Inline mode** | **~5 linhas** | **opt-in** |
| δ | Delta (per-coluna) | ~5 linhas | opt-in |
| P | Prefix elision (per-coluna) | reservado | opt-in |
| L' | Line-RLE (layout) | reservado | opt-in |
| K | Count-recycling (streaming) | reservado | opt-in |

Default produção: `SRDMA` (5 flags, ganho ≥ 0 sempre, custo decoder
~25 linhas).

Default produção otimizada: `SRDMA + δ + Π + I` quando o dataset
justifica (datas, muitos absolutos, valor agregado de inline).

---

## Tamanho final do dataset (todas as flags + shorthand)

| Versão | Bytes | vs CSV (762) |
|---|---|---|
| C1 (CSV bruto) | 762 | — |
| L3 (regra unificada solo) | 415 | -45% |
| L3+S (com sort) | 348 | -54% |
| Mesa síntese (regra unificada + sort) | 342 | -55% |
| Adicionando flag A (alfabeto) | 341 | -55% |
| Adicionando coluna data com δ | 409 | -46% (mais info, menos %) |
| Adicionando flag I + shorthand `*+` | ~395 | -48% |
| Cota teórica (entropy + dict) | ~120 | -84% |

A cada flag, ganhos marginais decrescem. O dataset pequeno não
demonstra todo o potencial — é caso teste para validar mecânica.
Datasets maiores devem amplificar diferenças.

---

## Princípios destilados

1. **Compressão por repetição** ≠ **compressão por representação**.
   Eixos ortogonais. Cada um tem sua mesa.
2. **Per-coluna sempre vence per-arquivo.** Encoder decide local; flags
   ativam features por necessidade.
3. **Defaults para padrões > 30% justificam shorthand.** Abaixo, custo
   de complexidade não retorna em bytes.
4. **Auto-delimitação por prefixo** habilita inline mode sem separadores.
   Restrita a tipos com formato fixo ou prefixo claro.
5. **Modularidade composicional**: cada flag pode ser ligada/desligada
   independente das outras. Custo cumulativo decrescente.

---

## Comparativo total (todas as mesas, atualizado)

```
TCF v0.4 lv=0  ←  literal puro (= flag ∅)
TCF v0.4 lv=1  ←  + RLE (= R)
TCF v0.4 lv=2  ←  + sort + RLE (= SR)
TCF v0.4 lv=3  ←  + dict explícito (= SRD com bloco header dict)

TCF v0.5 default ←  SRDMA  (regra unificada + sort + alfabeto)
TCF v0.5 com δ   ←  SRDMA + δ por coluna
TCF v0.5 full    ←  SRDMA + δ + Π + I + shorthand

TCF v0.5 ablação ←  flag única (R, D, ou ∅) para experimento
```

Migração v0.4 → v0.5 troca níveis discretos por flags compositoriais.
Decoder v0.5 lê v0.4 (parser tolerante). Encoder v0.5 default = SRDMA
(produção otimizada baixo-risco).

---

## Próximas mesas (recomendação ordenada)

1. **Mesa P (prefix elision)** — análoga a δ, para colunas tipo
   `INV-001`, `usr_42`, etc. Falta um dataset com esse padrão.
2. **Mesa L' (line-RLE)** — para datasets com linhas inteiras
   duplicadas. Logs de eventos.
3. **Voltar à mesa de transporte** (`2026-05-07-hipoteses-transporte`).
   Agora que o formato base + densificação estão fechados, podemos
   discutir chunks com base estável.
4. **Protótipo Python** — implementar L3+SA com flags δ, Π, I
   ativáveis. Validar bytes manuais contra implementação real.
5. **Validação em escala** — TPC-H ou similar para confirmar que ganhos
   se mantêm em datasets grandes.

---

## Observação final sobre ordem natural

A ordem que adotamos nas mesas — primeiro estabelecer regra mínima,
depois empilhar flags ortogonais, depois densificar sintaxe — segue o
princípio que o usuário articulou:

> Construção da linguagem primeiro e eliminação de redundâncias
> possíveis em segundo lugar.

A gramática formal cabe em uma página. Cada flag adiciona ~5 linhas no
parser. O default de produção (SRDMA) é matematicamente dominante sobre
qualquer alternativa do conjunto {literal, RLE, dict} clássico. As
extensões (δ, P, L', I, Π) cobrem padrões estruturais não-cobertos pela
base — cada uma com critério claro de quando ativar.

A linguagem está fechada. Próxima fase: testar P, L', e voltar ao
transporte/chunks.
