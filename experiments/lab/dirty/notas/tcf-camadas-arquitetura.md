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

## L3 — bloco de OTIMIZAÇÕES (parâmetros), a testar em massa (NÃO concluído) — 2026-07-14

**[probatório, HIPÓTESE — não veredito]** Owner (reforço 2026-07-14): a multiplicidade explícita×deduzida
é **só UMA hipótese ilustrativa, uma entre várias condições primárias** — não o fenômeno único. O L3 é um
**bloco de otimizações** com **parâmetros** (inicialmente usáveis), cujos eixos incluem **latência, memória,
velocidade geral e compressão**. Nada aqui está fixado; tudo precisa de **teste em massa** antes de conclusão.

Primeira medição-piloto (1 lente, sintético, N pequeno) em
[`2026-07-14-2043-l3-multiplicidade-independencia`](../2026-07-14-2043-l3-multiplicidade-independencia/):
- **Sinal observado** (não conclusão): crossover por largura — estreito (K=1-2) a forma deduzida gastou
  menos bytes; largo (K≥4) a explícita gastou menos E deu independência. O "imposto" da coluna de count
  ficou pequeno/constante (~20 B) nesse experimento.
- **O que isto NÃO estabelece**: só variou 1 eixo (largura) × 1 métrica (bytes-pré-brotli), sintético, sem
  latência/memória/velocidade medidas, sem dado real, sem brotli a jusante. É um sinal, não um veredito.
- O default ATUAL do weld usa `#count` explícito — por ora, não porque esteja "provado ótimo".

**H-L3-OPT-BLOCK** (bloco de otimizações, DEIXAR PRO FIM): expor parâmetros de L3 (ex.: multiplicidade
explícita/deduzida; e outros a levantar) com eixos **latência × memória × velocidade × compressão**; medir
em massa; talvez `min()` por documento. `aberta`, confiança: Baixa. Multiplicidade = 1 item do bloco, não o
bloco. Não implementar agora (owner: fixar o óbvio primeiro, otimizações no final).

## Restrição de design — NÃO "soldar" demais (owner 2026-07-14)

**[dispositivo]** Reforço do owner ao fechar o weld: **otimização é baixa prioridade**; a **separação por
funcionalidade** importa mais que ter tudo ótimo agora. Regras:
- **Não "soldar" demais as peças** — se vamos otimizar depois, L1/L2/L3 devem ficar **desacopláveis**. O
  L3 (deduções: count, omit-closes, tabelão-vs-nível-aware) hoje está parcialmente embutido no L2 (encode);
  a dívida de desacoplá-lo num **passe separado opt-in** fica registrada pra `.9` — NÃO refatorar agora.
- **Cauteloso em mexer no core agora**: o weld está verde (flat byte-idêntico); mudanças de otimização
  esperam. O que fazemos agora é **fechar funcionalidade + fluxo**, não otimizar.
- **Discriminador = dica, não `if` rígido** (H-DISC-ACCEL-01): a modularidade que permitiria acelerar
  blocos por-forma (`H`/`M`/espaço) e o mimemagic externo deve ser **preservada**, mas **não implementada**
  agora. Só não fechar portas. Ver [char-registry §propósito duplo](tcf8-header-char-registry.md).
- **Sequência**: fechar os tickets de cada parte (pra não se perder) → **depois** teste em massa (até via
  shaper montando o dataset hierárquico — TPC-H `customer→orders→lineitem`).

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
