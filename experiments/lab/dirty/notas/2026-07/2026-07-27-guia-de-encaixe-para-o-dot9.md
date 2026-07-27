# Guia de encaixe para o `.9` — onde cada coisa nova entra, e onde ela poderia ser antecipada

> *"pra cada otimização, o que conseguimos fazer de forma automática, preditiva, especulativa,
> sem ter que esperar tudo pra começar? o que cada etapa dá de dica pra acionar antes? decidir
> antes? (…) é tipo um mapa de guia pra cada coisa que a gente mexa ver onde podemos encaixar.
> seja de forma remendada e rápida pra funcionar (que é o mais importante) e depois onde ele
> poderia ficar mais acelerado/especulativo/cacheado."*

Documento **vivo**. Complementa o mapa descritivo
([`2026-07-27-mapa-do-pipeline-e-o-que-falta-pro-float.md`](2026-07-27-mapa-do-pipeline-e-o-que-falta-pro-float.md)),
que diz *o que existe*. Este diz **onde encaixar** e **o que dá pra antecipar**.

---

## 0. Censo corrigido dos pontos de decisão

Eu tinha dito "7 FLOORs". Estava contando só quem compara bytes **finais**, e o `_best_of`
sozinho é **três** comparações sequenciais, não uma. O censo por categoria:

### A. FLOOR de bytes — decide comparando tamanho real (10)

| # | o que compete | onde | materializa os 2 lados? |
|---|---|---|:-:|
| A1 | seq-RLE × corpo canônico | `hcc_seqrle.py:329` | sim |
| A2 | nature single-col × baseline | `encoder.py:338` | sim |
| A3 | tipado: core × core+polaridade × denso b64 | `encoder.py:444` | sim |
| A4 | polaridade inicial `R` × `L` | `polaridade.py:160` | **não — conta** |
| A5 | polaridade × canônico (nunca-pior) | `polaridade.py:162` | **não — conta** |
| A6 | raw × tcf (multi) | `multi/core.py:425-427` | sim |
| A7 | dict V2-B × melhor até agora | `multi/core.py:428-430` | sim |
| A8 | split × melhor até agora | `multi/core.py:431-433` | sim |
| A9 | nature multi-col — **blob inteiro** | `multi/core.py:472-474` | sim |
| A10 | nature no `.8H` (detecta win pela presença do header) | `hierarchical.py:488-496` | sim |

**8 de 10 materializam os dois lados.** Só A4/A5 decidem por contagem — é a dívida que o `.9`
tem de atacar, e o próprio código já a registra (`encoder.py:404-405`).

### B. Decisão por ESTIMATIVA (proxy, não bytes) — 1

| # | o que | onde |
|---|---|---|
| B1 | HCC: argmax de `net = (R-1)*(baseline-n_tam)` com running-max e prune | `syntax.py:435-465` |

É o **único** lugar que já decide por preditor em vez de materializar. Serve de modelo.

### C. GATES de aplicabilidade — decide se sequer tenta (9)

| # | gate | onde | custo |
|---|---|---|---|
| C1 | `_fallback_safe` (raw) | `multi/core.py:424` | 1 passada |
| C2 | dict: cardinalidade > 8192 | `multi/dict_v2b.py:57-58` | 1 set |
| C3 | dict: `K < 2 or K >= N` | `multi/dict_v2b.py:61-62` | O(1) após C2 |
| C4 | split: `< 2` valores | `multi/split.py:33-34` | O(1) |
| C5 | split: `< 2` campos de dígito | `multi/split.py:34-35` | 1 valor |
| C6 | split: template não-uniforme (gate 100%) | `multi/split.py:40-41` | 1 passada |
| C7 | split: campos todos constantes | `multi/split.py:44-45` | 1 passada |
| C8 | polaridade: FAIXA inteira usada | `polaridade.py:159` | acumulador |
| C9 | pré-passe: `n_rows < 100` | `auto_min_len.py:56-57` | O(1) |

### D. HEURÍSTICAS de parâmetro — escolhem valor, não comparam bytes (3)

