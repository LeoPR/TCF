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

## Partição do code-space bN (registro original)

O owner propôs usar o **próprio código** pra distinguir os papéis: `b2/b4/b8` (potências de 2, tile-de-byte)
pra a **representação de índice reativa**; `b3/b5/b7` (os "números que faltam") pra **índices internos**
(preemptivos). Duas leituras a avaliar (não fechado):
- **Opção A (code encodes role)**: o char/código do marcador codifica largura **E** papel (reativo vs
  interno) — economiza um marcador, mas gasta code-space e mistura dois eixos.
- **Opção B (marcador + largura exata)**: um marcador separado diz reativo-vs-interno; a largura é sempre
  `ceil(log2(k))` (inclui b3/b5/b6/b7 como larguras exatas, que packam mais que snap-a-potência). Mais
  limpo, ortogonal. **Recomendo B** (largura exata é ganho real; o papel é um bit à parte) — mas registrar
  a A como alternativa. Interage com o [registry de chars do header](tcf8-header-char-registry.md).

## Fechamento (o "fechar algo já")

- **Modelo bN**: duas perspectivas — reativa (`@dict`-index bit-packed, domínio na coluna, via `min()`) e
  preemptiva (dict interno clássico, domínio no formato). **bN ⊂ @dict** na representação.
- **Dict interno clássico**: proposto como **feature de spec opt-in congelada** (não ganho de byte), com o
  vocabulário inicial acima. Weld/freeze = owner, pré-1.0. Registrado **H-TYPE-07**.
- **Largura exata** (b3/b5/b6/b7): recomendada (Opção B) sobre snap-a-potência.

## Cross-links
- Primitiva unificada: [`dict-referencia-hipoteses.md`](dict-referencia-hipoteses.md) §primitiva.
- Prior-art: [`cep-outer-dict-codebook-pesquisa.md`](cep-outer-dict-codebook-pesquisa.md) (outer-dict) ·
  [`specs-capacity-map.md`](specs-capacity-map.md) (SPEC_REGISTRY + EnumSpec no-go).
- bN/specs: [`tipos-meta-grupo-fluxo.md`](tipos-meta-grupo-fluxo.md) (§5 bN, §8 eixos) ·
  [`tipos-como-specs.md`](tipos-como-specs.md) · gate [`2026-07-08-1938-bn-gate-realworld-5fontes`](../2026-07-08-1938-bn-gate-realworld-5fontes/result.md).
- Header: [`tcf8-header-char-registry.md`](tcf8-header-char-registry.md).
