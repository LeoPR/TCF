---
title: TCF em 3 camadas — compressor de colunas · relacionamento · otimização [dispositivo]
type: explanation
status: aberta
created: 2026-07-14
related:
  - tickets/T-CODE-TCF8H-WELD.md
  - experiments/lab/dirty/notas/hierarquia-inventario-hipoteses.md
  - experiments/lab/dirty/notas/teoria-cardinalidade.md
  - experiments/lab/dirty/2026-07-14-0111-hierarquico-fechar-fluxo/
---

# TCF em 3 camadas (reframe do owner, 2026-07-14)

**[dispositivo]** Insight do owner: TCF se separa em **três camadas** que devem ficar
**desacopladas** no código e só então **otimizadas entre si** (pra comprimir mais E manter
performance/paralelismo).

```
  L1 · COMPRESSOR DE COLUNAS   (o mesmo para single / multi / hierarquia / multi-tabela)
        │  OBAT + HCC + @dict + RLE + seq-RLE. Recebe uma LISTA de strings, devolve um corpo.
        │  NÃO sabe nada de relacionamento. É o `tcf.encode`/`decode` de coluna que já existe.
        ▼
  L2 · RELACIONAMENTO ENTRE COLUNAS   (a "natureza" do vínculo: multi-col, hierarquia,
        │  ragged, N:N, multi-tabela). Vive no HEADER. **Só a descrição do relacionamento
        │  no header já reconstrói o dataset** — INDEPENDENTE de como as colunas foram
        │  comprimidas. É o análogo do cross-dict: um mecanismo pra as colunas "conversarem".
        ▼
  L3 · OTIMIZAÇÃO PELO RELACIONAMENTO   (deduzir p/ economizar bytes). Ex.: a hierarquia
           permite deduzir a multiplicidade (count), omitir sizes/closes, escolher a projeção
           (tabelão vs nível-aware), fatorar afixo/dict entre ramos. É OPCIONAL: tirar L3 e o
           dataset ainda reconstrói (só maior).
```

## As 3 afirmações do owner (dispositivas)

1. **O processamento de colunas é o MESMO** — independe de single-col, multi-col, hierarquia ou
   tabelas. Essa parte não muda.
2. **O que muda é o mecanismo que CONVERSA entre as colunas** (como o cross-dict fazia). Ter
   hierarquia é **meramente um artifício que permite as colunas conversarem** pra otimizar. Ter só
   a **descrição da hierarquia no header** já reconstrói o dataset hierárquico, **independente da
   forma que as colunas são comprimidas**. O mesmo vale para ragged e multi-tabela.
3. Logo o que temos é: **(L1) compressor de colunas** + **(L2) um relacionamento entre colunas de
   alguma natureza** (ragged, hierarquia, N:N…) + **(L3) tirar vantagem desse relacionamento pra
   deduzir e economizar bytes**.

## Revisão: a distinção NO CÓDIGO (estado atual)

| camada | onde está hoje (lab `2026-07-14-0111`) | separada? |
|---|---|---|
| **L1 compressor** | as chamadas `tcf_encode(coluna)` / `tcf_decode(body)` — o motor `src/tcf` intacto | ✅ SIM — o hierárquico NUNCA toca o compressor; só passa listas |
| **L2 relacionamento** | `derive_schema` (topologia) + `_build_meta`/`_parse_meta` (header com `{}`/`[]`/`#count`) + `_emit_*`/`_read_object` (shred/reconstrói) | ✅ SIM — vive todo no header + walk; o header sozinho basta pra reconstruir |
| **L3 otimização** | os `#count` (multiplicidade 1×), última-folha-sem-size, omit-closes, o RLE de pai que "cai de graça" do L1 | ⚠️ PARCIAL — misturada no meio do L2; deveria ser um passe separado |

**Conclusão da revisão**: L1 já está limpo (o hierárquico é 100% cliente do compressor, zero
acoplamento — é por isso que `encode+gzip+decode` fecha sem tocar o core). L2 está coeso. **L3 é
o que falta desacoplar**: hoje as deduções (count, omit-closes, escolha tabelão-vs-nível-aware)
estão embutidas no encode; deveriam ser um **passe de otimização** sobre um L2 "cru" — assim dá
pra ligar/desligar, medir cada uma, e paralelizar L1 por coluna independente de L2/L3.

## Corolário — multi-tabela como SUPER-hierarquia (hipótese do owner, REGISTRAR, não fazer ainda)

**H-HIER-MULTITABELA-01**: o header pode aninhar MAIS DE UM TCF — não só hierarquia/multi-col, mas
**multi-tabelas**. "Embutir" todas as colunas e tornar as multi-tabelas **implícitas** como uma
super-hierarquia. Ragged e N:N seriam casos disso. — É a mesma L2 generalizada: o relacionamento
deixa de ser só contenção (árvore) e passa a expressar FK/junção (grafo). Já mapeado no inventário
como o limite "snowflake/N:N = FK, não contenção" (H-SNOW-*/H-HET-SNOWFLAKE-FK). **Alternativas a
ver depois**; agora só registrado. `aberta`, confiança: Baixa.

## Implicação pro WELD (T-CODE-TCF8H-WELD)

O weld deve **respeitar as 3 camadas**: (L1) reusar o `encode`/`decode` de coluna do core SEM
mudá-lo; (L2) o hierárquico é um MÓDULO NOVO que só descreve/reconstrói o relacionamento via header;
(L3) as deduções são um passe separado, opt-in. Isso torna o weld **aditivo e de baixo risco** (o
flat fica byte-idêntico; o hierárquico é um cliente do compressor + um dispatch por `H`). É a razão
de o codec `shred.py` já rodar sem tocar `src/tcf`.