| # | o que | onde | natureza |
|---|---|---|---|
| D1 | `min_len` ∈ {3,4,5,6} — árvore de 8 ramos | `auto_min_len.py:56-75` | estatística (constantes calibradas) |
| D2 | cadência — 2 regras | `auto_cadence.py:67-96` | heurística (limiares 0.7 / 0.5) |
| D3 | `obat_shape` — replica o último shape | `obat_shape.py:36-65` | dinâmica (muda a cada string) |

### E. PODA dentro de algoritmo (6+)

HCC: prune por upper-bound (`syntax.py:437-441`), `R<2`, `virtual_count>1`, body-order,
parada quando ninguém lucra (`477-480`), cap de 99 (`522-523`). OBAT: teto e cota
(`core/online.py:125-126, 133-134, 152-153, 161-162`).

**Total: ~29 pontos de decisão**, não 7.

---

## 1. A tabela de encaixe

Para cada etapa: **o que dá de dica**, **quando dá pra decidir**, e as duas versões
(remendada / otimizada).

### Legenda do eixo "quando"

```
[stream]  dá pra decidir com os valores CHEGANDO, sem ver o fim
[k=N]     dá pra decidir depois de N valores, com risco de errar
[fim]     precisa da coluna inteira
[pós]     precisa do corpo já emitido
```

---

### 1.1 `analyze_column` — o perfil

| | |
|---|---|
| **hoje** | 1 passada O(N) no fim da coleta (`encoder.py:539`); roda **sempre**, mesmo com `pre_pass=False` |
| **dica que dá** | `is_numeric`, `cardinality`, `avg_len` — os 3 insumos de **todas** as heurísticas D1/D2 |
| **quando** | **[stream]** — todos os campos são acumuladores incrementais (contador, soma, set) |
| **remendado** | expor `ColumnFeatures.update(valor)` e alimentar valor a valor; o resultado final é idêntico |
| **otimizado** | `is_numeric` já usa só os **20 primeiros** (`column_features.py:78`) → um perfil **provisório** existe em k=20. Publicar isso como `features_parciais` destrava D1/D2 cedo |
| **risco** | `cardinality` é o campo que mais muda com n; decidir cedo por ele é o que exige o gate C9 |

### 1.2 `detect_cadence` — o detector mais precoce que existe

| | |
|---|---|
| **hoje** | usa as **5 primeiras únicas** (`auto_cadence.py:62`) |
| **dica que dá** | liga/desliga o `obat_shape` (D3) |
| **quando** | **[k=5]** — já é praticamente streaming |
| **remendado** | nada a fazer; já é barato |
| **otimizado** | usar o mesmo resultado como **dica de spec** (§3): cadência regra-1 = "máscara fixa", que é exatamente a assinatura de CPF/CNPJ/cartão |

**Este é o gancho mais barato do pipeline inteiro.** Já roda, já detecta forma fixa, e hoje
o resultado morre servindo só ao OBAT.

### 1.3 `min_len` — a heurística estatística

| | |
|---|---|
| **hoje** | árvore de 8 ramos sobre `(n_rows, avg_len, cardinality, is_numeric)` |
| **dica que dá** | parametriza o OBAT — que é **online** e **semeia o vocabulário com o primeiro valor** |
| **quando** | **[fim]** por causa de `n_rows`, mas o gate C9 (`n<100`) é decidível **[stream]** |
| **remendado** | assim que o contador passa de 100, o gate está aberto — não precisa esperar o fim para saber isso |
| **otimizado** | estimar em k≈100-200 e **rodar o OBAT especulativamente**; se a estimativa mudar, só aí refazer |
| **risco declarado** | mudar `min_len` no meio **invalida a tokenização** (o vocabulário já foi semeado). Medido na nota `2026-07-26-min-len-ganho-dinamico-e-custo.md`: 5× CPU. **É o obstáculo estrutural do OBAT ser online** |

### 1.4 OBAT — já é online

| | |
|---|---|
| **hoje** | tokenizer incremental; a 1ª string semeia o vocabulário (`core/online.py:202-248`) |
| **quando** | **[stream]** por construção |
| **otimizado** | o índice buckets por **trigrama fixo** (`s[:3]`) mesmo quando `min_len` é 4/5/6 — buckets mais largos que o necessário. Não medido |

### 1.5 HCC — o modelo a copiar

