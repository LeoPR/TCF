# bN × @dict — duas perspectivas + proposta de dicionário interno clássico [proposta, owner 2026-07-08]

**Owner (2026-07-08)**: bN e `@dict` são similares mas **depende da perspectiva**; e a ideia de **firmar um
dicionário interno pros dados mais clássicos** (true/false, true/false/null, yes/no…). Refina a
[primitiva unificada "referência por índice"](dict-referencia-hipoteses.md). **Anotado pra revisar cada
uma**; o concreto a fechar é o **dict interno clássico**.

## Duas perspectivas de bN (a chave)

O bN e o `@dict` são a mesma primitiva (referência por índice), mas o bN aparece em DOIS papéis:

### (a) REATIVA — pós-núcleo, representação do índice do `@dict`
Depois do HCC, se uma coluna virou `@dict` com domínio pequeno (k≤256), o **stream de índices** pode ser
**bit-packed** (bN) em vez de base-94. É o candidato do `min()` que já prototipamos. **bN ⊂ @dict**: é o
`@dict` com o índice em bits em vez de base-94. Domínio **guardado na coluna**. Decidido por medição (min).

### (b) PREEMPTIVA — dicionário INTERNO, "petrificado" no formato
Alguns domínios são **universais/clássicos** (`true/false`, `true/false/null`, `yes/no`, `sim/não`, `0/1`,
`Y/N`). Esses podem ser um **dicionário fixo embutido no formato** (congelado até o 1.0) — a coluna
**não guarda o domínio**, referencia o interno. "Até a referência fica interna" (owner). É o **`SPEC_REGISTRY`
das natures aplicado a enums clássicos**.

## A motivação da preemptiva — revisitada (owner, 2026-07-08): os 3 FLUXOS

> Owner: "a preemptiva não tem função exata a não ser para duas coisas" — (1) **dicionário pré-carregado**:
> quando o HCC termina, o mapeamento já existe, "só precisa mapear" (não constrói nem armazena domínio);
> (2) **habilitar o roteamento entre 3 fluxos** por coluna. Os 3 fluxos mapeiam 1:1 na taxonomia QUANDO
> ([tipos-meta-grupo-fluxo](tipos-meta-grupo-fluxo.md) §2):

| fluxo | quando | o que faz | núcleo (OBAT+HCC) | o que otimiza | âncora existente |
|---|---|---|---|---|---|
| **1. Bypass** (substituição direta) | entrada/pré | **aposta** que a coluna segue o domínio clássico (true/false); substitui direto por índices (1-2 bits), **sem passar pelo núcleo** | **pulado** | **LATÊNCIA + memória** (vértice tríplice, ADR-0002) | aposta falhada coberta pelo **overlay de exceções** ([spec-bin-motor](../2026-07-06-2354-spec-bin-motor/result.md): dominantes + canal esparso, lossless) |
| **2. Pré-tx aceleradora** | camada 0 (pré-núcleo) | remove o previsível — máscara `.`/`-`, dígito verificador — o núcleo processa MENOS bytes e **roda mais rápido** | roda (input menor) | velocidade DO núcleo + bytes | **JÁ EXISTE, WELDED** = natures ADR-0015 (`TemplatedCheckedSpec` "descarta máscara+DV") — o "CPF-like" do owner é literalmente isso |
| **3. Misto seletivo** | processo + pós-HCC | identifica o tipo no processo (`analyze_column`: cardinality), roda o núcleo normal, e aplica a classe bN **só nos itens de bool ou largura ≤ 4 bits (k≤16)** | roda | bytes, só onde paga | o `min()` por-coluna, com gate **k≤16** (mais estrito que o k≤256 do protótipo — casa com o gate D3: o forte é k pequeno) |

**Análise crítica (o que cada fluxo realmente acrescenta)**:
- **Fluxo 2 não precisa do dict interno** — já é o mecanismo das natures (welded). Bool não tem máscara/DV
  a tirar; o dict clássico não acrescenta aqui. Serve como *modelo* do padrão, não como trabalho novo.
