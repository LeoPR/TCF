# ADR-0041 — Spec em TRÊS planos: nome de código, id de wire, e o carimbo

- **Status**: **aceito — weld A SOLDADO** (2026-08-13, aprovação "pode soldar"; as 4
  decisões foram tomadas uma a uma no mesmo dia). Suíte 1239 → **1247**; gates
  byte-canonical intactos. A decisão 4 é capacidade nova fora deste weld
  (`T-SPEC-SEM-CARIMBO`).
- **Escopo**: identificação de spec/nature em todas as rotas que a emitem
  (`#TCF.8 [col]:id` single-col · `#TCF.8M…=col:id` multi-col · `#TCF.8H` `:size:id`),
  o registry (`natures/`) e a resolução no decode.
- **Interage com**: ADR-0027 (a tag no header · self-describing) · ADR-0034 (header é
  default) · ADR-0024 (pré-1.0, baselines re-pináveis) · ADR-0015 (natures) ·
  `T-NATURE-CANDIDATO-BN` · `T-PULSO-SINGLE-COL`
- **Origem**: direção do owner (2026-08-12), reafirmando desenho já revisado antes.

---

## Contexto

Hoje o spec tem **um** nome (`name: str`), **sem regra nenhuma** — sem limite, sem
charset, sem validação. Ele é ao mesmo tempo o identificador de código e o que viaja no
wire. Três consequências medidas:

1. **Custo**: a tag ` :data-iso` são **10 B** num artefato de 32 B — **31%**. E o
   comprimento do id **decide a competição**: em N ≥ 11 datas diárias a nature **perde**
   o FLOOR com `data-iso` (47 B, o encoder emite o core) e **vence** com um id de 2
   chars (43–44 B). *O nome longo suprime a própria nature* no regime de payload
   minúsculo (O-FMT-15/16).
2. **Corrupção**: sem validação, um id com `,` faz o decode explodir como *"referência a
   fragmento inexistente"* — erro que aponta pro corpo, não pro nome. `:` parseia coluna
   errada; `\n` dá "bytes excedentes"; `}` quebra o `.8H`.
3. **Divergência de parse**: o mesmo id é lido por **três gramáticas** distintas —
   primeiro `:` (single), último `:` não-escapado (multi), até `,]}` (`.8H`). Um id
   `a:b` quebra em multi e passa no `.8H`.

O erro de enquadramento que este ADR corrige: tratar "nome legível" e "id curto" como
**alternativas**. Não são — são **planos diferentes**, e o desenho pede os dois.

## Decisão

### 1. Três planos, separados por natureza

| plano | quem é | onde vive | quem o vê |
|---|---|---|---|
| **CÓDIGO** | `name` legível (`data-iso`) | API, telemetria, mensagens de erro | o dev |
| **DADO** | `wire_id` curto (`dt`) | header do wire, quando carimbado | o arquivo/transmissão |
| **CONTRATO** | se o id **acompanha** o dado ou fica nas pontas | decisão de emissão | as duas pontas |

O nome de código **nunca** viaja. O id de wire **nunca** é o identificador da API. São
campos distintos do mesmo spec, não duas grafias do mesmo campo.

> **DECIDIDO (owner, 2026-08-13)**: **dois campos**. A alternativa era um campo só,
> encurtado (`dt` também na API) — ganharia os mesmos bytes com menos maquinaria, mas o
> código perderia legibilidade e a decisão 3 deixaria de existir. O owner escolheu
> separar, mantendo `data-iso` legível em API/telemetria/erros.

### 2. Regra de grafia do `wire_id`

```
wire_id  ::=  ^[a-z][a-z0-9]{0,7}$        # minúscula inicial, alfanumérico, 1-8
```

Validado **fail-loud em dois pontos**: no **registro** (recusa grafia inválida *e*
colisão) e na **emissão** (fecha o buraco do §Contexto-2 para spec de terceiro).

> **CORREÇÃO (2026-08-13, medida)** — a versão anterior deste ADR justificava
> "minúsculas-only" como necessidade técnica (reservar MAIÚSCULAS/pontuação para os
> sufixos de rota). **Isso não se sustenta**: o id vive depois do `:` e não colide
> posicionalmente com sufixo nenhum. Testado — `DT`, `Dt`, `8d`, `ab_c`, `x-y` fazem
> round-trip hoje, em single-col e multi-col. Varrendo os 33 caracteres de pontuação,
> **só `,` e `:` quebram** (são separadores do meta multi-col), mais `\n`.

**O requisito DURO é pequeno**: excluir `,`, `:` e controle. Sem isso o id hostil corrompe
com erro **enganoso** (`,` explode como *"referência a fragmento inexistente"* — aponta pro
corpo, não pro nome).

**Todo o resto é convenção**, e a convenção compra três coisas concretas:

1. **previsibilidade** — id sempre reconhecível de relance, e validação trivial de
   escrever e de explicar;
2. **espaço de convenção** — família por prefixo (`dt`, `dtm`, `dtym`…) e `x…` reservado
   a terceiros só funcionam se a forma for regular;
3. **imunidade a mudança futura de gramática** — hoje só `,`/`:` separam, mas o `.8` ainda
   pode ganhar separador; um charset estreito não precisa ser revisitado.

O ganho de **bytes** vem do LIMITE, não do charset (`dt` custa o mesmo que `DT`). Sem
hífen porque ele custa 1 byte e não informa — era o único caractere que fazia `data-iso`
estourar 8.

> **DECIDIDO (owner, 2026-08-13)**: a regra **restritiva**. As alternativas eram a mínima
> (proibir só o que corrompe) e a intermediária (alfanumérico com maiúscula) — as duas
> dariam os mesmos bytes. O owner escolheu previsibilidade e espaço de convenção sobre
> liberdade de grafia.

### 3. O `wire_id` é o que a resolução compara

Consequência **obrigatória** do plano 1, sem a qual o plano 3 quebra. Hoje
`_resolve_header_spec` compara `supplied.name == nature_id`; com dois campos isso diverge
sempre (medido: `decode(wire_com_':dt', nature=SPEC_DATA_ISO)` → *"'dt' não coincide com
'data-iso'"*). A comparação passa a ser contra o **`wire_id`**.

A **precedência já existe e fica como está** — verificada em código:

| situação | comportamento |
|---|---|
| dado tem id, função cala | **o dado manda** (registry resolve) |
| dado tem id, função declara o mesmo | ok — a função **estende** o registry (spec de terceiro) |
| dado diz `X`, função passa `Y` | **fail-loud** — nunca escolhe calado |

> **DECIDIDO (owner, 2026-08-13) — resolução ESTRITA**: compara **só** o `wire_id`
> vigente. Os **14 wires históricos** com `:data-iso` (labs) passam a **falhar alto** com
> mensagem acionável; quem quiser lê-los passa o spec out-of-band
> (`dataclasses.replace(SPEC, wire_id="data-iso")`). As alternativas eram um alias
> histórico declarado no spec (`wire_ids_legado`) e regravar os 14 wires — a primeira
> deixaria dois ids resolvendo pro mesmo spec (bagagem no registry, com data de remoção
> a combinar); a segunda inflaria o diff. **Coerente com o ADR-0024**: o passado se lê
> pelo git, não por bagagem no código.
>
> Consequência aceita: os 14 wires **não abrem pelo `view`** (que não tem a válvula
> out-of-band). Documentado, não consertado — são artefatos de lab.

**Não decidido aqui**: um `force` que deixe a função sobrepor o dado. Fica para estudo
(direção do owner: *"ainda não sei quem tem prioridade… podemos fazer um force depois"*).

### 4. Modo sem-carimbo — **fora do escopo deste weld** (`T-SPEC-SEM-CARIMBO`)

Uma opção de emissão em que o encode **sabe** do spec, aplica a transformação, e
**não** põe o id no dado — obrigando a outra ponta a declarar. É contrato-nas-pontas
(direção de 2026-07-16), aplicado ao spec.

Medido no caso de transmissão (600 datas diárias):

| | wire |
|---|---:|
| com carimbo | `#TCF.8 :data-iso` + corpo = **32 B** |
| sem carimbo | corpo puro `*600+1\|\739617` = **15 B** |

**Hoje as duas metades estão quebradas** e precisam ir juntas:

- **emissão**: `encode(vals, nature=SPEC, stamp=False)` **carimba assim mesmo** — a rota
  da nature devolve `header+body` antes de chegar no `if stamp is False`.
- **recepção**: `decode(corpo_sem_tag, nature=SPEC)` devolve o **payload cru**
  (`'739617'`) — o parâmetro só age quando já existe tag no header.

**É um parâmetro NOVO, não o `stamp=False`**: `stamp=False` remove o header inteiro
(órfão); este remove só o `:id`. São eixos distintos e podem se combinar.

O preço, explícito: sem o id, o wire fica **indistinguível** de uma coluna de inteiros
qualquer. É o custo do "mínimo de header", e casa com a assinatura-de-contrato fail-loud
já registrada na direção de contrato externalizado.

> **DECIDIDO (owner, 2026-08-13) — ticket PRÓPRIO, depois do rename.** As decisões 1-3 são
> um *rename com consequências*: contido, testável, reversível, sem superfície nova. Esta é
> **capacidade nova** (parâmetro no encode + semântica nova no decode), e as duas pontas
> têm de ir juntas — emissão sozinha produziria wire que a própria API não lê (medido:
> `decode(corpo_sem_tag, nature=SPEC)` devolve o payload cru). Misturar as duas naturezas
> num weld só faria um defeito no modo novo derrubar o rename junto. Vira
> **`T-SPEC-SEM-CARIMBO`**, com o desenho já fechado acima.

## O mapa de ids — **revisável até o 1.0**

> Decisão do owner: *"isso permite a gente revisar esses nomes até o final do 1.0 — se
> eles ficarem na forma de mapa de escolha, até o momento de fixar com a versão, podemos
> mexer; basta ter a estrutura clara."*
>
> **O que este ADR congela é a ESTRUTURA** (os três planos, a regra de grafia, o campo
> `wire_id`, o modo sem-carimbo). **A tabela abaixo é escolha, não estrutura** — muda por
> edição desta tabela + re-pin, enquanto o formato for pré-1.0 (ADR-0024). Congela junto
> com a versão.

| `wire_id` | `name` (código) | estado |
|---|---|---|
| `dt` | `data-iso` | **soldado 2026-08-13** — medido: 12 flips do FLOOR contra 6 do `dtiso` |
| `cpf` | `cpf` | vigente, já cumpre a regra |
| `cnpj` | `cnpj` | vigente, já cumpre |
| `ip` | `ip` | vigente, já cumpre |
| `dtm` | datetime | reservado (H-CP-DATETIME) |
| `dtbr` | data-br | reservado (H-TM-DATA-BR) |
| `dtym` | data-ano-mes | reservado (medido, EXP-017) |
| `dtmes` | data-mes | reservado (medido, EXP-017) |
| `dtfim` | data-fim-de-mes | reservado (medido, EXP-017) |
| `x…` | — | **prefixo reservado a terceiros**; o core nunca usa |

**Amplitude** sob a regra: 26 ids de 1 char, **936** de 2, ~2·10¹² até 8. O universo
planejado no registry é ~25 specs — 2 chars já cobrem 37×. `dt` vira **prefixo natural
da família de data** sem colidir com nada.

**Por que `dt` e não `dtiso`**: captura **12** flips do FLOOR contra 6, vence em todo
N ≥ 11, e leva 600 datas de 32 → **26 B** (−18,8%, contra −9,4% do `dtiso`).
**Por que não `d`**: 1 char são 26 slots no universo inteiro, e gastá-lo justo no tipo
com mais irmãos previstos deixaria a família sem prefixo.

## O weld A, executado (2026-08-13)

**Pontos tocados** (todos pequenos, como previsto na migração): campo `wire_id` nos 3
dataclasses de spec (fallback `""` → `name` nos Templated; `data_iso` explícito `"dt"`);
`_register` fail-loud montando os DOIS planos (`SPEC_REGISTRY` por name — intacto — e
`_WIRE_REGISTRY` por wire_id), validação e colisão checadas ANTES de inserir (falha não
deixa estado parcial); `_valida_emissao` na **porta do `tcf.encode`** — na porta de
propósito: a rota `.8H` envolve a emissão interna num try/except que cai pro piso, e
validar lá dentro ENGOLIRIA o spec hostil (pin: as 3 rotas recusam); emissores usando
`wire_id` (single `header_nat`, multi `nature_candidates`, `.8H` herda da single);
`_resolve_header_spec` comparando `wire_id`, estrito; gadget `natures_compiler/registry`
semeado com `data-iso` (gap fechado). Slot `None` em `nature_per_col` segue tolerado
(contrato pré-existente).

**Achado DO weld — a MASCARADA** (buraco novo dos dois planos, fechado na porta):
`replace(SPEC_CPF, name="custom-cpf")` **herda** `wire_id="cpf"` — emitiria `:cpf`, o
decode resolveria o spec CORE, e uma transformação derivada divergente corromperia
**calado** (pré-weld o id era o name, o buraco não existia; o teste antigo de spec
custom flagrou). Fechamento: wire_id do registry exige `name` IGUAL ao do dono. O check
é por **name** de propósito — clone funcional compilado de `.dsl` pelo gadget se chama
`cpf` e passa (essa é a fronteira de confiança PRÉ-weld, registry-first no decode;
igualdade de dataclass não serve porque regex/callables comparam por identidade). O weld
fecha só o buraco novo, sem estreitar nem alargar a fronteira antiga. Specs de terceiro
derivados levam wire_id próprio (`xcpf` nos testes re-pinados).

**Pins criados** (8 testes novos + 5 re-pins): flip do FLOOR N=10/11/12; grafias
recusadas nas 3 rotas (11 grafias × 3); registro atômico (grafia + 2 colisões, estado
não muda); wire histórico `:data-iso` falha alto + válvula `replace(wire_id=)` lê +
divergência "nao coincide"; mascarada recusada / no-op `replace(SPEC)` e core passam;
telemetria `nature_apply["spec"]` fica no plano do CÓDIGO (`data-iso`), wire só `:dt`.

## A caçada adversarial do weld (2026-08-13)

5 lentes executadas (gramáticas · resolução · mascarada · FLOOR/bytes · regressão),
cada suspeita **re-medida contra o commit anterior** para separar defeito-do-weld de
pré-existente. **Zero defeitos introduzidos.** O que ficou medido:

- **Regressão zero**: 295 wires (todos os `.csv` de `datasets/`, em multi-col,
  single-col e 3 variantes de flag) **byte-idênticos** ao pré-weld no caminho sem
  `nature=`. Gates byte-canonical (D1–D9 = 1545 B, real-world = 89430 B) intactos.
- **FLOOR nunca-pior**: 1416 combinações (8 padrões × N=2..60 × 3 níveis de sujeira),
  mais multi-col, `.8H`, `sort_by` e o seq-RLE periódico do ADR-0040 — nenhuma
  regressão de byte, RT em todas. Em N ≤ 10 o wire é **byte-idêntico ao core**; o
  flip é exatamente em **N = 11**.
- **Wires históricos**: os 14 são **todos single-col** — nenhum `.8H`, logo todos
  alcançáveis pela válvula out-of-band. (Achado de carona: a rota `.8H` **nunca**
  aceitou spec out-of-band — `decode_hierarchical(texto)` não recebe spec —, então
  spec de terceiro sempre foi ilegível por lá. Pré-existente, idêntico no commit
  anterior; não afeta nenhum dos 14.)
- **Três suspeitas descartadas** por serem idênticas no pré-weld: coluna de nome
  vazio vira anônima posicional (documentado, com warning); a válvula não chega ao
  `.8H` (acima); e spec divergente passado ao decode quando o id **está** no registry
  é ignorado — é o "header vence" do ADR-0027, não uma brecha nova.

**Consequência nova, aceita**: spec **duck-typed** escrito antes deste ADR (sem campo
`wire_id`) não emite mais. É fail-loud com mensagem que ensina o campo a declarar.
Quebra de API pré-1.0, coerente com ADR-0024.

**Lacuna medida, NÃO fechada aqui** (`T-SPEC-IMPOSTOR`): um duck-type que se declara
com a identidade do core (`name` **e** `wire_id`) e transforma diferente vence o FLOOR,
carimba `:dt`, e o decode aplica o spec core — corrupção **calada** (200 valores
deslocados 1000 dias, sem exceção). Reproduzida idêntica no commit anterior: a
fronteira de confiança da emissão é o `name`, e ela é pré-weld. Apertar exige decidir
entre quebrar o clone funcional compilado de `.dsl` (que legitimamente se chama `cpf`)
ou verificar equivalência por amostragem contra o spec do registry — escopo próprio,
não carona de rename. O weld **estreitou** o buraco: de "coincidir o name" para
"coincidir name e wire_id". Pinada em `TestLacunaImpostorDuckType`.

## Consequências

**A favor**
- Corta 31% do artefato no regime de payload minúsculo, e **destrava a nature** em N ≥ 11
  (onde hoje ela é suprimida pelo próprio nome).
- Fecha uma classe de corrupção com erro enganoso (nomes hostis).
- Elimina o espaço de divergência entre as 3 gramáticas de parse.
- Separa o que era acidentalmente acoplado: DX legível **e** wire econômico, sem trade.

**Custos / riscos**
- **Format change de grafia** — barato agora (ADR-0024), **caro depois do 1.0**. É o
  único item da rodada com prazo real.
- O flip do FLOOR significa que encurtar o id **muda resultados de competição**: wires
  re-encodados mudam de bytes, e alguns passam a emitir header de spec onde antes
  emitiam core. Pins criados no weld (`TestWireIdDoisPlanos`): N=10 core, N=11/12 `:dt`.
- Wires históricos com `:data-iso` (14 `.tcf` commitados em labs) ficam como história;
  decodam pela válvula out-of-band já existente (`decode(w, nature=…)`), **exceto pelo
  `view`**, que não tem essa válvula — documentar, não consertar.
- **Não** mexe em `cpf`/`cnpj`/`ip`: já cumprem, e a economia seria 0,2–1,8%.

**Migração** (medida): 1 string em `natures/data_iso.py` · 3 asserts literais em
`tests/test_natures.py` · docs · 1 linha semeando o spec no registry gadget (gap
pré-existente: ele não semeia `data-iso`). **Baselines byte-pinned NÃO re-pinam** —
verificado: zero nature nos suites de regressão/snapshot.

## Alternativa considerada e descartada

**Um nome só, curto** (`dt` também na API). Descartada: joga fora a legibilidade do
código sem ganhar byte nenhum — o nome da API nunca esteve no wire. Foi o erro de
enquadramento que originou este ADR.
