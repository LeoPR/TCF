# Tipos como specs — o espectro único (reframe do owner, 2026-07-06) [probatório→conceitual]

**Origem**: owner 2026-07-06, sobre o resultado dos tipos (Ciclos 1a/1b). Lab que mede:
[`2026-07-06-2310-tipos-como-specs/`](../2026-07-06-2310-tipos-como-specs/result.md).
Amarra: [H-TYPE-01](roadmap-hipoteses.md), [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md),
natures (ADR-0015), [checklist C1/C2/C4](tcf8h-header-checklist.md).
**Meta-grupo de hipóteses de tipo + taxonomia QUANDO (entrada/processo/pós-HCC) + design de fluxo/header**:
[tipos-meta-grupo-fluxo.md](tipos-meta-grupo-fluxo.md) (H-TYPE-00..04; bN = irmão bit-packed do dict).

## CONSOLIDAÇÃO E CORREÇÃO (2026-07-07) — leia isto primeiro

> Antes de consolidar o espectro de specs, pesquisei se bit-width/bitmap já tinha sido discutido/testado
> antes desta sessão (pedido do owner). Achado: **não é território novo além do que construímos nesta
> própria sessão** — mas existem 3 peças de prior-art genuíno e anterior que mudam a leitura dos números.
> Verificado por workflow (síntese + 3 críticos adversariais independentes: precisão numérica, atribuição
> de prior-art, gate `confirmada-empirica` do CLAUDE.md) — os 3 aprovaram a substância; as correções de
> redação abaixo já foram aplicadas.

### 1. Resumo executivo

Esta sessão (2026-07-06/07) explorou, no protótipo TCF.8H (fora de `src/tcf`), um espectro de specs para
tipos/enum/bool: fallback-string na base, subindo pra int/float/hex-subspec, depois enum/bool via
bit-packing por largura (família `bN`: `b`/`b2`/`b4`/`b8`), até nature rica no topo. A regra de indução é
round-trip (a spec só se aplica se decodifica byte-idêntico); o gabarito é propõe-e-confirma; há 8 eixos
ortogonais de caracterização (compressão, aceleração, autoridade, normalizabilidade, fechamento-de-domínio,
variante, reversibilidade, validação/sanidade).

Dois problemas foram identificados e corrigidos nesta revisão, e ficam registrados aqui de forma
proeminente porque alteram a leitura do resultado:

- **Correção 1 (baseline errado)**: os três labs de bit-packing compararam contra `tcf.encode(list[str])`
  (path single-column), que ignora o parâmetro `fallback`. O baseline correto é
  `encode({col: vals}, fallback=True)` (multi-coluna), que já aciona **V2-B** — o dicionário categórico,
  **já weldado em produção** ([ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md)).
  Contra o baseline correto, o ganho de bit-packing cai de forma acentuada mas continua existindo e é
  teoricamente limpo: razão aproximada `8/w` bits por item quando V2-B custa ~1 byte/linha.
- **Correção 2 (colapso sob brotli)**: aplicando brotli quality=11 sobre os dois lados, o ganho pré-brotli
  (2× a 8×) colapsa para 1.01×-1.33×. O brotli, como compressor de entropia geral, já captura quase toda a
  redundância que o bit-packing bit-level também captura.

O enquadramento correto NÃO é descarte do trabalho, e sim **aprofundamento de prior-art já registrado**
(seção 6): a família `bN` é uma ideia real, com ganho real e teoricamente limpo contra o baseline correto,
mas redundante com o que o brotli já encontra sozinho a jusante. O nicho honesto é TCF como representação
**terminal** (sem re-compressão posterior) — exatamente o território que a filosofia do projeto já reserva
pra V2-L ("não compete com gzip/brotli/zstd"). Pelo checklist de 5 perguntas do CLAUDE.md (real-world
testado, N≥5 fontes, sintético vs real, viés declarado, bytes absolutos relevantes), com N<5 fontes reais
(3 DBs: adult, tpch, receita) e o gate brotli reprovado na forma testada, o veredito é **confirmada-empírica
com ressalva** — não confirmada-empírica plena.

### 2. O espectro de specs consolidado

