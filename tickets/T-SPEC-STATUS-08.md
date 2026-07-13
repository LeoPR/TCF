---
title: T-SPEC-STATUS-08 — status dos specs (2 abordagens) antes do teste em massa; decisão do que fecha no .8
status: in-progress (revisao cadastral 2026-07-12; conjunto canonico atual preservado)
priority: P1
created: 2026-07-12
updated: 2026-07-12
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-OPT-INFERENCE.md
  - tickets/META-TYPE-ENCODERS.md
  - docs/adr/0015-natures-templated-checked-weld.md
  - src/tcf/natures/templated_checked.py
  - experiments/lab/dirty/notas/specs-capacity-map.md
---

# T-SPEC-STATUS-08 — onde os specs estão, pra decidir o que fechar antes do teste em massa

> **DECIDIDO (owner 2026-07-12): OPÇÃO A.** Só CPF/CNPJ (já welded) no `.8` — o material reporta
> CNPJ (receita REAL) e CPF (sintético-teto), COM o caveat medido no F4 (a nature CNPJ piora a
> tabela em dado real). NENHUM spec novo no `.8` (zero core novo, zero risco no tail). Os clássicos
> que cabem por construtor (CEP/PIS/renavam/título/CNH) e os que precisam máquina nova
> (telefone/RG/placa) ficam registrados aqui + na linha FILTROS-POPULARES do ROADMAP → **`.9`**,
> abertos só quando houver dataset real com a coluna (senão repete o gap sintético-vs-real). O F6
> DEVE carregar o caveat "nenhum clássico, nem CNPJ, é ganho de tabela garantido em real".
> Pré-requisitos p/ qualquer spec novo (.9): anonimizador §2.3 + gerador estendido — não existem.

> **REABERTURA DE EXPLORACAO (owner 2026-07-12)** — antes do fechamento documental, o owner pediu
> revisar os campos cadastrais mais comuns (CEP, RG, identificacao de motorista, datas de aniversario,
> telefone e codigos sem inferencia natural) e avaliar base64/base96. A decisao inicial A continua
> valendo como baseline: nenhum novo spec foi welded nesta revisao. A evidencia nova esta em
> [`2026-07-12-specs-cadastrais-v1`](../experiments/lab/dirty/2026-07-12-specs-cadastrais-v1/).

**[dispositivo→registro]** Pedido do owner (2026-07-12): "quero ver o status dos specs, pra poder
lançar com os datasets. Os specs tinham duas abordagens: (1) revisão da LINGUAGEM pra ficar
generalista e fácil de adaptar a qualquer acoplamento; (2) usar algo mais 'encaixotado' como o CPF
já tem — clássicos: CNPJ, CEP, telefone, RG, CPF e outros códigos brasileiros. Quero fechar essas
coisas antes de partir pro teste em massa."

Fonte: survey de 3 agentes (2026-07-12, read-only, file:line verificado; 1 re-rodado por resposta
degenerada — o re-survey CORRIGIU um erro material do primeiro sobre o `check_fn`).

## Abordagem 1 — LINGUAGEM generalista (specs induzidas)

**Estado: mapeada, confirmada-CONCEITUAL, gated `.9`.** Não é código a rodar no teste em massa.

- Framework = `T-OPT-INFERENCE` (open, reframe owner 2026-07-06: tipo/base-hex/nature são a MESMA
  coisa, espectro de specs justificadas por COMPRESSÃO ou ACELERAÇÃO, induzidas com segurança sse
  round-trip). Nota-mãe: `tipos-como-specs.md` (escada string→int/float→enum-bN→nature rica; regra
  universal = RT; gabarito propõe-e-confirma). Meta-grupo `H-TYPE-00..05`; motor `spec_bin/bN`.
- Achado que calibra: em TCF TEXTUAL a compressão de tipo é modesta (bool ~6B); o forte é
  ACELERAÇÃO + espaço binário V2-L. Gate `H-TYPE-03` aberto (decisão de produto do owner:
  "terminal é representativo?"). Medições fechadas (D3 N=8: 8.8% terminal / 1.7% pós-brotli).
