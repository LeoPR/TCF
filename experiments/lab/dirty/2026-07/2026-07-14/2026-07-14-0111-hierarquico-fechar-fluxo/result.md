# Resultado — funcionalidade + fluxo do hierárquico FECHADOS

**[probatório]** `run.py` valida os dois fluxos antes dos bytes. Contra-prova:
[`outputs/11-contraprova.txt`](outputs/11-contraprova.txt); roundtrips `.json` byte-idênticos
aos canônicos de `intermediates/`. Sintético, viés declarado
([datasets-provenance.md](datasets-provenance.md)).

## O que fechou

1. **Codec por shredding (blocos + counts)** faz RT-exato nos clássicos de transmissão:
   cadastro (2 listas irmãs + endereco{geo} 1:1), pedidos (aninhado + vazio), telemetria
   (sensores{} 1:1 + série). Fecha o que o tabelão integrado NÃO fechava (múltiplas listas,
   ambiguidade de chave, arrays vazios).
2. **Os dois fluxos RT-exatos**: (A) funcional encode/decode; (B) transmissão simulada
   encode→gzip/brotli→gunzip/unbrotli→decode. Performance por proxy (a API real é `.9`).
3. **Multiplicidade 1× (nível-aware)**: as colunas-pai não repetem; a multiplicidade vive nos
   `#count`. Generaliza a peça 9 / lab 2356 recursivamente e resolve a ambiguidade (count escrito).

## Bytes (transmissão simulada; FORMA, não gate)

| entrada | JSON | TCF.H | +gzip | +brotli | JSON+br |
|---|---:|---:|---:|---:|---:|
| cadastro | 842 | **520** | 379 | 362 | 330 |
| pedidos | 635 | **328** | 270 | 246 | 255 |
| telemetria | 698 | **314** | 231 | 204 | 196 |

TCF.H cru ~40–55% < JSON; sob brotli empata/perde por poucos bytes em payload minúsculo (a
vantagem aparece com volume — o gate de performance é `.9`, não este lab).

## Estado

- **É**: funcionalidade + fluxo encode/decode do hierárquico FECHADOS para os clássicos de
  transmissão, com blocos+counts, RT-exato, dois fluxos.
- **Falta p/ firmar (weld)**: ragged/presença (máscara def-level, peça 11); N raízes; reconciliar
  gramática com ADR-0031 (sem-espaço, hex); gate real-world + performance (`.9`); tipos (ortogonal).

`confianca: Média` (sintético, N=1 lab, medida de forma/funcionalidade).