O trabalho da sessão reframa "tipos" como **specs induzidas por round-trip**, não como um sistema de tipos
declarado a priori. A escada, da mais genérica à mais específica:

1. **String fallback** — nenhuma estrutura assumida; base sempre disponível e sempre correta (round-trip
   trivial).
2. **int/float/hex-subspec** — spec numérica, válida apenas se todo o domínio observado faz parse e
   reconstrói o literal original byte-a-byte (cuidado com zeros à esquerda, notação científica, hex
   maiúsculo/minúsculo).
3. **enum/bool-bN** — spec de domínio fechado de baixa cardinalidade, com o domínio embutido como
   referência (não um catálogo externo) e emissão por largura de bits conforme k (ver seção 3).
4. **Nature rica** — specs semânticas (CPF, CNPJ, IP, etc.), opt-in, com validação/normalização próprias
   (ADR-0015).

A **regra de indução** é round-trip: uma spec só é aplicável a uma coluna se, para TODO o domínio
observado, encode seguido de decode reproduz o byte original. Isso descarta specs "quase certas" (ex.: int
que falha em um valor com zero à esquerda) sem exigir heurística adicional — o teste é binário e barato.

O **gabarito operacional** é propõe-e-confirma: uma etapa de análise propõe a spec mais específica
compatível com as amostras vistas; uma etapa de confirmação roda o round-trip completo sobre o domínio
antes de comprometer o encode a essa spec. Se a confirmação falha, recua pra spec anterior na escada (nunca
pra uma spec mais específica sem confirmar).

Os **8 eixos ortogonais** usados pra caracterizar cada spec (nenhum implica os outros):

| Eixo | O que descreve |
|---|---|
| Compressão | quanto a spec reduz bytes vs a spec anterior na escada |
| Aceleração | se a spec permite pular trabalho no encode/decode (ex.: bitshift vs parse de string) |
| Autoridade | se a spec é a fonte do valor ou só uma representação alternativa dele |
| Normalizabilidade | se a spec pode canonicalizar variantes (ex.: `01` vs `1`) sem perder informação |
| Fechamento-de-domínio | se o conjunto de valores possíveis é finito e conhecido a priori (enum) ou aberto |
| Variante | se a spec tolera formatos de entrada distintos pro mesmo valor lógico |
| Reversibilidade | se `decode(encode(x)) == x` é garantido byte-a-byte (round-trip) |
| Validação/sanidade | se a spec pode sinalizar dado inválido sem tentar corrigi-lo (alinhado à filosofia "só detecta, nunca arruma") |

Um achado empírico relevante desta linha: "boolean" quase não existe como tipo primitivo em dado real — é
quase sempre um enum-k com superfície igual ao dado bruto (ex.: `matriz_filial` em 1/2, não 0/1). Isso
motivou tratar bool como caso k≤2 da família enum/bN, em vez de spec separada.

### 3. A família bN (b/b2/b4/b8)

A família `bN` é o motor de bit-packing por largura de bits, indexado pela cardinalidade `k` observada da
coluna (número de valores distintos no domínio):

| Nome | Largura (w) | Itens/byte | Faixa de k |
|---|---|---|---|
| `b` | 1 bit | 8 | k ≤ 2 |
| `b2` | 2 bits | 4 | k ≤ 4 |
| `b4` | 4 bits | 2 | k ≤ 16 |
| `b8` | 8 bits | 1 | k ≤ 256 |

O princípio: em vez de emitir o domínio como um catálogo externo (dicionário com header próprio), o domínio
é **embutido como referência** direto no fluxo — os valores distintos observados viram índices implícitos
(0, 1, 2, …) na ordem de primeira aparição, e cada linha subsequente vira apenas `w` bits apontando pro
índice. Isso reusa o mesmo princípio de referência por posição que o HCC já usa pra refs atômicos/virtuais,
aplicado agora no nível de bits em vez de caracteres.

Duas variantes de formato foram exploradas pra materializar isso:

- **Formato A (streaming)**: reusa o próprio fluxo de referências que o HCC já produz durante uma passada
  única — o bit-packing é um passo posterior sobre índices já calculados, sem exigir nova varredura do dado.
- **Formato B (2 passadas)**: primeira passada determina o domínio e a cardinalidade k (e portanto qual
  `bN` se aplica); segunda passada emite os bits. Mais simples de raciocinar, custo de uma segunda varredura.

