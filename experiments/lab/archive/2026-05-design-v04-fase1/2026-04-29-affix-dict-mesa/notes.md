# Lab dirty: affix-DICT — testes de mesa (matematica vs dados)

## Objetivo

Validar empiricamente a formula matematica da Proposta H
(affix-aware DICT) registrada em
[H-compression-v04-roadmap.md](../../../../docs/workbench/tickets/open/H-compression-v04-roadmap.md):

```
Δ = (c·N - 1)·|P| - overhead - (1-c)·N·|marker|
```

NAO eh experimento formal. Eh "teste de mesa" para construir
intuicao com dados variados.

## Hipoteses a verificar

| H | Predicao matematica | O que medir |
|---|--------------------|-----------|
| H1 | Identificadores sinteticos (Supplier#NNN): GANHA | bytes economizados vs DICT padrao |
| H2 | URLs (https://...): GANHA medio | idem |
| H3 | Emails (sufixo @): GANHA SE sufixo tratado | sufixo: implementar ou nao |
| H4 | Datas ISO (2026-05-): MARGINAL | bytes economizados |
| H5 | Nomes pessoais: NEUTRO ou perde | confirmar formula com c~0 |
| H6 | Texto livre: PERDE | algoritmo deve detectar e desativar |
| H7 | Hashes/UUIDs: NEUTRO (LCP=0) | confirma C5 |

## Metodo

1. Sintetizar/coletar 7 datasets pequenos (10-100 valores cada)
2. Calcular LCP (longest common prefix) por dataset
3. Aplicar formula: prever ganho
4. Comparar com encoding manual sem affix
5. Tabelar: previsto vs observado

## Material

Datasets sinteticos para garantir variabilidade controlada:

- **D-id**: 50 ids `Supplier#000000NNN`
- **D-url**: 30 urls com prefixos `https://example.com/path/`
- **D-email**: 40 emails clusterizados em 2 dominios
- **D-date**: 60 datas ISO concentradas em 2 meses
- **D-name**: 30 nomes proprios
- **D-text**: 20 frases curtas
- **D-uuid**: 50 hex hashes 16-char

## Saida esperada

Tabela tipo:

| Dataset | N | \|P\| LCP | c | Δ previsto | Δ medido | Match? |
|---------|---|---------|---|-----------|---------|--------|

Se previsto ≈ medido em todos os 7, **a formula esta correta**.
Se houver discrepancia, investigar ate fechar.

## NAO e objetivo

- Decidir se implementar (decisao em separado, no ticket)
- Otimizar performance
- Roundtrip (teste de mesa eh so encode + medicao)

Saida: `./output/`

---

## Resultados (run.py — 2026-05-05)

### Tabela medida

| Dataset | N | \|P\| | c | Δ previsto | Δ medido | Status |
|---------|---|------|---|-----------|---------|--------|
| D-id (Supplier#NNN) | 50 | 16 | 1.00 | +761B | +761B | **OK** |
| D-url (https://...) | 30 | 36 | 1.00 | +1021B | +1021B | **OK** |
| D-date (ISO) | 60 | 6 | 1.00 | +331B | +331B | **OK** |
| D-email (clusters 50/50) | 40 | 0 | — | -23B | +0B | bypass |
| D-name (pessoais) | 30 | 0 | — | -23B | +0B | bypass |
| D-text (livre) | 20 | 0 | — | -23B | +0B | bypass |
| D-uuid (hex) | 50 | 0 | — | -23B | +0B | bypass |

### Achados

**1. Formula matematica bate exato (±0B) nos 3 casos com prefixo limpo**

Onde c=1.0 e |P|≥5, a previsao Δ = (c·N - 1)·|P| - overhead casa
ao byte com a medicao real. Confirma C1, C2, C3 do ticket.

**2. Ganho real em prefixo limpo: 50-80% do tamanho naive**

- D-id: -79.7% (50 ids × 18 chars → 12 chars/linha + 1 prefix)
- D-url: -77.1% (30 urls × 50 chars → 14 chars/linha)
- D-date: -49.8% (60 datas × 10 chars → 4 chars/linha)

Numeros muito acima do esperado intuitivo. Em datasets com
identificadores estruturados, **affix-DICT eh dominante**.

**3. Auto-bypass natural: Δ=0 onde a formula prediz -23B**

Casos sem prefixo (|P|=0) deveriam custar +23B de overhead se
forcassem affix. Mas o algoritmo correto **detecta |P|=0 e nao
emite o header**, retornando ao encoding naive. Resultado: Δ=0
em vez de -23B.

Implicacao: **auto-bypass NAO eh otimizacao — eh a propria forma
correta**. Sem ele, perderia em 4/7 cenarios.

**4. D-email revelou limite do algoritmo ingenuo**

Dois clusters claros (`@gmail.com`, `@company.com`) com 50% cada,
mas LCP full retorna "" e LCP com cobertura 70% tambem nao acha.
Algoritmo perde a oportunidade.

Para pegar este caso precisaria:
- Multi-prefix detection (k-means de prefixos)
- Ou: deteccao de **sufixos** (afixo @-dominio)

Ambos saem do escopo inicial da Proposta H. Registrado como
extensao futura.

### Afirmacoes induzidas (com rigor)

| # | Afirmacao | Evidencia |
|---|-----------|-----------|
| A1 | Quando c=1.0 e \|P\|≥5: ganho previsto pela formula bate exato | 3/3 casos testados |
| A2 | Ganho em prefixo limpo eh substancial (50-80% do naive) | medido |
| A3 | Auto-bypass eh OBRIGATORIO; sem ele o algoritmo perde em ~57% dos casos sinteticos | medido |
| A4 | Multi-cluster (D-email) NAO eh capturado pelo algoritmo ingenuo | medido |
| A5 | Sufixos NAO foram testados; podem ser uma classe inteira de wins perdida | nao testado |

### O que NAO foi provado neste lab

- Datasets sao **sinteticos** — distribuicao real de \|P\| e c em
  datasets do mundo eh desconhecida (D1, D2 do ticket)
- **Sufixos** (D6) nao testados
- **Interacao com gzip do transporte** (D4) nao testada
- **Multi-prefix clusters** (D3) confirmado como limite, nao resolvido

### Decisao informada (com base nestes dados)

Affix-DICT **vale implementar** com 3 condicoes:

1. **Auto-bypass obrigatorio** (algoritmo verifica |P| antes de emitir)
2. **Threshold minimo**: \|P\|≥5 chars E ganho previsto > 50B
3. **Escopo inicial**: so prefixo single. Multi-cluster e sufixo em
   tickets separados.

Implementacao estimada: ~80 linhas Python (lcp + emit + decode).

Lab `E-affix-real-datasets` (formal) ainda necessario antes de
incluir no Sprint 1+2 do v0.4. Este lab dirty so deu intuicao
matematica controlada — nao representa o mundo real.
