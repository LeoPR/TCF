# Três frentes, onde atacar — nome de spec · view · pulsos×estrutura

**Data**: 2026-08-12
**Tipo**: consolidação de pesquisa profunda (3 lentes, tudo medido com `encode`/`decode`
reais; sondas no scratchpad, read-only em `src/`)
**Origem**: pedido do owner — *"focar bem no nome de spec e revisar compatibilidade e
estrutura do view (…) pulsos: como afeta a estrutura do arquivo, pode ser interessante
ver agora"* — com a instrução de achar **onde atacar**, mesmo dentro do `.8`.
**Antecedente**: [`2026-08-10-nomes-lazy-e-pulsos-revisao.md`](2026-08-10-nomes-lazy-e-pulsos-revisao.md)

---

## A. NOME DE SPEC — o foco

### O que o censo achou (além do custo já conhecido)

1. **O id viaja em TRÊS gramáticas de wire**, com parses divergentes:
   - single-col `#TCF.8 [nome]:id` — partition no **primeiro** `:` (`decoder.py:217`)
   - multi-col `...=col:id` — rsplit no **último** `:` não-escapado (`multi/core.py:208`)
   - `.8H` `:size:id` — id até `,]}`  (`hierarchical.py:718-728`)

   Divergência latente medida: nome `a:b` RT-quebra em multi e passaria em `.8H`.
2. **Zero validação** — nomes hostis corrompem com erros ENGANOSOS: `,` no nome explode
   como "referência a fragmento inexistente" (parece corrupção de corpo!), `:` parseia
   coluna errada, `\n` dá "bytes excedentes", `}` quebra o `.8H`.
3. **O achado forte — o comprimento do id FLIPA o FLOOR**: em N=11–15 datas diárias, a
   nature **PERDE** com `data-iso` (o blob com header perde do core: 47 B) e **VENCE**
   com `dt`/`d` (43–44 B). O nome longo **suprime a própria nature** exatamente no
   regime de payload minúsculo (O-FMT-15/16). `dtiso` captura 2 desses flips; `dt`/`d`
   capturam 5.
4. O rename **libera limpo**: wire velho falha **loud** com mensagem acionável; baselines
   byte-pinned **não re-pinam** (zero nature nos suites de regressão); e a válvula
   runtime já existe — `decode(wire_velho, nature=dataclasses.replace(SPEC, name="data-iso"))`
   faz RT sem git checkout (`decoder.py:71`).

### A proposta

**ADR novo com a regra**: id de wire casa **`^[a-z][a-z0-9]{0,7}$`** — minúscula inicial,
1–8 chars, sem hífen — validado **fail-loud em dois pontos**: no registro (`_register()`
que recusa grafia inválida E colisão) e na emissão (fecha o buraco dos nomes hostis).

**Minúsculas-only é decisão carregada, não estética**: reserva MAIÚSCULAS e pontuação
para os sufixos de rota (polaridade `!`, bN `B1c8`) que o `T-NATURE-CANDIDATO-BN` pode
trazer para a MESMA linha do header — **desarma lexicalmente o conflito** antes de
qualquer weld. Custo zero hoje; re-grafia cara depois.

**Migração `data-iso` → id novo**: 1 string (`data_iso.py:66`) + 3 asserts literais +
docs + 1 linha semeando o spec no registry gadget (gap pré-existente: o gadget não
semeia `data-iso`) + a mensagem de `view.py:154`. De carona: `view.py:156` usa
`spec.decode_value` cru em vez do wrapper que trata None-slot (bug latente, 1 linha).

**Namespace**: ids de 1 char são 26 slots — o ADR leva tabela de reserva (core nunca usa
prefixo `x`; terceiro que quiser id no wire usa `x…`).

### As DUAS decisões que são do owner

| decisão | opção 1 | opção 2 |
|---|---|---|
| **tamanho** | `dtiso` (5): legível, −9,4%, captura 2 flips | `dt` (2): pronunciável, padrão do `ip`, −3 B/artefato a mais, captura **5** flips |
| **desenho** | rename simples (o wire leva o nome da API) | **híbrido**: id curto no wire + nome legível na API/telemetria — único que fecha "cada byte conta" E DX; custo: wire opaco (`:d` só se explica via registry) |

