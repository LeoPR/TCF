# ADR-0041 — Spec em TRÊS planos: nome de código, id de wire, e o carimbo

- **Status**: proposto (2026-08-12) — **aguarda aprovação de weld do owner**
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

### 2. Regra de grafia do `wire_id`

```
wire_id  ::=  ^[a-z][a-z0-9]{0,7}$        # minúscula inicial, alfanumérico, 1-8
```

Validado **fail-loud em dois pontos**: no **registro** (recusa grafia inválida *e*
colisão) e na **emissão** (fecha o buraco do §Contexto-2 para spec de terceiro).

**Minúsculas-only é decisão carregada, não estética**: reserva MAIÚSCULAS e pontuação
para os sufixos de rota que podem passar a compartilhar a linha do header — polaridade
(`!`, ADR-0035) e bN (`B1c8`, ADR-0036), se o `T-NATURE-CANDIDATO-BN` soldar a rota
plena. Fixar o charset agora custa zero e evita re-grafia depois.

Sem hífen: ele custa 1 byte e não informa (era o único caractere que fazia `data-iso`
estourar 8).

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

**Não decidido aqui**: um `force` que deixe a função sobrepor o dado. Fica para estudo
(direção do owner: *"ainda não sei quem tem prioridade… podemos fazer um force depois"*).

### 4. Modo sem-carimbo: aplicar o spec **sem** mandá-lo junto

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
| `dt` | `data-iso` | **proposto agora** (rename) |
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
  emitiam core. Nenhum teste atual pina esses casos — o weld deve criar os pins.
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
