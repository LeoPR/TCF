# Levantamento: data está fechada? qual o próximo tipo? e a ordem por ROI

**2026-08-13** · pedido do owner: *"apenas levante… data parece concluído já. podemos ver o
próximo tipo… veja se tem a possibilidade de ver mais alguma coisa de núcleo ou alguma
hipótese que dê pra adiantar ou estudar agora, senão acho que podemos olhar para os números,
começando com algum como inteiro por exemplo. faça suas sugestões ou até mudança de ordem se
for o caso pra capturar oportunidades (ou tal ROI)."*

Tudo abaixo é medido. **A recomendação final muda a ordem** — e a razão é uma medição que eu
não esperava.

---

## 1. Data está concluída? **Sim, essencialmente** — e você tinha razão

Testei a folga que sobra nas 10 colunas de data reais do corpus, varrendo `min_len` com o
spec ativo:

| | agregado |
|---|---:|
| spec, `min_len` automático | 162.293 B |
| spec + melhor `min_len` da grade | 161.963 B |
| ganho | **0,2%** |

Sem o spec, a mesma varredura dava 1,19× a 1,39× em várias dessas colunas — **o spec já
captura o que o `min_len` capturaria**. As duas únicas que ainda ganham são justamente as que
o spec **não** pega: `retail-invoicedate` (datetime, 1,19×) e `receita-data-inicio`
(`YYYYMMDD`, 1,02×), que são o `T-DATA-GRAFIAS-IRMAS` já registrado.

**Correção de leitura minha**: cheguei a ver 1,39× em `football-date` e quase reportei data
como não-fechada. Aquilo era medição **sem spec** — que não é o caminho real.

## 2. Núcleo adiantável: existe, mas vale menos do que parecia

O `min_len` é escolhido por heurística **antes** de encodar e **não compete** — é a mesma
classe de "o candidato existe e a rota não consulta" que já apareceu 5 vezes no projeto.
Varrendo 101 colunas (sintéticas do repo + corpus real + regimes numéricos), uma grade de 4
candidatos bate o automático em **22 colunas (22%)**, com **9,1%** de economia no corpus.

**Mas esse número é enganoso**, e a checagem contra os specs mostra por quê:

| coluna | sem spec | com spec |
|---|---:|---:|
| datas reais (10 colunas) | 1,19–1,39× | **~1,00×** |
| CNPJ | 1,14× | **1,05×** |
| epoch/timestamp (sem spec algum) | **3,00×** | — |

Onde há spec, ele já colhe quase tudo. O que sobra de verdade: **3,00× em timestamp** e
1–5% em texto/CNPJ. Custo: 4,1× de CPU para uma grade de 4.

**Sugestão**: *não* abrir isto como item próprio agora. A maior parte do que ele pegaria é
justamente o que um tratamento de número resolveria melhor (o caso epoch é numérico). Fazer
os dois seria trabalho duplicado. Reavaliar depois, com a grade reduzida a 1–2 candidatos.

## 3. O próximo tipo: número — a folga, medida

Número **já é tipo nativo** (`stype='n'`), mas não tem pré-transformação nenhuma: vira string
e passa pelo core. A rota tipada custa **1 byte a mais** que a string, sem ganhar nada.

Duas alavancas, ambas com precedente soldado no projeto:

**(a) Largura variável quebra o marcador aritmético.** A mesma progressão, grafada diferente:

| coluna | como está | com zero-pad | ganho |
|---|---:|---:|---:|
| `1..600` | 36 B (3 marcadores) | **19 B** (1 marcador) | 1,9× |
| passo 7 | 48 B (4 marcadores) | **20 B** | 2,4× |
| passo 3 | 48 B | **20 B** | 2,4× |

`1..600` sai como `*9+1\|1` + `*90+1\|10` + `*501+1\|100` — o run quebra em cada mudança de
dígito (9→10, 99→100). É o mesmo fenômeno que a docstring do `data_iso` descreve para ISO
(*"2026-01-31 → 2026-02-01 não é '+1' em campo nenhum isolado"*). O `TemplatedPaddedSpec` (IP)
**já usa padding zero-leading exatamente para ativar o seq-RLE** — o precedente existe.