Quando o domínio tem exatamente 2 valores textuais com afixo comum (ex.: `male`/`female`), o motor pode
representar o domínio de forma comprimida por afixo (`fe`+ref) antes mesmo do bit-packing por linha — mas o
ganho principal é sempre o bit-packing por linha, não a codificação do domínio em si (O(k), desprezível
pra N grande).

### 4. CORREÇÃO 1 — baseline errado (single-col vs multi-col+fallback=True/V2-B)

Os três labs desta sessão (`2026-07-06-2332-boolean-spec-datasets`, `2026-07-06-2354-spec-bin-motor`,
`2026-07-07-0028-spec-bitwidth-bN`) mediram o bit-packing contra `tcf.encode(list[str])` — o path
**single-column**. Esse path ignora o parâmetro `fallback` (a própria docstring de `encoder.py` documenta:
pra `list` (single-col), o parâmetro é ignorado). O `fallback=True` só se aplica no path **multi-coluna**
(`encode({col: vals}, fallback=True)`), que é o default desde 0.7/ADR-0024 e é o que aciona **V2-B** — o
dicionário categórico já weldado em produção (ADR-0025).

Em outras palavras: os três labs compararam contra uma baseline que o usuário do TCF não usa por default.
Isso inflou artificialmente os ganhos reportados (o HCC puro, sem V2-B, não tem mecanismo de dicionário
categórico eficiente pra baixa cardinalidade — é precisamente o ponto cego já documentado em ADR-0018, ver
seção 6).

Contra o baseline correto (V2-B via `encode({col: vals}, fallback=True)`), os números pré-brotli são:

| Coluna | N | k | w (bits) | V2-B atual (bytes) | bit-pack (bytes) | ganho |
|---|---|---|---|---|---|---|
| adult.sex | 48842 | 2 | 1 | 48870 | 6117 | 7.99x |
| adult.class | 48842 | 2 | 1 | 48872 | 6117 | 7.99x |
| adult.race | 48842 | 5 | 4 | 48916 | 24477 | 2.00x |
| adult.relationship | 48842 | 6 | 4 | 48930 | 24483 | 2.00x |
| adult.marital-status | 48842 | 7 | 4 | 48952 | 24503 | 2.00x |
| adult.workclass | 48842 | 9 | 4 | 48954 | 24510 | 2.00x |
| adult.occupation | 48842 | 15 | 4 | 49070 | 24624 | 1.99x |
| adult.education | 48842 | 16 | 4 | 49003 | 24558 | 2.00x |
| lineitem.l_returnflag | 60175 | 3 | 2 | 60206 | 15050 | 4.00x |
| orders.o_orderstatus | 15000 | 3 | 2 | 15032 | 3756 | 4.00x |
| lineitem.l_linestatus | 60175 | 2 | 1 | 48499 | 7526 | 6.44x |
| estabelecimentos.matriz_filial | 200000 | 2 | 1 | 71897 | 25008 | 2.87x |

O padrão teórico é limpo: a razão pré-brotli é aproximadamente `8/w` quando V2-B custa ~1 byte/linha (caso
comum das colunas `adult`/`tpch` acima) — w=1 → ~8×, w=2 → ~4×, w=4 → ~2×. Os dois desvios (`l_linestatus`
6.44× em vez de ~8×, e `matriz_filial` 2.87× em vez de ~8×) têm explicação: são dados reais já
ordenados/agrupados, onde o HCC-RLE nativo já captura parte do ganho antes mesmo do bit-pack entrar em cena
— reduzindo a vantagem marginal do bN sobre o V2-B nesses casos específicos.

Este ganho pré-brotli, isolado, é real e teoricamente bem-explicado. A questão que a Correção 2 levanta é
se esse ganho sobrevive quando o output do TCF é re-comprimido a jusante — o que é o uso comum de qualquer
formato textual em produção.

### 5. CORREÇÃO 2 — colapso sob brotli

Aplicando brotli quality=11 sobre ambos os lados — V2-B atual e bit-pack — em quatro colunas reais cobrindo
larguras distintas (w=1, w=2, w=4×2), o resultado é:

| Coluna | w | V2-B + brotli (bytes) | bit-pack + brotli (bytes) | ganho pré-brotli | ganho pós-brotli |
|---|---|---|---|---|---|
| adult.sex | 1 | 6169 | 5715 | 7.99x | 1.08x |
| orders.o_orderstatus | 2 | 2933 | 2209 | 4.00x | 1.33x |
| adult.race | 4 | 6423 | 5473 | 2.00x | 1.17x |
| adult.education | 4 | 18374 | 18214 | 2.00x | 1.01x (basicamente zero) |

O ganho pré-brotli (2× a 8×) colapsa quase inteiramente pra faixa 1.01×-1.33× pós-brotli. Isso não é um
resultado negativo isolado a se descartar — é a confirmação empírica, com números reais, de uma
preocupação **já registrada antes desta sessão** em H-REF-05 ("isso encosta em entropy-coding e tende a
sumir sob brotli", ver seção 6) — a hipótese original é qualitativa (sem números ou faixas específicas); o
que esta sessão adiciona é a medição que confirma o caveat, não o caveat em si. O brotli, sendo um
compressor de entropia geral, já encontra quase toda a redundância que o V2-B (indexação base-94,
character-level) deixa na mesa; o bit-packing (bit-level) opera no mesmo espaço de redundância e por isso
adiciona pouco quando há um compressor de entropia geral rodando depois. O mesmo padrão — ganho que não
sobrevive ao brotli a jusante, por mecanismo distinto (afixo inter-item em vez de dicionário de baixa
cardinalidade) — está registrado como preocupação aberta em H-CARD-07.

**Reinterpretação correta do escopo de uso**: isso não invalida a família bN como ideia; delimita onde ela
se aplica. O ganho de bN é real quando TCF é a **representação terminal** — ou seja, quando o `.tcf`
produzido é o artefato final (armazenamento, transmissão, leitura direta), sem uma etapa de re-compressão
binária genérica a jusante. Nesse cenário, não há brotli/gzip/zstd pra "engolir" a redundância que o
bit-pack capturou, e o ganho de 2×-8× se mantém integral. Esse é precisamente o nicho que a própria
filosofia do projeto já reserva pra V2-L: "TCF não compete com compressores binários (gzip, brotli, zstd) —
esses ocupam áreas cinzas (denso, opaco, exige descompressão pra ler). TCF ocupa áreas explicáveis"
(CLAUDE.md, filosofia de design). O colapso sob brotli, portanto, não é uma derrota da ideia — é a
demonstração de que o caso de uso de bN é o mesmo caso de uso já declarado pra V2-L, e não um caso de uso
genérico de "substituto de compressor binário".

### 6. Prior-art genuíno (anterior a esta sessão)

O enquadramento correto deste trabalho é **aprofundar o que já existia**, não inaugurar um problema novo.
Três peças de prior-art, todas anteriores a esta sessão, já cobriam partes substanciais do terreno:

**ADR-0018 (V2-L, guarda-chuva de binarização, accepted, 2026-05-27)** —
[`docs/adr/0018-v2-format-roadmap.md`](../../../../docs/adr/0018-v2-format-roadmap.md) já define a camada
V2-L ("Binarização em camadas, Parquet-like, INTERNO ao TCF") como conceito guarda-chuva: "HCC body
binarizado: marcadores RLE/seq-RLE/refs em bytes packed em vez de ASCII... Header textual mantido (pra
inspeção + roteamento)... NÃO é compressor binário genérico". O mesmo ADR, na seção de contexto (lab
`2026-05-27-naturezas-reais-uci`), já documenta o **ponto cego de baixa-cardinalidade**: "TCF tem ponto
cego de baixa-cardinalidade: colunas numéricas curtas e repetitivas inflam até 2.3x (ex.: beijing `hour`,
24 únicos → 228.8%). Toggles (PipelineConfig) não corrigem — é o núcleo OBAT+HCC." Esse achado — o MESMO
problema de baixa cardinalidade que motivou a família bN, medido em dataset real (UCI beijing-pm25), com
número de inflação explícito — é anterior a esta sessão (ADR de 2026-05-27, quase seis semanas antes por
calendário). O trabalho de bN se encaixaria dentro deste guarda-chuva, se fosse weldado; não o inaugura.

