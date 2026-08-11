# Nomes de spec · lazy view com bypass · encode em pulsos — revisão medida

**Data**: 2026-08-10
**Tipo**: nota de revisão + direções de pesquisa (nada é `.8`; nada foi soldado)
**Origem**: três pontos levantados pelo owner antes de passar pro próximo tipo.
Tudo abaixo foi **medido agora**, com `encode`/`decode` reais e RT conferido.

---

## 1. Nomes de spec — procede, e o custo é maior do que parece

### O estado

**Não há formalização nenhuma.** `name: str` nos três protocolos de spec, sem limite, sem
validação, sem grafia definida. O ADR-0027 fixou *onde* a tag mora (`#TCF.8 <col>:<spec>`),
nunca *como* ela se escreve.

| spec | tag no wire | custo |
|---|---|---:|
| `ip` | ` :ip` | 4 B |
| `cpf` | ` :cpf` | 5 B |
| `cnpj` | ` :cnpj` | 6 B |
| **`data-iso`** | ` :data-iso` | **10 B** |

Três de quatro já cabem numa regra de 8; **só o `data-iso` destoa** — e ele é o único com
hífen, que custa 1 byte e não informa nada.

### O custo real, medido

Numa coluna de data comprimida o artefato inteiro tem 32 B. A tag come **28%**:

| n | wire | `:data-iso` | com `:dtiso` |
|---:|---:|---:|---|
| 12 | 47 B | 9 B = **19,1%** | 44 B (−6,4%) |
| 600 | 32 B | 9 B = **28,1%** | 29 B (−9,4%) |
| 6000 | 33 B | 9 B = **27,3%** | 30 B (−9,1%) |

Isso bate direto na diretriz de **payload minúsculo** (`project_byte_level_compression_focus`,
O-FMT-15/16): 3 bytes num artefato de 32 é quase um décimo do arquivo.

### A proposta — e o contraponto que ela precisa

**Regra sugerida**: `[a-z0-9]{2,8}`, **sem hífen**, validada no registro do spec.
`data-iso` → **`dtiso`**. Os outros três já cumprem.

**O contraponto**: nome curto compete com **auto-descrição**, que foi a razão do ADR-0027 e
do ADR-0034 (o arquivo se explica sozinho em vez de depender de quem o produziu). Há um
piso de legibilidade: `dtiso` ainda é adivinhável, `dti` não é. Por isso **8, não 4** — o
limite existe para impedir o próximo `data-iso-extendida-br`, não para espremer ao máximo.

**Custo de mudar**: é grafia no wire → format change. Barato agora (ADR-0024: baselines
re-pináveis pré-1.0), **caro depois do 1.0**. Se for pra fazer, é agora.

**Aberto**: o nome de COLUNA (`<col>:` antes da tag) fica de fora — é dado do usuário, não
nosso. E vale decidir se o registry passa a rejeitar nome fora da regra (fail-loud) ou só
avisa.

---

## 2. Lazy view + bypass heurístico — a ideia tem base nova, e ela nasceu do spec

### O estado: funciona, mas materializa tudo

`tcf.view` existe e é soldado (`LazyTCF`/`Filtered`, read-only, `#TCF.8M`). O filtro de data
que o owner descreve **já roda**:

```python
lz = view(wire)
lz.where("dt", pred=lambda d: d.startswith("2025")).count()   # 365 linhas ✓
lz.where("dt", pred=lambda d: d[5:7] == "03").count()         # 93 linhas  ✓
lz.where(...).select(["v"])                                    # outra coluna, mesmas linhas ✓
```

**Mas `materialized_bytes` = 100%.** Ele decodifica a coluna inteira e filtra depois. O
"bypass heurístico" não acontece.

### Por que não acontece — e o que mudou

As NOTAS do `view.py` registram a tentativa de 2026-06-16:

> *"agregar os runs `*N|` direto no modo-tcf **NÃO** é barato/separável — OBAT+HCC
> entrelaçam o valor com refs de outras linhas (…) **0 colunas tcf "clean-numeric"**"*

Naquele momento a conclusão estava certa: não havia coluna que fosse um run limpo. **O spec
de data criou exatamente essa condição** — medido agora:

| coluna | corpo | forma |
|---|---|---|
| diário, 900 valores | **1 linha** | `*900+1\|\739617` |
| dias úteis, 900 valores | **1 linha** | `*900~1,3,1,1,1\|\739617` |

Um marcador. Nada entrelaçado. **O que o L3 procurou e não achou, o spec fabrica.**

### A pesquisa que isso abre

O payload é **ordinal monotônico**. Um filtro de data vira **intervalo aritmético**:

- `where(ano == 2025)` = `[toordinal(2025-01-01), toordinal(2025-12-31)]`
- num run `*N+d|base`, os valores são `base + i·d` → responder "quais índices caem no
  intervalo" é **duas divisões**, não 900 comparações
- num run periódico `*N~pad|base` a soma por ciclo é constante → mesma ideia, com o resto
  do ciclo resolvido por tabela de `p` entradas

Ou seja: `count`, `where` e até `min`/`max` de data respondíveis **em O(1) no tamanho do
run**. E encadeia com o `select` de outra coluna, porque o formato é row-aligned por posição.