**(b) Aleatório de largura fixa não ganha nada hoje.** 600 IDs de 6 dígitos = 4.209 B contra
~4.200 B crus. O `TemplatedCheckedSpec` (CPF) já converte 11 dígitos em 5 chars BASE94 — a
mesma ideia daria ~2,3× aqui.

Onde **não** compensa (medido): moeda com centavos rende só 1,17×, e o padding **piora**
(0,82×); negativos com offset, 1,06× e o padding piora. Ou seja, as alavancas valem para
**progressão e largura fixa**, não para número em geral — o FLOOR decide.

## 4. A oportunidade maior está em M e H — e o mecanismo já existe

Esta é a medição que muda a ordem. Uma coluna sozinha × a **mesma** coluna dentro de tabela:

| coluna (600 valores) | sozinha | em `.8M` | em `.8H` |
|---|---:|---:|---:|
| **bool nativo** | 112 B | **12,79×** | **12,67×** |
| bool como string | 124 B | 5,01× | 10,73× |
| categoria (k=5) | 342 B | 1,87× | 5,12× |
| data | 414 B | 1,08× | 1,08× |
| inteiro sequencial | 37 B | 0,97× | 1,08× |
| texto | 68 B | 1,00× | 1,06× |

Data, inteiro e texto atravessam quase incólumes. **Baixa cardinalidade despenca**: o bool
sozinho vira bitpack denso (`#TCF.8b1`, 112 B para 600 valores) e dentro de tabela vira
1.433 B. O mecanismo existe, está soldado, e a rota multi não o consulta.

Numa tabela de cadastro realista — 10 colunas × 2000 linhas, com 5 flags booleanas, que é o
formato de qualquer sistema:

```
tabela inteira: 41.760 B
  as 5 flags, sozinhas:      1.740 B
  as 5 flags, na tabela:    12.428 B      (7,1×)
  uf (k=6), sozinha:         1.031 B
  uf, na tabela:             5.854 B      (5,7×)
soma dos custos marginais excedentes: 19.646 B = 47% da tabela
```

*(Ressalva metodológica: "na tabela" é custo marginal — `total − total_sem_a_coluna`. A soma
de marginais não é exatamente decomponível, então os 47% são indicativos, não um teto exato.
O padrão por coluna, esse, é inequívoco.)*

O `T-BN-MULTICOL` já registrava 13,8% para bN em multi-col. **A medição de hoje é muito
maior** — 5× a 12,8× em colunas de baixa cardinalidade — porque bool nativo e categoria são
casos que aquele ticket não cobria.

## 5. Sugestão de ordem (mudança)

**Antes eu recomendaria**: número → M → H.
**Agora recomendo o inverso**, e a razão é ROI por unidade de risco:

1. **Baixa cardinalidade em M/H** — 5× a 12,8× medidos, num padrão universal de dados
   tabulares (flags, status, UF). **Não exige inventar mecanismo**: o denso/bN já existe,
   soldado e testado; falta a rota multi consultá-lo. É a 6ª ocorrência da classe "o candidato
   existe e a rota não consulta", que no projeto tem histórico de ser barata e nunca-pior.
2. **Número** — 1,9× a 3,0× nos regimes de progressão e largura fixa. Exige spec novo
   (design + weld + pins), com dois precedentes prontos para copiar (padded do IP, base94 do
   CPF). O caso `epoch` sozinho (3,0×) já justifica.
3. **`T-DATA-GRAFIAS-IRMAS`** — fecha data de verdade: `YYYYMMDD` e datetime são 2 das 10
   colunas reais. Barato, é irmão do `data-iso` (o precedente CPF/CNPJ diz: uma grafia, um
   spec).
4. **Candidato `min_len`** — reavaliar **depois** de (2), com grade reduzida. Boa parte do
   que ele pega hoje é o que o número resolveria.

O item 1 é o único que entrega ganho grande sem mecanismo novo. Se a ideia é capturar
oportunidade por ROI, ele vem primeiro — e ainda tem a vantagem de forçar a olhada em M/H,
que é para onde você quer ir.

## O que não muda

Streaming/latência seguem como eixo ortogonal de `.9`/`2.0`, com os tickets já registrados e
o protótipo de leitor de prefixo servindo de enquadramento.