**ADR-0025 (V2-B já weldado, é o baseline correto)** —
[`docs/adr/0025-v2b-dictionary-categorical-weld.md`](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md)
documenta que o dicionário categórico (V2-B) já está weldado em produção, não é roadmap: "Weld V2-B como 3º
candidato do fallback per-coluna: `min(tcf, raw, v2b)`... default True". Caracterizado em 8 datasets reais,
round-trip 42/42 OK, 13.9% weighted. Índice em base-94 (character-level), largura escala com cardinalidade
K. Este é precisamente **a solução já existente** pro ponto cego de baixa-cardinalidade citado acima — e
portanto o baseline correto contra o qual bN deveria ter sido medido desde o início (Correção 1).

**H-REF-05 (a hipótese que já previa o caveat do brotli)** —
[`dict-referencia-hipoteses.md`](dict-referencia-hipoteses.md) (2026-06-19) registra, como hipótese aberta
e explicitamente de prioridade baixa: "Índice de largura mínima / curto pros frequentes. O índice escala
com a cardinalidade (V2-B já faz base-94 width). Levar adiante: width mínima + (opcional) códigos curtos
pros atoms mais frequentes. CUIDADO: isso encosta em entropy-coding e tende a sumir sob brotli — só com
gate explícito; provavelmente o de menor prioridade." Isto é precisamente a ideia de largura mínima por
cardinalidade (ainda que em espírito char-level/base-94 generalizado, não bit-level puro) — registrada
quase 3 semanas antes desta sessão, cujo caveat qualitativo sobre brotli se confirma empiricamente nesta
sessão (seção 5), ainda que a hipótese original não trouxesse números ou faixas específicas.

Em resumo: o guarda-chuva (V2-L), o baseline correto (V2-B) e o caveat de risco (H-REF-05) já estavam todos
registrados. O trabalho desta sessão contribui a generalização por largura de bits (b/b2/b4/b8) e a medição
empírica que confirma o caveat — não a identificação do problema nem do risco.

### 7. Onde isso deixa o trabalho

**O que ainda vale, com ressalva**: a razão teórica 8/w do bit-packing contra o baseline correto (V2-B) é
limpa e reproduzível nas 12 colunas medidas (seção 4). Como spec dentro do espectro (seção 2), `bN` é um
caso válido e bem-fundamentado de enum/bool de baixa cardinalidade. A ressalva é de escopo: o ganho só se
sustenta integralmente quando o `.tcf` é consumido como representação terminal — sem brotli/gzip/zstd a
jusante. Sob re-compressão geral, o ganho adicional sobre V2-B cai pra 1.01×-1.33× (seção 5), o que em
termos de proporção (não microbytes) é marginal.

**O que NÃO se sustenta**: declarar `bN` como welding candidate genérico pro pipeline canonical
(`src/tcf/`) nesta forma. Pelo checklist de 5 perguntas do CLAUDE.md: (1) real-world testado — sim, mas
(2) N≥5 fontes de dados diferentes — não, são apenas 3 DBs (adult-census, tpch, receita-cnpj), N<5; (3)
sintético vs real — não se aplica (todas as medições são real-world), mas isso não supre o requisito de
N≥5 fontes; (4) viés declarado — não há dataset sintético nesta rodada; (5) bytes absolutos relevantes
(≥5% weighted real-world) — não medido em escala de corpus completo, só coluna a coluna. Por isso o
veredito é **confirmada-empírica com ressalva**, nunca confirmada-empírica plena — e a ressalva central é
dupla: escopo (terminal, sem re-compressão) e cobertura de fontes (N<5).

**O que fica aberto**:
- Testar bN contra V2-B em ≥5 fontes reais distintas (incluir UCI beijing-pm25, já citado no ponto cego de
  ADR-0018, e outro dataset fora do conjunto adult/tpch/receita) antes de qualquer proposta de weld.
- Decidir, como questão de produto/arquitetura e não de algoritmo, se o cenário "TCF como representação
  terminal sem re-compressão a jusante" é realista o suficiente no uso pretendido do projeto pra justificar
  a complexidade adicional de bN dentro de V2-L — decisão de escopo, não algo que os números respondem sozinhos.
