# Inspecao CPF — 3 casos do fluxo (amostra 50) + dataset realista

`gerar_inspecao.py` gera CPFs sinteticos **realistas** (9o digito = Regiao Fiscal,
ponderado por populacao: 8=SP maior; serial uniforme; DV mod-11 valido) e produz a
amostra de 50 nos 3 casos pra inspecao. Dataset de 5000 em `cpfs-sinteticos-realistas.txt`.
Ressalva: serial uniforme e' simplificacao (real clusteriza por epoca de emissao); nao
afeta o eixo de compressao (aleatorio de qualquer jeito).

## Os 3 casos (mesmos 50 CPFs)
- **caso1-raw.tcf.txt**: sem nature — CPF mascarado pelo pipeline (`\526.\018.\157-\36`).
- **caso2-base94.tcf.txt**: nature atual — `#TCF.8 :cpf` + base94 denso (5 chars, DV dropado).
  (= modo no-obat/bypass; mesmos bytes.)
- **caso3-digitos.tcf.txt**: modo-1 (normalizar p/ OBAT) — 9 digitos sem mascara/DV.
- **caso3b-digitos-cadenciado.tcf.txt**: ILUSTRATIVO (CPFs sequenciais, NAO realista) —
  mostra o seq-RLE ganhando.

## Tamanhos (single-col; brotli = regua p/ 1-coluna-SEM-lazy)
| caso | textual | brotli |
|---|---|---|
| 1 raw | 944 | 408 |
| 2 base94 | **354** | 283 |
| 3 digitos | 595 | **279** |
| 3b cadenciado (ilustr) | 41 | — |

## Achados da inspecao
1. **seq-RLE ESPURIO no aleatorio**: o caso3 (digitos) dispara `*2+<delta-largura-cheia>|`
   em pares consecutivos aleatorios -> INFLA (595 > base94 354). O seq-RLE so' ganha com
   delta PEQUENO (cadencia real): caso3b = 41 bytes (`*8+1|`, `*40+1|`). Explica
   visualmente por que CPF (aleatorio) -> base94, e onde o modo-1 ganha (sequencial).
2. **Sob brotli, base94 ~ digitos** (283 vs 279): a DENSIDADE do base94 NAO ajuda o brotli
   (ja' e' denso/incompressivel); o digito da redundancia pro brotli comprimir. Os dois
   chegam perto da entropia do numero. **A DV-drop e' o ganho compartilhado real; base94 vs
   digitos so' importa no regime TEXTUAL/lazy (354 vs 595), nao sob brotli.**

## Decisao (regua brotli do owner)
- **TCF-nativo / textual / lazy / inspecionavel**: base94 (mais denso textual).
- **Consumidor-brotli (1 coluna, sem lazy)**: base94 ~ normalizar (wash). A densificacao
  do base94 nao paga sob brotli -> normalizar (dropar mascara+DV) e' inspecionavel E
  brotli-competitivo. So' a DV-drop e' decisiva nos dois.