**A generalização**: isso não é de data — vale para **qualquer spec cujo alvo seja um
inteiro monotônico**. É a contrapartida de leitura do "spec orienta": o spec que declara o
eixo também declara que o payload é ordenável, e o lazy usa isso.

**Ressalvas honestas**: (a) só serve na rota `#TCF.8M` (o `view` é multi-col); (b) exige que
a coluna tenha virado run limpo — se a válvula produziu literais no meio, o run quebra e o
bypass vira parcial; (c) o predicado do usuário é uma lambda opaca — o bypass precisa de uma
forma **declarativa** de filtro (`ano=2025`, `entre(a,b)`) para poder raciocinar sobre ele.
A (c) é a decisão de design, não a aritmética.

---

## 3. Encode em pulsos — o wire já aceita; o bloqueio registrado é de outra rota

### O teste decisivo

O desenho do owner, verificado:

```
#TCF.8 :data-iso            #TCF.8 :data-iso
*600+1|\739617       →      *300+1|\739617
                            *300+1|\739917
```

**`decode` aceita os dois e devolve os mesmos 600 valores.** RT verificado em 1, 2, 4, 6,
12 e 60 pulsos. **A gramática está pronta** — o que falta é o encoder ter um ponto de
decisão "parar aqui e emitir".

### O preço da latência, medido

| pulsos | bytes | vs 1 pulso | o 1º pulso entrega |
|---:|---:|---:|---|
| 1 | 32 | — | 100% (só no fim) |
| 2 | 47 | +15 B | 50% |
| 4 | 77 | +45 B | 25% |
| 6 | 107 | +75 B | 16% |
| 12 | 185 | +153 B | 8% |
| 60 | 857 | +825 B | 1,7% |

**Cada pulso custa ~15 B** (o marcador repetido). É uma reta: `bytes ≈ 32 + 15·(p−1)`. Isso
dá a régua exata do trade latência × tamanho — e permite um modo `deadline_ms` calcular o
corte em vez de chutar.

### O bloqueio do V2-J **não** cobre o caso do owner

O ADR-0018 (V2-J, streaming) registra:

> *"Bloqueador formato: header `# size=name,...` atual exige saber sizes ANTES do body"*

Isso é **multi-col**. O single-col flat com spec tem header `#TCF.8 :data-iso\n` — **sem
sizes**. O caso exato que o owner desenhou (stream de datas, coluna única) **não está
bloqueado pelo formato**. O registro atual não faz essa distinção, e por isso o item parecia
mais longe do que está.

### A restrição de design que o periódico impõe (nova)

Cortar um run periódico não é livre. Medido com `*600~1,3,1,1,1|` (p=5):

| corte | rotação | pad do 2º pulso | RT |
|---:|---:|---|---|
| 300 | 0 | `1,3,1,1,1` | ✓ |
| 301 | 1 | `3,1,1,1,1` | ✓ |
| 250 | 0 | `1,3,1,1,1` | ✓ |
| **7** | 2 | `1,1,1,1,3` | **falha** |

Duas regras saem daí:

1. **O pad do 2º pulso rotaciona por `corte mod p`.** Corte múltiplo do período mantém o
   pad; fora de fase exige rotacionar — e a rotação tem de continuar canônica sob o guard
   do ADR-0040.
2. **Pulso periódico tem tamanho mínimo: `2p+1` valores** (o guard exige 2 ciclos
   completos). Com p=5, um pulso de 7 é ilegal — teria de cair no marcador uniforme ou em
   literais. **Um modo de baixa latência não pode cortar em qualquer lugar.**

### Onde isso já estava registrado

- `V2-J` (ADR-0018, 2.0) — pipeline streaming, com o bloqueio multi-col acima.
- `H-ENCODE-DEADLINE-01` (2026-07-16) — *"encode em pulsos por deadline (~1ms); a linguagem
  permite, o código não; saída não-canônica → modo de perfil"*. **O owner já tinha dito
  isso**; esta nota confirma com número e acrescenta o que é/não é bloqueado.
- `T-ONLINE-NESS-BENCH` — o vetor de online-ness que o `bench_perf` não mede.

---

## 4. O que dá pra pesquisar agora (ordenado por custo)

| # | pesquisa | custo | por que agora |
|---|---|---|---|
| 1 | **Regra de nome de spec** (`[a-z0-9]{2,8}`, sem hífen) + renomear `data-iso`→`dtiso` | baixo — grafia + re-pin | 9,4% do artefato em payload pequeno, e é **format change: barato só até o 1.0** |
| 2 | **Bypass aritmético no lazy** para run de spec monotônico | médio — read-only, não toca o formato | a condição ("run limpo") **passou a existir**; o L3 de 2026-06 concluiu contra um corpus que não a tinha |
| 3 | **Filtro declarativo** (`ano=`, `entre=`) no `view` | médio | pré-requisito do #2 — sem ele o predicado é lambda opaca |
| 4 | **Modo `deadline_ms` no single-col** com corte alinhado ao período | médio | o wire já aceita; a curva de custo é linear e conhecida; o bloqueio do V2-J é de outra rota |
| 5 | Pulso em multi-col | alto | aí sim esbarra no `size=` do header (V2-J, 2.0) |

Nenhum é `.8`. **#1 é o único com prazo** — depois do 1.0 o nome congela.