- Cross-referenciar com H-CARD-07 (mesmo padrão de colapso sob brotli, mecanismo diferente: afixo
  inter-item em vez de dicionário de baixa cardinalidade) — as duas hipóteses compartilham a mesma pergunta
  de fundo e poderiam ser avaliadas em conjunto.
- H-TYPE-02 e H-REF-05 registradas/atualizadas no roadmap (ver `roadmap-hipoteses.md` e
  `dict-referencia-hipoteses.md`).

### Correções aplicadas nos 3 labs afetados

Notas de correção adicionadas (histórico preservado, não reescrito) em:
[2026-07-06-2332-boolean-spec-datasets](../2026-07-06-2332-boolean-spec-datasets/result.md),
[2026-07-06-2354-spec-bin-motor](../2026-07-06-2354-spec-bin-motor/result.md),
[2026-07-07-0028-spec-bitwidth-bN](../2026-07-07-0028-spec-bitwidth-bN/result.md).

## A tese

**Tipo não é um bolt-on — é a ponta mínima do MESMO espectro de specs** que já inclui as natures
(CPF/CNPJ/datetime). Um primitivo (`string`/`int`/`float`/`bool`/`null`) é uma **spec ultra-minimalista
induzida**. Do mínimo ao rico: `string` (fallback) → `int`/`float`/`bool` → `nature` (CPF, datetime, …).
No código isso já existe nas duas pontas: `natures.templated_checked.TemplatedCheckedSpec` (rica) e
`column_features.analyze_column` (`is_numeric`, `cardinality`, `sample`) que **induz** a ponta mínima.

## Toda spec se justifica por COMPRESSÃO ou ACELERAÇÃO

Uma spec só vale a pena se dá pelo menos um dos dois:
- **Compressão**: o body encolhe (template, delta, dict, bitmap).
- **Aceleração**: o decode não precisa deduzir (parse/typing conhecido) + habilita acesso lazy/tipado.

Se não dá nenhum → não spec (fica `string`). Medido (o número corrigiu a intuição):

| spec | induz de | compressão (medida) | aceleração | round-trip guard |
|---|---|---|---|---|
| **string** | — (default) | não | não (identidade) | — |
| **int** | dígitos, sem ponto | HCC/seq-RLE quando sequencial (1..100: 601→23B); cadence/delta se ligado | parse rápido | `str(int(v))==v` |
| **float** | tem ponto | idem int | parse rápido | `str(float(v))==v` |
| **bool** | domínio {true,false} | **TEXTO: só ~6B flat** (dict-shrink; HCC já referencia os 2 distintos); **bitmap** (1 bit/val) só em **binário V2-L** | mapa direto | `v∈{true,false}` |
| **null** | máscara (Ciclo 1c) | body vazio + def-level | pula célula | — (máscara) |
| **nature** (CPF/CEP/datetime) | template/gabarito | **template + delta** (forte) | validação | round-trip do template |

> **Correção empírica importante**: em TCF **textual**, o bool-spec NÃO economiza ~N (1 bit/valor) — só o
> **dict** encolhe uma vez (~6B), porque o HCC já dedup os 2 valores e guarda N referências idênticas. O ganho
> por-valor do bool é **binário** (bitmap, V2-L/ADR-0018). Em texto o bool vale por **aceleração**. Não
> superestimar a compressão de tipo em texto — o forte é aceleração + o espaço binário.

## Além dos 2 eixos: características ORTOGONAIS (owner 2026-07-06)

Compressão e aceleração são **preditivas** (dizem se vale aplicar). Mas uma spec tem mais eixos ortogonais:

| eixo | o que é | decide |
|---|---|---|
| 1 compressão | body encolhe | vale aplicar? |
| 2 aceleração | decode sem deduzir + acesso tipado | vale aplicar? |
| 3 **autoridade** | mandatório / spec-natural / deduzido | liberdade de canonicalizar |
| 4 **normalizabilidade** | superfície livre vs byte-locked | pode mudar a superfície? |
| 5 **fechamento de domínio** | fechado (enum/bitmap) vs aberto | habilita bitmap/dict |
| 6 **variante** | superfície do mesmo semântico (1/0, t/f, Y/N) | o que guardar p/ RT |
| 7 **reversibilidade** | round-trip | seguro induzir? |
| 8 **validação/sanidade** | nature alerta anomalia (só detecta) | efeito colateral |

