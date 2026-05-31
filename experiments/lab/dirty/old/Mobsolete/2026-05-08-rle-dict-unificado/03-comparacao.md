# Comparação — regra unificada vs C11-híbrido

---

## Tabela mestre

| Estratégia | Bytes | Diferença |
|---|---|---|
| C1 (CSV) | 762 | — |
| C11-híbrido sort-(valor, produto, qty) | 348 | -54% |
| **Regra unificada sort-(valor, produto, qty)** | **342** | **-55%** |
| Cota teórica | ~100 | -87% |

Ganho da regra unificada sobre C11-híbrido: 6 B (~1.7%) neste dataset.

---

## Onde os 6 B vieram

Da coluna `produto`, especificamente da 2ª aparição de `Caderno`:

```
RLE puro (C11):              Regra unificada:
4*Caderno                    4*Caderno
2*Marcador                   2*Marcador
Caderno          ← 8B        6                ← 2B (ref a idx 6 = Caderno)
2*Mochila                    2*Mochila
```

O encoder unificado **detectou** que `Caderno` voltou e a 1ª aparição já
declarou idx 6, então emitir `6` (2 B) é mais curto que repetir `Caderno`
(8 B). Ganho: 6 B.

---

## Generalização — onde a regra unificada ganha mais

A magnitude do ganho depende de:

### 1. Quantos valores fragmentam após o sort

No nosso dataset, só `Caderno` fragmenta. Mais frequente em datasets
maiores com correlações imperfeitas. Cada fragmentação que volta como ref
economiza `len(valor) - digits(idx)` bytes (na melhor hipótese, com bare).

### 2. Tamanho dos valores que fragmentam

Caderno (`len=7`) vs idx 6 (`len=1`) → ganho 6 B por fragmentação.
Se fragmentasse "Apontador" (`len=9`) → ganho 8 B.
Se fragmentasse "Ana" (`len=3`) → ganho 2 B.

→ **Strings longas que fragmentam dão maior ganho.**

### 3. Tamanho do índice (número de digits)

idx 1-9: 1 dígito de ref → ganho máximo
idx 10-99: 2 dígitos → ganho 1 B menor
idx 100+: 3 dígitos → ganho 2 B menor

→ Em datasets de cardinalidade muito alta (centenas de valores únicos), o
ganho diminui mas continua positivo se `len(valor) > 3`.

---

## Onde C11-híbrido empata

Quando todas as ocorrências de cada valor único formam **um único bloco
contíguo**:

- Sort primário (sempre): cada valor único em 1 bloco. Empate.
- Colunas com cardinalidade extrema (poucas linhas, muitos únicos): cada
  valor 1× só, sem repetição. Empate (ambos = literal).
- Colunas onde o sort criou agrupamento perfeito por sorte. Empate.

---

## Onde C11-híbrido ainda VENCE (raros casos)

Em coluna onde:
- Refs precisam de marcador (`:N`)
- Cardinalidade é alta
- Valores são curtos

A regra unificada **deveria** decidir por linha que literal é melhor que
ref. Mas se o encoder for forçado a usar ref (por configuração ou bug),
perde para C11 que escolhia literal de cara.

→ Na prática, **a regra unificada bem implementada não perde** — ela faz a
mesma escolha que C11 faria, só que linha-a-linha em vez de coluna-a-coluna.
A vantagem é que captura ganhos extras quando há mistura.

---

## Critério de unificação

### A regra unificada substitui as 4 modalidades anteriores?

**Sim**, no sentido de que ela engloba todas. Os modos {literal, RLE, dict,
RLE+dict} viram **estados emergentes** da regra única, dependendo de:
- Quantas linhas têm run length > 1
- Quantas linhas referenciam idx anterior
- Domínio dos valores (bare ou marcado)

### Ainda precisa do header com modos por coluna?

**Provavelmente não.** O decoder consegue inferir tudo da estrutura:
- 1ª aparição de cada valor → declara idx
- `N*<v>` → run de literais (declara se 1ª)
- bare integer ou `:N` → ref (decoder descobre modo de discriminação pelo
  conteúdo da coluna na 1ª varredura)

O header com modos por coluna (`# enc: D, R, L, R`) **vira redundante**
porque o encoder não está mais escolhendo entre eles — ele aplica a regra
única e o resultado emerge.

O que o header AINDA pode declarar:
- `# encoding=v05-unified` (versão do formato, anti-ambiguidade futura)
- `# col qty discrim=marked` (modo bare/marcado por coluna, opcional)
- `# sort: valor, produto, qty` (ordem de sort aplicada — útil para cliente)

---

## Implicação para o formato TCF

A passagem por C11-híbrido foi instrutiva mas **a regra unificada é mais
elegante**. Sugere uma redefinição do "nível L" do TCF:

### v0.4 e antes
```
# TCF v0.4 lv=2     ← um nível para o arquivo (L0/L1/L2/L3)
```
- L0 = literal puro
- L1 = + RLE
- L2 = + sort + RLE
- L3 = + dict (separado)

### v0.5 com regra unificada
```
# TCF v0.5
# sort: valor, produto, qty
```
(sem `lv=`, sem `enc:`, regra única implícita)

A "compressão" não é mais um nível discreto — é a aplicação da regra única
sobre os dados na ordem decidida. O encoder pode fazer mais ou menos sort
(0 chaves = unordered, 1 chave = sort solo, 2-3 = multi-sort) — isso é o
único parâmetro relevante.

---

## Hipótese para validar em escala

> Em datasets grandes com cardinalidade média e algumas correlações
> parciais, a regra unificada captura ganhos extras de 1-5% sobre
> C11-híbrido por capturar fragmentações repetidas. O ganho cresce com:
> - Tamanho dos valores
> - Número de fragmentações
> - Diversidade dos blocos

→ Não calculado aqui — fica para experimento em TPC-H ou semelhante.