- **Trilho literal de DSL de spec** (a "linguagem generalista" no sentido estrito) = W4 "TCFL"
  (`resegmentacao-workstreams-2026-06-27.md`) + `filtros-dsl-plano.md` — registrado, deferido 2.0.
- **Pro teste em massa AGORA**: só o que está welded (natures ADR-0015 + self-describing `:id`
  ADR-0027 + SPEC_REGISTRY). Todo o resto = `.9`, gated. Nada a fazer aqui pro `.8`.

## Abordagem 2 — clássicos BR encaixotados

**Achado central (verificado): o gargalo NÃO é a máquina, é DADO.** As máquinas welded já cobrem
5 dos 7 clássicos por CONSTRUTOR, sem tocar o core — mas nenhum hub tem coluna de clássico BR além
de CPF/CNPJ, e o gerador só produz cpf/cnpj. Logo o gate de weld (≥15% em 2+ reais, sobrevive a
brotli) só é atingível HOJE por CNPJ.

### O que a máquina suporta (correção do re-survey)

- **`check_fn` é PARÂMETRO LIVRE do construtor** (`templated_checked.py:58`), NÃO um dict fechado.
  Plugar um DV novo (PIS pesos próprios, algoritmo custom da CNH, título sobre sub-fatias) =
  **só passar `check_fn=` no construtor**. Zero core, zero subclasse. (O dict fechado
  `CHECK_FNS = {mod11-cpf, mod11-cnpj, none}` existe SÓ no gadget DSL `scripts/natures_compiler/`
  — o primeiro agente errou ao chamar a máquina de "biblioteca fechada".)
- Restrição real: algoritmo tem de ser `list[int] -> list[int]` (dígito-int); Luhn/alfanumérico
  não cabe. `zfill(body_length)` no decode (`:104`) preserva zeros à esquerda (habilita CEP).
- **Único toque de core**: registrar o `:id` no `SPEC_REGISTRY` (`natures/__init__.py:56-60`, 1
  linha, SEM collision-check) — e SÓ se quiser o header self-describing público. Uso via
  `spec.encode_value/decode_value` direto = zero core. **Cuidado (meu BUG-13b, lote 4)**: id
  desconhecido no header AGORA É ERRO — um spec novo precisa estar no registry pra o
  `encode/decode` público round-tripar.

### Veredito por clássico (mecânico + dado)

| clássico | DV | cabe na máquina? | dado real? | PII? | veredito |
|---|---|---|---|---|---|
| **CNPJ** | 2× mod-11 | ✅ welded | ✅ receita-cnpj 200k | não | **(a) fecha o gate** — único confirmada-empirica |
| **CPF** | 2× mod-11 | ✅ welded | só sintético | sim | **(a) medível, synthetic-teto** (ressalva sempre) |
| **CEP** | nenhum | ✅ Checked `check_length=0` (zfill salva o zero) | ❌ nenhum hub | não | (b) precisa-gerador; ganho duvidoso |
| **PIS** | 1× mod-11 | ✅ `check_fn=` | ❌ | sim | (b) encaixe limpo, sem dado |
| **Renavam** | 1× mod-11 | ✅ `check_fn=` | ❌ | parcial (veículo) | (b) encaixe limpo, sem dado |
| **Título eleitor** | 2× mod-11 sub-fatia | ✅ `check_fn=` | ❌ | sim | (b) cabe, sem dado |
| **CNH** | 2× custom | ✅ `check_fn=` | ❌ | sim | (b) cabe, sem dado |
| **Telefone** | nenhum | ❌ largura 10/11 variável | ❌ | sim | (c) precisa máquina var-width OU 2 specs |
| **RG** | varia por estado | ❌ formato/DV per-estado | ❌ | sim | (c) precisa decisão de política; não-.8 |
| **Placa Mercosul** | nenhum | ❌ alfanumérico | ❌ | não | (c) precisa máquina alfanumérica nova |