| | |
|---|---|
| **hoje** | greedy iterativo, 1 alias por rodada, com **prune por upper-bound** e running-max (B1) |
| **quando** | **[fim]** — precisa das pieces de todas as linhas |
| **por que importa** | é o único ponto que **decide sem materializar**: estima `net`, poda por cota superior, e só então paga o cálculo caro. **É o padrão que os 8 FLOORs de A deviam seguir** |

### 1.6 seq-RLE — janela de 2

| | |
|---|---|
| **hoje** | **[pós]** — re-parseia o texto já emitido (`find_escape_digit_runs`) |
| **dica que dá** | nada pra frente; é terminal |
| **quando** | a comparação é entre **linhas adjacentes** (`compare_for_seq`) — ou seja, **janela de 2** |
| **remendado** | nada |
| **otimizado** | rodar incremental conforme as linhas saem do `_emit_body`, com buffer de 2. Elimina a re-varredura completa **e** a re-parseação |
| **encaixe futuro** | se o `_emit_body` ganhasse camada de token de saída (hoje é `list[str]` puro), o seq-RLE leria o token em vez de reencontrar o `\` — dissolve o bloqueador registrado no ADR-0035 |

### 1.7 Polaridade — o único que já conta em vez de medir

| | |
|---|---|
| **hoje** | **[pós]** — 1 passada sobre o corpo pronto (`polaridade.py:98-137`) |
| **quando** | os 3 acumuladores (alfabeto, `trocas_R`, `trocas_L`) são **[stream]** por linha |
| **remendado** | já funciona e é nunca-pior |
| **otimizado** | fundir no laço que `syntax._escape_lit` **já roda** (`syntax.py:173-193`) — registrado como `T-POLARIDADE-FUSE`. **Zero mudança de byte**, elimina 1 passada |
| **especulativo** | a proporção escapes/transições estabiliza cedo → dá pra **prever o vencedor** antes do fim e emitir já polarizado |

### 1.8 Os FLOORs multi-col (A6-A8) — os gates são baratos, os candidatos não

| | |
|---|---|
| **hoje** | materializa `raw`, `dict` e `split` **inteiros**, compara |
| **dica que dá** | os gates C1-C7 são **todos avaliáveis numa passada sobre os valores**, antes de encodar |
| **quando** | gates **[stream]**; candidatos **[fim]** |
| **remendado** | rodar C1-C7 primeiro e só materializar quem passou. Ganho de CPU, **zero mudança de byte** |
| **otimizado** | preditor de tamanho por candidato (como o `net` do HCC) — materializar só o favorito e o atual |
| **cacheável** | `dict` e `split` recomputam a cardinalidade e o template que o perfil já tem |

### 1.9 Nature/spec (A2, A9, A10) — encoda a coluna duas vezes

| | |
|---|---|
| **hoje** | `encode_value` em **todos** os valores, encoda a coluna transformada **inteira**, compara |
| **dica que dá** | a transformação é **por valor e independente** |
| **quando** | **[k=N]** — se em 50 valores a nature não reduz, quase certamente não reduz em 5000 |
| **remendado** | decidir por **amostra** com margem de segurança, e materializar inteiro só o vencedor |
| **otimizado** | ver §3 (camadas do spec) |

---

## 2. O que é ordenável por dependência

O que trava o quê, para saber por onde começar:

```
[stream] features parciais (k=20)
    |
    +--> cadencia (k=5)  --> obat_shape          ja' rapido
    |         \
    |          +--------> DICA DE SPEC (§3)      NAO EXISTE
    |
    +--> min_len (k~100) --> OBAT                travado: OBAT e' online
    |
    +--> gates C1-C7     --> quais candidatos materializar    FACIL, so' reordenar
    |
    +--> alfabeto + trocas --> polaridade        FACIL, fundir no _escape_lit
                                    |
                              [pos] seq-RLE      janela de 2, incrementalizavel