- **Fluxo 1 é a motivação REAL da preemptiva** — e é um play de **latência/throughput** (pular o núcleo
  inteiro pra colunas trivialmente tipadas), não de bytes. Alinha com o vértice tríplice (latência é
  restrição dura) e com o eixo **aceleração** — que é exatamente o eixo **sem número** até hoje (só a
  compressão foi medida, em todos os labs). A aposta exige o overlay de exceções pra permanecer lossless.
- **Fluxo 3 refina o reativo** — o gate k≤16 do owner encurta o alcance do bN pro trecho onde o gate D3
  mostrou ganho denso (b/b2/b4); b8 (k≤256) fica de fora do default. Segue condicionado a terminal.

**Consequência de ordem**: a **Opção B (largura exata, formato) fica EM ESPERA** — antes de cravar formato,
**medir o fluxo 1** (latência bypass-com-dict-interno vs núcleo completo, com overlay de exceções). Se o
bypass pagar em velocidade, a preemptiva se justifica pelo eixo aceleração; senão, sobra só o fluxo 3
(reativo com gate k≤16) e o dict interno vira apenas vocabulário de spec (self-description).

## Análise crítica 2 (owner, 2026-07-08) — serialização byte-aligned · lifecycle do F2 · corrida especulativa

### (i) Restrição de serialização: só vale binarizar com w≤4, em stream byte-aligned
> Owner: "só vale a binarização se serializável em ≤4 bits e em sequências de 8 bits — dificílimo
> representar menos de 8 bits de verdade; o resto do stream fica 'comido' (padding)."

- **Matemática do tiling (verificada)**: w ∈ {1,2,4} divide 8 → cada byte contém exatamente 8/w valores,
  **nenhum valor atravessa fronteira de byte** → serialização trivial, acesso por aritmética byte+shift,
  stream inspecionável por byte. w ∈ {3,5,6,7} **não divide 8** → cursor de bits, valores atravessando
  bytes. **b8 fora do default** (gate D3: ganho mais fraco; k>16 → dict/base-94 cobre).
- **Padding do rabo**: ≤7 bits = **≤1 byte por coluna**; o decoder já resolve parando em N valores
  (`bn_decode(body, n)` do protótipo faz isso — os bits de pad são ignorados). Não-questão pra N≥~16.
- **⟲ REVISÃO HONESTA da recomendação**: esta restrição **REFUTA a minha Opção B** (largura exata
  b3/b5/b6/b7): essas larguras não tile-iam bytes, e o ganho marginal (b3 vs b4 = 25% do stream de índices,
  medido) não paga a complexidade/opacidade num nicho já terminal. E com 3/5/6/7 **inúteis como largura
  física**, o code-space deles fica livre — **a Opção A do owner (b/b2/b4/b8 = largura física; b3/b5/b7 =
  códigos de papel/dict-interno) volta a ser coerente**: não gasta nada, usa números sem significado físico.
  *(Formulação com b8 SUPERADA pela RESOLUÇÃO abaixo: a família resolvida é b1/b2/b4, SEM b8 — 8 bits =
  1 byte exato, sem packing sub-byte; o regime k>16 já é coberto pelo `@dict`/v2b. Confirmado pelo F3.)*
  *(Registro: a técnica conhecida que resgataria larguras exatas é agrupar 8 valores → 8·w bits = w bytes
  inteiros — o bit-packing do Parquet; anotada, NÃO recomendada agora.)*
- **Larguras físicas do default: {1, 2, 4}** — consistente com o F3 (k≤16) e com o corte denso do gate D3.

### (ii) Lifecycle do F2: specs são GANHAS em volume de projeto, depois CONGELADAS (o template CPF)
F2 **nunca é induzido em runtime**: um tipo prova a vantagem híbrida em **estudo/volume prévio** (lab),
passa o gate (≥15%/2-reais, estilo ADR-0015) e é **fixado** como spec no registry congelado — daí em diante
"usa nesse formato pré-tx", no estilo do CPF. Separação limpa que isso cristaliza:
**F1/F3 = runtime, classes GENÉRICAS** (bool/low-card, sem semântica) · **F2 = project-time, specs
SEMÂNTICOS** (CPF/CNPJ/datetime), earned + frozen. Um não vira o outro em execução.

### (iii) A corrida especulativa (F1+F2, "quase paralelo com espera")
> Owner: as duas filas disparam; a do núcleo ESPERA um pouco; se a fila de tipo decide "classe simples
> (bool)", **cancela** a fila do núcleo.