`cpf`/`cnpj`/`ip` não mudam: já cumprem a regra; economia seria 0,2–1,8%.

---

## B. VIEW — compatibilidade e estrutura

### A matriz (executada, não lida)

**Abre**: as 8 variantes `#TCF.8M` (default, `@`dict, `%`split, `:spec` com corpo run,
`:spec` com corpo **periódico `*N~`**, spec+dict, drop_names, min_header).
**Recusa** (num único `startswith`, `view.py:67`): as 11 formas não-M — flat, polarizado,
bN, denso b1/b2, tipados, `nB`, `bB`, **single-col com spec**, `.8H`, órfão.

### Os três fatos novos

1. **BUG real, silencioso, emissível HOJE** (`.8`): coluna nature que vence em modo dict
   (`#TCF.8M@1a9=dt:data-iso,@v` — emissível com datas de baixa cardinalidade) responde
   `where`/`group_count` pelo **payload ordinal**, não pelo valor revertido:
   `where('dt','2025-06-20')` = **0** onde a verdade é **133**; `group_count` devolve
   chaves `'739266'`. Resultado errado **sem erro** — a pior classe pela régua do
   projeto. Fix: ~6 linhas em `view.py::_dict_parts` (reverter as K únicas).
2. **Single-col no view é DISPATCH-ONLY** — um `LazyTCF` montado à mão sobre
   `#TCF.8 :data-iso` roda RT/where/sum perfeitos, **inclusive wire PULSADO 2×300**
   (paridade com o decode por construção, via `_decode_column`). ~20–25 linhas no
   `_parse`, com fail-loud dedicado para tipados/polarizado/`.8H`/órfão. **É o caso de
   stream do owner — e as frentes 2 e 3 se encontram aqui sem tocar formato.**
3. **Bypass aritmético medido**: filtro `ano=2025` num run de spec = **12 µs contra
   12.285 µs (1000×), 0 B materializados**, índices idênticos, compõe com `sum` de outra
   coluna via `Filtered(parent, idx)`. O caminho `.9`: `where(col, entre=(lo,hi))`
   resolvido em 3 camadas (aritmética no run / K únicos revertidos no dict / fallback).

E uma propriedade a registrar: o view **acompanhou o ADR-0040 sem mexer em nada**
(corpo periódico `*N~` lido via fonte única `_decode_column`) — paridade por construção.

### Restrições que o view impõe ao `T-NATURE-CANDIDATO-BN`

- Marcador de modo novo no meta multi = **pontuação, nunca letra**: token `B178=col` é
  **hex-parseado calado** pelo `_parse_meta` (letra a–f é size válido!).
- Solda simétrica: `_parse_meta` E `view._col` no mesmo weld.

---

## C. PULSOS × ESTRUTURA — o que se decide agora

### A matriz de pulse-friendliness (48 colunas reais)