**Autoridade** (o ponto do CSV vs typed): no **CSV cru** trata-se como **string/enum** (preserva a superfície
exata, sanidade — `True`/`False` fica como está); se a entrada é **typed/declarada**, o compressor pode
**canonicalizar** (a saída pode sair `true` minúsculo — "vemos o DADO, não a string"). Três classes:
- **mandatório**: tipo declarado na entrada → canonicaliza.
- **spec-natural**: padrão conhecido (bool, datetime, CPF) → **gabarito-da-spec** (template implícito, a
  coluna nem guarda referência: os valores vêm da spec).
- **deduzido**: induzido do dado via round-trip → preserva superfície.

## Estudo empírico: "boolean" nos nossos datasets → é ENUM, não bool

Varredura (lab [`2026-07-06-2332-boolean-spec-datasets`](../2026-07-06-2332-boolean-spec-datasets/result.md),
synthetic + adult/tpch/receita/…): **ZERO `true`/`false`** em dado real. O que existe é **enum-2/3 com
superfície = DADO** (Male/Female, <=50K/>50K, F/O, A/N/R) + `matriz_filial=1|2` (**não** 0/1!). Portanto:
- **o primitivo útil é ENUM/domínio-k** (fechado, pequeno); **boolean (true/false) é a variante semântica,
  rara em tabela**. A spec certa é *enum-k*, com boolean como sub-caso (k=2 semântico).
- **Variante** é um eixo real: `1/0`, `t/f`, `true/false`, `True/False`, `Y/N` são a MESMA spec (bool) com
  superfícies diferentes; `matriz_filial=1|2` mostra que assumir 1/0 corromperia a semântica.
- **Bytes** (adult.sex, N=48842): raw 97KB → textual 49KB (~2×, encurta superfície) → **bitmap 6KB (~16×)**.
  O ganho textual é ∝ encurtamento da superfície; o grande/constante (1 bit/val) é **binário** (V2-L).

**Motor spec_bin** (lab [`2026-07-06-2354-spec-bin-motor`](../2026-07-06-2354-spec-bin-motor/result.md)):
enum-2 sem catálogo via **escape** (os 2 mais comuns = domínio, guardados 1× afixo-comprimidos: `male→fe1`);
corpo = bit-stream com **2 codificações** que o motor escolhe: **RLE** (textual/explicável, mantém a quebra) vence
ordenado/skew; **packed** (binário N/8, V2-L) vence espalhado. **Overlay de exceções** (99% dominantes + raros
null/other → canal esparso, = def-level do 1c). Medido: em **dado real espalhado, packed vence** (adult.sex
16×; 17–21k runs) → o corpo útil de enum real é binário; RLE fica pro ordenado + pela explicabilidade.

**Reuso do HCC + Formato A/B** (lab [`2026-07-07-0016-spec-bin-formato-A-B`](../2026-07-07-0016-spec-bin-formato-A-B/result.md)):
o HCC **já** produz o binário como literais+refs com índices naturais (`*3|male\n*2|fe1\n*2|^1\n*3|^2` →
male=^1=bit0, female=^2=bit1; `*N|^k` = bit-stream em RLE). Logo o `spec_bin` é **camada pós-HCC (V2-L)**, não
substituto: ordenado → HCC-RLE nativo (textual); espalhado → empacota as refs. **Formato A** (literal na 1ª
ocorrência + 2º declarado no 1º byte-escape) reusa o layout do HCC e é **single-pass streaming** (owner
prefere); **Formato B** (2 literais no topo) é 2-passadas. Mesmos bytes.