```

**Os dois encaixes mais baratos e sem risco de byte**: reordenar gates antes de materializar
candidatos (§1.8) e fundir a varredura da polaridade (§1.7).

---

## 3. Specs em camadas — CPF como piloto

Hoje um spec é **uma coisa só**: `encode_value(v) -> (transformado, stats)` +
`decode_value`. É a camada de **agir**. Não existe camada de **reconhecer**, e é por isso
que o spec tem de ser passado à mão.

### O contrato proposto — 5 camadas

| camada | pergunta | custo | quando |
|---|---|---|---|
| **L0 — FORMA** | "tem a máscara?" | O(len), por valor | **[stream]** |
| **L1 — VALIDADE** | "o dígito verificador fecha?" | O(len), só se L0 passou | **[k=N]** amostral |
| **L2 — MOMENTO** | "já vi o bastante pra me comprometer?" | O(1), lê contadores | **[k=N]** |
| **L3 — AGIR** | transformar (é o que existe hoje) | O(N) | após L2 |
| **L4 — DESISTIR** | apareceu valor que não casa: e agora? | O(1) | **[stream]** |

### CPF como piloto — por que é o caso certo

- **L0 é trivial e exato**: `NNN.NNN.NNN-NN` — 14 chars, posições fixas. E a **cadência
  regra-1 já detecta isso hoje** (`auto_cadence.py:67-84`, lengths uniformes + LCP/LCS ≥ 0,7)
  — só que o resultado morre servindo ao OBAT. **A dica já existe e está sendo jogada fora.**
- **L1 é exato, não estatístico**: o DV fecha ou não fecha. Sem limiar arbitrário.
- **L2 tem número conhecido**: já medimos que uma coluna de CPF único não gera referência
  nenhuma (lab `2026-07-26-0200`) — o regime é identificável cedo.
- **L4 tem saída natural**: o FLOOR de hoje já é o fallback; a diferença é desistir **antes**
  de materializar, não depois.

### O que isso destrava, em ordem

1. **detecção automática de spec** — hoje inexistente (`schema.py:194` e
   `side_outputs.py:36-37` marcam como "Fase 3")
2. **decisão amostral** em vez de encodar a coluna duas vezes (§1.9)
3. **specs compostos** — L0/L1 separados permitem "é máscara de documento" sem saber qual

### Cuidado registrado

L1 no CPF **exige DV válido**, e a política do projeto é **nunca publicar CPF DV-válido**. Os
testes do piloto usam placeholders repetidos mod-11-válidos, como já se faz hoje.

---

## 4. O que NÃO dá pra antecipar (e por quê)

Honestidade sobre os limites — para não gastar tempo tentando:

| item | por que não |
|---|---|
| `min_len` dinâmico no meio da coluna | o OBAT é **online** e o vocabulário é semeado pelo 1º valor; mudar invalida a tokenização (5× CPU medido) |
| HCC antes do fim | precisa das pieces de **todas** as linhas para contar sub-tuplas repetidas |
| "matar" um candidato em voo | não há concorrência especulativa; o `parallel=` é data-parallel por coluna |
| tamanho final antes de emitir | só existe preditor no HCC (B1); os outros 8 FLOORs medem de fato |

---

## 5. Como usar este guia

Ao mexer em qualquer coisa nova, responder 4 perguntas:

1. **Em que categoria cai?** (A FLOOR / B estimativa / C gate / D heurística / E poda)
2. **Qual é o `[quando]`?** stream / k=N / fim / pós
3. **Qual a versão remendada** que funciona hoje sem mudar byte?
4. **Onde ficaria o preditor**, se um dia valer a pena?

A polaridade (ADR-0035) é o exemplo completo: entrou como **A4/A5 + C8**, `[pós]` na versão
remendada, com o `[stream]` já identificado (`T-POLARIDADE-FUSE`) e **nunca-pior por
construção** — que é o que permitiu soldar sem esperar a otimização.

---

## Pendências que este guia cria

- `T-POLARIDADE-FUSE` — fundir a varredura no `_escape_lit` (byte-neutro)
- `T-GATES-ANTES` — avaliar C1-C7 antes de materializar candidatos (byte-neutro)
- `T-SEQRLE-INCREMENTAL` — janela de 2 em vez de re-varredura (byte-neutro)
- `T-SPEC-L0L1` — camadas de reconhecimento, CPF piloto (**muda byte**: passa a detectar sozinho)
- `T-FEATURES-STREAM` — `ColumnFeatures` incremental + perfil parcial em k=20
- `T-OBAT-TRIGRAMA` — bucket por `min_len` em vez de 3 fixo (só CPU)