| classe | rotas | pulsável? |
|---|---|---|
| header emissível-cedo | **spec** `#TCF.8 :id` · flat `#TCF.8` · **tipado-core `#TCF.8n`** (fato novo) · órfão | **SIM, hoje** — RT verificado |
| sufixo-no-fim | polarizado `!!`, e o flat quando o min() elege polaridade/bN | não sem decisão |
| count/size no header | denso b1/b2 · bN `B1c8` · `bB`/`nB` · `.8H` (#count) · `.8M` (size=) | **não** — count-no-fim = format change (V2-J/2.0) |

**Custo do modo-pulso na flat**: +4,73% no corpus real — e **2/3 é forfeit de bN** (até
+262% em coluna categórica), 1/3 polaridade. Lição: o perfil de pulso roteia **por
coluna** — categórica de baixa cardinalidade não entra em pulso cegamente.

### O conflito com o `T-NATURE-CANDIDATO-BN` — resolvido, e de graça

Medido no corpo transformado das colunas reais: **em série monotônica (o regime onde o
pulso vive) o FLOOR da polaridade já recusa o sufixo sozinho** — a polaridade só venceria
em coluna desordenada (−4,7 a −6,1%), e o bN **nunca** vence o corpo transformado.

**Resolução (b), custo zero no regime de pulso**: quando o `T-NATURE-CANDIDATO-BN`
soldar, polaridade/bN entram na rota spec como candidatos **condicionados ao perfil
batch** (o default de hoje), nunca `min()` incondicional. Preserva por construção a única
rota com header emissível-cedo. (Se o plumbing de perfil atrasar, a constraint vale com
default batch — nada muda até o perfil existir.)

**Resolução (c) — trailer no fim — REPROVADA**: o decoder teria de bufferizar o corpo
inteiro antes de interpretar a 1ª linha; é a mesma álgebra (17×) que rebaixou o modo C.
Registrado para o `.9` não reintroduzir trailer como "limpeza natural".

### As outras decisões de estrutura

- **Leniência não-contratada** (descoberta): commit precoce de sufixo corrompe
  SILENCIOSAMENTE (`ab!cd` → `abcd`, sem erro), mas o parser aceita escape `\!`
  não-emitido — canonicidade por acidente. **Fechar (fail-loud) ou contratar** — a
  escolha decide se a via "sufixo precoce + escape" existe. Tem prazo.
- **Canonicidade E4**: wire pulsado = **"emissível não-canônico"**, espelho do modo C
  ("decodável não-emitido"). **Sem flag de header** — decode não precisa, a assinatura é
  detectável por scan raso, e re-encode canonicaliza (verificado byte-igual). Exigência
  prática é gate: baseline byte-canonical **nunca pinna saída pulsada**.
- **Fase do periódico**: 100% estado de encoder (fase = emitidos mod p; rabo <2p+1 sai
  em literais, RT ok). **Zero formato.** `deadline_ms` fica adiável de verdade.
- **Multi-col por coluna** (sem format change): +6,4% (fecha-coluna) a +28,8% (pulso
  pleno) — só serve produtor colunar; fica no 2.0 **como teto** para propostas futuras.

### O colateral que virou ticket

**O `min()` por coluna do `.8M` não consulta o bN**: soma de wires single-col = 2.784 B
vs `.8M` = 3.231 B no adult-census (**−13,8%**), mesmo pagando header+nome por coluna.
É a **5ª ocorrência** da classe *"o candidato existe e a rota não consulta"*
(T-BN-TIPADO · FLOOR-da-nature · T-SPLIT-SINGLE-COL · T-NATURE-CANDIDATO-BN · agora o
`.8M`). Atualizado no `T-BN-MULTICOL`.

---

## O menu de ataque consolidado

| # | ação | tier | mexe em `src/`? |
|---|---|---|---|
| 1 | ADR da regra de nome + validação 2 pontos + rename `data-iso` | **agora-.8** | sim — **aguarda aprovação** (+ decisão dtiso/dt/híbrido) |
| 2 | fix do BUG view nature+dict (~6 linhas) | **agora-.8** (bug soldado) | sim — **aguarda aprovação** |
| 3 | dispatch single-col no view (~20-25 linhas; lê pulsos de graça) | **agora-.8** | sim — **aguarda aprovação** |
| 4 | CONSTRAINT no weld do `T-NATURE-CANDIDATO-BN` (perfil batch) + grafia de modo (pontuação, nunca letra) | **decisão de estrutura, agora** | não (é constraint de weld futuro) |
| 5 | fechar/contratar a leniência `\<pontuação>` | decisão-owner, com prazo | depende |
| 6 | bN como 5º candidato do `.8M` (13,8%) | `.8` (classe floor) | sim — ticket irmão |
| 7 | filtro declarativo `entre=` + bypass aritmético (1000×) | `.9` | sim |
| 8 | `deadline_ms`, pulso multi-col | `.9` / 2.0 | — |