## Evidência nova do F4-mínimo (2026-07-12) — reforça a Opção A

Medição do F4 (`evidencia-0.8/f4-minimo/`, RT 9/9) trouxe um dado que MUDA a leitura de "CNPJ fecha
o gate": a nature CNPJ **piora em dado REAL a nível de TABELA**. Em receita-cnpj (200k→5k, REAL):
sem nature 100121B, com `:cnpj` **107460B (+7339B)** — a coluna cnpj cai de `split` (32665B) pra
`raw` (39999B), porque o corpo base-94 da nature DESTRÓI a estrutura (matriz/filial, prefixos de
mesma empresa) que o split/dict do próprio TCF já explorava. No sintético (br-empresas) a MESMA
nature AJUDA (55.3% vs CSV). O ganho per-coluna de 40.9% do T-DATA-2 (antigo) era isolado; a nível
de tabela em dado real ele REVERTE — mesmo padrão do FILTRO-NUMERO (per-col dilui/reverte). Não
invalida a máquina (RT ok), mas: **nenhum clássico — nem o CNPJ — é ganho de tabela garantido em
dado real**. Isto empurra fortemente pra **Opção A** e é caveat obrigatório do F6.

## Revisao cadastral 2026-07-12 — o que cabe no `.8`

O laboratorio mediu o **blob completo** com prototipos fora de `src/tcf`, sempre com RT. Os hubs
usados nao fornecem RG, CEP ou CNH reais; `br-identidades` e' sintetico e TPC-H e' benchmark
sintetico. Logo os numeros abaixo sao capacidade/triagem, nao gate ecologico.

| campo/familia | estado observado | resultado da triagem | recomendacao |
|---|---|---|---|
| **data ISO / aniversario** | `YYYY-MM-DD` ja' entra no split; prototipo base-80 calendar-aware ainda nao existe | pessoas single 5000: 46417 -> 25979 (-44%); multi pessoas/empresas: empate; TPC-H orders: -0.4% | `DateSpec` ISO e' o unico candidato de baixo risco para `.8`, mas so' com validacao de calendario, dois gates reais e aprovacao explicita; caso contrario `.9` |
| **datetime** | formato fixo em amostra publica online-retail | 100 valores: 165 -> 124B (-24.8%) no prototipo | `.9` ou mesma familia de `DateSpec`, apos medir em mais fontes |
| **CEP** | nao tratado corretamente hoje: zero inicial significativo nao pode ser removido | CEP masked random 5000: 59665 -> 32425; sequencial: 33818 -> 31755; sem dado real no hub | `.9`; primeiro criar fixed-width zero-preserving + dataset real |
| **RG** | nao existe formato nacional unico; mascara e politica variam por UF | RG SP-shaped sintetico ganhou, mas isso nao cobre o dominio | `.9`; uma nature nacional seria enganosa |
| **CNH / identificacao de motorista** | numero e campos dependem do documento/politica; valor sem mascara cai hoje em `format_unmasked` | proxy de codigo decimal fixo 11 random ganhou 43%; sequencial empatou com OBAT/HCC | `.9`; criar `FixedDigitsSpec` generica antes de batizar CNH |
| **RENAVAM/PIS/titulo** | alguns cabem em maquina checked com `check_fn`, mas nao ha dataset real nem anonimizador | nao medidos como fontes reais | `.9`, um por vez, com regra e dado reais |
| **telefone** | largura e mascara variam (fixo, movel, DDD, pais) | TPC-H `c_phone` 180006 -> 170851 (-5.1%), benchmark sintetico | `.9`; var-width/normalizacao e fonte real antes do weld |
| **codigo alfanumerico** | sem estrutura semantica, so' vale se alfabeto e largura forem declarados | nao ha ganho universal demonstrado | `.9`; `FixedAlphabetSpec` opt-in, nunca auto-inferido por formato |

### Base64, base80 seguro e base96