**Spec primitivo por LARGURA DE BITS `b<w>`** (lab [`2026-07-07-0028-spec-bitwidth-bN`](../2026-07-07-0028-spec-bitwidth-bN/result.md),
owner): generaliza `spec_bin` a enum-k. k distintos → w bits → 8/w linhas/byte: k≤2→**b**(8/byte) ·
k≤4→**b2**(4/byte) · k≤16→**b4**(2/byte) · k≤256→**b8**(1/byte). O spec = `col:b<w>` + a **lista do domínio
embutida = a referência** (índice↔valor); `spec_bin`=`b`. Medido em 12 colunas reais: **bit-pack vence em
todas** (dado espalhado) — b ~16×, b2 ~6-9×, b4 ~2-6× vs raw HCC. **Pesa vs HCC-nativo** (RLE de refs): HCC
ganha ordenado (poucos runs, textual/explicável); bit-pack ganha espalhado (V2-L). O motor escolhe o menor;
header `col:b<w>` textual roteia. Une string→enum-k num só spec primitivo.

## A regra universal de indução: ROUND-TRIP

**Uma spec induz-se com segurança ⟺ o valor faz round-trip por ela** (encode-pela-spec → decode devolve o
original). É zero-config e resolve o self-description (o mesmo problema do hex, do tipo e da nature) de uma vez:

| valor | induz | por quê |
|---|---|---|
| `"30"` | **int** | `str(int("30"))=="30"` ✓ |
| `"01310"` | **string** | `int("01310")=1310` → `"1310"` ≠ `"01310"` (zero à esquerda) ✗ |
| `"4.5"` | **float** | `str(float("4.5"))=="4.5"` ✓ |
| `"4.50"` | **string** | `float("4.50")=4.5` → `"4.5"` ≠ `"4.50"` ✗ |
| `"1e3"` | **string** | `float("1e3")=1000.0` → `"1000.0"` ≠ `"1e3"` ✗ |
| `"true"` | **bool** | `∈ {true,false}` ✓ |
| `"True"` | **string** | JSON é minúsculo; `∉ {true,false}` ✗ |

O que reverte, induz de graça (sem marcador). O que **não** reverte é uma string que *parece* tipada → fica
string, ou leva marcador explícito (a **C-híbrida** do 1b). É o análogo exato do **hex-default**
(T-OPT-INFERENCE) e da **1ª-string-molde do OBAT**.

## Gabarito: a 1ª amostra propõe, o round-trip confirma

`analyze_column.sample` (primeiras 20) = o **gabarito**. A 1ª amostra **propõe** a spec da coluna; o
round-trip em **todas** **confirma** (ou rebaixa pra string). Medido:
- `idades ["30","41",…]` → 1ª propõe int, todas revertem → **coluna int**.
- `ceps ["01310",…]` → 1ª propõe int, mas não reverte → **string** (o guard salva).
- `misto ["30","ana",…]` → 1ª propõe int, `"ana"` quebra → **string**.

= a **C-híbrida (1b) generalizada**: propõe pelo gabarito, confirma pelo round-trip, tag na colisão.

## Consequências (o que isto reorganiza)

1. **Unifica** três coisas que estavam separadas num **só mecanismo**: tipo (1a/1b) + base hex
   (T-OPT-INFERENCE) + natures (ADR-0015). Todas = specs induzidas por gabarito + round-trip; diferem só na
   riqueza. Hex vira uma **sub-spec numérica** (a base do número); CPF vira uma spec-template.
2. **Pipeline**: a indução é um estágio do **pre-pass** já existente — `analyze_column` induz (is_numeric,
   cardinality, sample), `detect_cadence`/HCC comprimem o número. Custo ~zero ("só o que já se calcula",
   SideOutputs). É "colocar no fluxo do mecanismo todo" (owner).
3. **Decisão por spec**: induz quando (comprime OU acelera) E faz round-trip; senão string (+ marcador na
   colisão). O eixo compressão/aceleração diz QUANDO uma spec vale; o round-trip diz SE é segura induzir.
4. **Camadas**: a compressão forte de alguns primitivos (bool→bitmap) é **binária (V2-L)**, não textual — o
   espectro de specs atravessa as duas camadas (header textual roteia; body pode ser binário).

## Aberto / próximo (Ciclo 3)

- Formalizar o registro de specs (primitiva ↔ nature) e o ponto de indução no pre-pass.
- Medir o ganho de **aceleração** (decode tipado vs deduzido) — hoje só a compressão foi medida.
- bool-bitmap na camada binária (V2-L) — quantificar o 1-bit/valor.
- Ligar hex (T-OPT-INFERENCE) como sub-spec numérica sob esta regra única.