- **Versão engenharia-honesta (batch, hoje)**: o classificador **já é (quase) o pré-pass existente** —
  `analyze_column` varre a coluna (cardinality/is_numeric/sample) ANTES do OBAT. O delta é pequeno:
  `analyze_column → [classe clássica/k≤16 + round-trip? → BYPASS] → OBAT → HCC`. Em batch não precisa de
  filas: o classificador tem **early-exit** (aborta no 17º distinto, ou no 1º valor fora do domínio além
  do budget de exceções) e custa << núcleo — "tentar-primeiro sequencial" domina a corrida.
- **Onde as filas viram REAIS**: em **streaming (V2-J)** — o classificador roda on-the-fly numa janela e o
  núcleo fica em espera/cancelável. A formulação do owner é o desenho streaming da mesma decisão; guardar
  pra quando V2-J abrir.
- **Risco da aposta tardia** (o valor 999.990 quebra a classe): mitigado por (a) **overlay de exceções com
  budget** — raros fora do domínio não cancelam a aposta, vão pro canal esparso; (b) hard-bail só quando o
  nº de distintos estoura a classe; (c) pior caso = 1 scan extra O(N) barato antes do núcleo — limitado.

## O que a perspectiva (b) vale — HONESTO (não é byte)

**Prior-art que qualifica**: o [outer-dict/codebook](cep-outer-dict-codebook-pesquisa.md) (2026-06-16) já
achou que codebook compartilhado é **subsumido pelo V2-B+split** no caso tabular; nicho = payload minúsculo
indexando tabela-padrão grande. O dict-interno-clássico é o caso de **domínio pequeno-universal** → a tabela
salva é minúscula (~9 B pra true/false) → **ganho de byte ainda menor**. Somando ao **EnumSpec no-go**
(M10 vence enum explícito) e ao **gate D3** (bN colapsa pós-brotli), o **byte NÃO justifica**.

O que justifica (o eixo certo, do [tipos-como-specs](tipos-como-specs.md)):
1. **Self-description / spec**: o formato *sabe* que a coluna é boolean/ternária → **acesso tipado**,
   **canonicalização** (mapear `True`/`1`/`sim` → o mesmo lógico na saída, se autoridade permitir).
2. **Aceleração** (decode conhece o mapa, não deduz) + o **byte-mínimo no nicho terminal/payload-minúsculo**
   (não guarda o domínio). É o mesmo nicho e o mesmo veredito do bN: vale **terminal**, não geral.

→ Proposta: dict-interno-clássico é uma **feature de SPEC (opt-in, congelada)**, análoga ao `SPEC_REGISTRY`
(cpf/cnpj/ip) — **não** um ganho de compressão. Weld/freeze = decisão do owner, pré-1.0.

## Proposta concreta — o vocabulário inicial (a firmar)

Registry interno mínimo de enums clássicos (cada um = mapa fixo + largura de índice):

| id | domínio (ordem canônica) | k | largura |
|---|---|---|---|
| `bool` | `false`, `true` | 2 | 1 bit |
| `bool3` (trio) | `false`, `true`, `null` | 3 | **2 bits** |
| `yesno` | `no`, `yes` | 2 | 1 bit |
| `simnao` | `nao`, `sim` | 2 | 1 bit |
| `bit` | `0`, `1` | 2 | 1 bit |
| `yn` | `N`, `Y` | 2 | 1 bit |

- **Variantes de superfície** (`True/False` vs `true/false` vs `1/0`) = o eixo **variante** do spec: o
  mesmo lógico, superfícies diferentes; a **autoridade** (typed → canonicaliza; CSV cru → preserva) decide
  se a saída sai canônica ou fiel. (ver `tipos-como-specs` §8 eixos.)
- Congelado até 1.0 (como `SPEC_REGISTRY`): adicionar um id novo = mudança de formato marcada.

## Partição do code-space bN (ideia do owner — a avaliar) — **EM ESPERA (owner, 2026-07-08)**