O nome historico `BASE94` representa **80 caracteres seguros** depois que a gramatica TCF remove
marcadores e separadores. Para dominios decimais de 8/9/10 digitos, base64, base80 e base96 usam
o mesmo numero de caracteres; em 11 e 15 digitos, base80 ja' empata ou vence base64. Base96 exigiria
caracteres reservados, escaping adicional ou abandonar a promessa ASCII. Portanto nao entra no
wire-format `.8`. A pesquisa `.9` deve preferir uma `FixedAlphabetSpec` com alfabeto seguro explicito,
medir o custo do escape e manter o FLOOR contra dados ordenados.

### Decisao operacional

- O `.8` continua com CPF/CNPJ/IP canonicos e suporte out-of-band coincidente para specs customizados.
- Nenhum RG, CNH, CEP, telefone ou codigo generico entra no registry canonico sem dado real e gate.
- `DateSpec` ISO/calendar-aware fica como **candidato condicional**, nao bloqueia F6 nem a rodada de
  massa. Se aprovado, deve ser um commit proprio, com testes, dois datasets reais e gate completo.
- A rodada de massa acontece depois do fechamento do pacote e do smoke clean-room; a investigacao
  cadastral fica separada dos numeros de closeout.

## Decisão pendente do owner (o que "fechar" significa pro .8)

Como CPF/CNPJ já estão welded, "fechar os specs pro teste em massa" NÃO é abrir spec novo — é
escolher entre:

- **Opção A — conservador (recomendado pro fechamento do .8)**: o material comprobatório reporta
  só CPF/CNPJ (F4 já faz: receita-cnpj REAL fecha o gate; br-identidades sintético = teto). Os
  demais clássicos ficam REGISTRADOS aqui como "cabem por construtor, faltam dado+gerador" → `.9`.
  Zero core novo, zero risco no tail do .8.
- **Opção B — demonstração de capacidade**: adicionar ao F4 1-2 specs sintéticos (CEP/PIS/renavam
  via construtor, RT-provado) como DEMO da máquina — explicitamente rotulado "capability, NÃO
  passa o gate ≥15%/2-reais" (herda o critério do FILTRO-NUMERO). Custa: gerador sintético
  (fora de src/tcf) + 1 linha no SPEC_REGISTRY por spec + anonimizador §2.3 pros que têm DV. Mais
  superfície pra migrar no C1/C2 (rename/consolidação).
- **Opção C — abrir um clássico "de verdade"**: só faz sentido pós-`.8`, quando houver dataset
  real com a coluna (nenhum existe hoje) — senão repete o padrão "sintético não generaliza"
  (anti-incidente 2026-05-21).

## Pré-requisitos que QUALQUER spec novo com DV precisa (registrados)

- **Anonimizador** (§2.3): re-invalidar DV `(dv+1)%10` pra publicar exemplo — NÃO existe, criar em
  `scripts/`. Vale pra CPF/PIS/título/CNH/renavam/CNS.
- **Gerador sintético** estendido: `setup_br_identidades.py` só faz cpf/cnpj — sem `_gen_cep/
  _gen_telefone/_gen_rg`.
- **1 linha no SPEC_REGISTRY** por id novo (core) + collision-check inexistente (dict sobrescreve
  calado — anotar como risco se crescer).

## Critério de aceite

- [x] Owner escolheu **A** (2026-07-12): `.8` só com CPF/CNPJ welded; nenhum spec novo foi welded
  nesta revisao cadastral. `DateSpec` ISO ficou como candidato condicional separado.
- [x] Clássicos (b)/(c) registrados aqui + cross-ref na linha FILTROS-POPULARES do ROADMAP → `.9`.
- [ ] **F6**: caveat obrigatório "nature CNPJ piora a tabela em dado real (F4: +7339B, split→raw);
  nenhum clássico é ganho de tabela garantido" no README/docs.
- [ ] `.9` (quando abrir): anonimizador §2.3 + gerador estendido ANTES de qualquer spec novo com DV.