> Antes de fazer a Opção B, o owner pediu pra revisitar a motivação da preemptiva (seção "os 3 FLUXOS"
> acima). **Decisão de ordem**: medir o **fluxo 1** (latência do bypass) ANTES de cravar formato/largura.
>
> **RESOLVIDO em parte (Análise crítica 2, mesma data)**: a restrição de serialização byte-aligned do owner
> **refuta a Opção B** (larguras exatas 3/5/6/7 não tile-iam bytes) → larguras físicas = **{1,2,4}**; os
> códigos 3/5/7 ficam livres pra papel/dict-interno (**Opção A do owner, agora coerente**). O que segue em
> espera é só a medição do **F1** (bypass paga em latência?).

## Partição do code-space bN (registro original)

### RESOLUÇÃO (owner 2026-07-08) — Opção A refinada; Opção B morta

O owner fechou a nomenclatura, e ela **mata a Opção B** (largura exata): como só `w∈{1,2,4}` tile-de-byte
(3/5/6/7 bits atravessam fronteira de byte — verificado), NÃO faz sentido `b3/b5/b6/b7` serem larguras
físicas. Então o **código é reusado como rótulo semântico** (Opção A refinada):
- **b1/b2/b4** (minúsculo) = LARGURA FÍSICA real (1/2/4 bits, tile-de-byte). Reativo, domínio na coluna.
- **b3** = código reusado p/ "b2 + null" (trio: false/true/null, 2 bits, 4º slot livre). Não é 3-bit.
- **b5/b6/b7** = códigos reusados p/ **tipos especiais** (reservados, a definir).
- **B** (MAIÚSCULO) = bool com dict INTERNO congelado — **não declara a referência** no arquivo, usa a
  interna sempre (economiza a tabela de domínio + self-describing).

Isto corrige o "Recomendo B" anterior: a largura exata não sobrevive à restrição byte-tiling; o que fica é
código-como-papel com só 3 larguras físicas. Interage com o [registry de chars](tcf8-header-char-registry.md).
Medido em [F1 latência](../2026-07-08-2302-f1-bypass-latencia/result.md) (bypass 2.4×; interno B RT-OK).

## Fechamento (o "fechar algo já")

- **Modelo bN**: duas perspectivas — reativa (`@dict`-index bit-packed, domínio na coluna, via `min()`) e
  preemptiva (dict interno clássico, domínio no formato). **bN ⊂ @dict** na representação.
- **Dict interno clássico**: proposto como **feature de spec opt-in congelada** (não ganho de byte), com o
  vocabulário inicial acima. Weld/freeze = owner, pré-1.0. Registrado **H-TYPE-07**. Medido: F1 latência
  2.4× + interno B RT-OK ([lab](../2026-07-08-2302-f1-bypass-latencia/result.md)).
- **Nomenclatura RESOLVIDA** (owner): b1/b2/b4=largura física; b3=trio (b2+null); b5/6/7=especiais;
  B=interno. Opção B (largura exata) MORTA — só 1/2/4 tile-de-byte.

## Cross-links
- Primitiva unificada: [`dict-referencia-hipoteses.md`](dict-referencia-hipoteses.md) §primitiva.
- Prior-art: [`cep-outer-dict-codebook-pesquisa.md`](cep-outer-dict-codebook-pesquisa.md) (outer-dict) ·
  [`specs-capacity-map.md`](specs-capacity-map.md) (SPEC_REGISTRY + EnumSpec no-go).
- bN/specs: [`tipos-meta-grupo-fluxo.md`](tipos-meta-grupo-fluxo.md) (§5 bN, §8 eixos) ·
  [`tipos-como-specs.md`](tipos-como-specs.md) · gate D3 [`2026-07-08-1938`](../2026-07-08-1938-bn-gate-realworld-5fontes/result.md).
- **Os 3 fluxos MEDIDOS**: F1 latência [`2026-07-08-2302`](../2026-07-08-2302-f1-bypass-latencia/result.md)
  (bypass 2.4×) · F3 seletivo [`2026-07-08-2355`](../2026-07-08-2355-f3-bn-seletivo/result.md) (w≤4 = 5.9%
  terminal / 0.5% pós-brotli, pode ir net-negativo) · F2 = natures ADR-0015 (já welded).
- Header: [`tcf8-header-char-registry.md`](tcf8-header-char-registry.md).
