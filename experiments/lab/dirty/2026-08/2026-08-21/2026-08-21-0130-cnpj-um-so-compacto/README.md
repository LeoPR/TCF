# 2026-08-21-0130 — um CNPJ só: o numérico como caso compacto POR VALOR

> ## ⚠ LAB HISTÓRICO — o desenho que ele mede foi SUPERADO no mesmo dia
>
> Este lab mediu **o compacto por valor ainda sob DOIS `wire_id` (`cnpj` legado + `cnpja` unificado)**, desenho superado pelo
> [ADR-0044](../../../../../../docs/adr/0044-cnpj-um-so-alfanumerico.md) horas depois
> (owner: *"a ideia é ter só 'cnpj' mesmo, ou seja nada de ter dois"*). Hoje existe **um**
> `SPEC_CNPJ`, alfanumérico, com o numérico como caso compacto.
>
> **Consequências para quem abrir este lab:**
> - o `run.py` **não roda mais** (importa `SPEC_CNPJ_ALFA`, que não existe mais) — é registro do que foi medido, não script vivo;
> - os wires em `outputs/` com header `#TCF.8 :cnpja` **não decodificam** no core atual: o id
>   saiu do vocabulário fechado e o decode **falha alto** (`ValueError: nature-id desconhecido`),
>   sem corromper. Para lê-los, `git checkout 2e9ab5c9`.
>
> **O que continua valendo deste lab** está no corpo abaixo — as medições são o registro do
> caminho, e o ADR-0044 se apoia nelas.

Evidência do weld [ADR-0043](../../../../../../docs/adr/0043-cnpj-um-so-compacto-por-valor.md),
que refina o ADR-0042 pela direção do owner:

> *"o CNPJ numérico ultimamente será apenas pra legado agora [...] no futuro ele se diluirá
> [...] precisamos firmar um CNPJ só, que será alfa e terá que cobrir o numérico [...] pode
> ser que a gente não consiga fazer uma heurística que sustente isso por muito tempo [...] se
> aparecer alguma oportunidade de expressá-lo menor (por ser numérico) me parece uma boa ideia."*

O argumento estatístico é exato: o numérico é `10¹²/36¹² ≈ 2,1×10⁻⁷` do espaço novo — hoje é
100% do cadastro, amanhã é um resíduo. **Qualquer heurística por coluna calibrada na fração
numérico/alfa tem prazo de validade.** A resposta não é heurística: é **por valor** — corpo
100% decimal grava em base 10 com **7 chars** (payload byte-idêntico ao legado), corpo com
letra grava em base 36 com **10**; o decode distingue pelo **comprimento**. Não há escolha a
errar, logo não há heurística a sustentar.

## G1 — Paridade: 2 000/2 000 payloads numéricos **byte-idênticos** ao `SPEC_CNPJ`

Não é "parecido": os índices do sub-alfabeto `0..9` **são** os dígitos, então o inteiro é o
mesmo e a grafia base-80 é a mesma. Verificado valor a valor em 2 000 CNPJ reais.

## G2 — Dominação na transição (real n=2000 + k injetados; RT em tudo)

| k | legado `:cnpj` | **unificado `:cnpja`** | Δ | fixo ADR-0042 |
|---:|---:|---:|---:|---:|
| 0 | 17 585 | 17 586 | **+1 B** (só o header) | 24 292 |
| 1 | 17 598 | **17 589** | −9 B | 24 292 |
| 100 | 19 060 | **17 892** | −1 168 B | — |
| 500 | 25 007 | **19 277** | −5 730 B | — |
| 2000 | 38 009 | **24 489** | −13 520 B | 24 542 |

O pior caso do unificado é **+1 byte** (o header `:cnpja` vs `:cnpj`), em coluna 100%
numérica. Em todo k≥1 ele vence o legado; e vence o desenho fixo do ADR-0042 em toda a
faixa (em k=0: **−27,6%** contra os 24 292 do fixo).

## G3 — O chooser: **51/51**, o resíduo desapareceu

A mesma varredura (3 sementes × 17 frações × n=2000) que reprovou o desenho anterior
(41/51, erros sistemáticos na faixa 22–25%, pior 3,15%) agora dá **51/51**. Não porque o
chooser ficou esperto — porque **a escolha deixou de existir**: o payload do unificado é ≤ o
do legado em todo valor (7=7 no numérico; 10 < 1+18 no alfa), então só resta o empate da
coluna 100% numérica, que fica com o legado por 1 B de header e byte-compat.

## G4 — Minúscula: medido, e **não soldado** (classe CONTRATO)

O domínio oficial é **maiúscula-only** — a NT Conjunta 2025.001/XSD valida
`[0-9A-Z]{12}[0-9]{2}`; minúscula **não pertence ao universo**, é variante de
**representação** (a prática do ecossistema é normalizar para maiúscula *antes* de validar).

| coluna 100% minúscula (n=2000) | bytes | vs raw |
|---|---:|---:|
| hoje (literal, byte-RT intacto) | 38 009 | +0,03% |
| sob contrato case-fold | 24 491 | **−35,55%** |

O contrato compraria **35,6%** — mas canonizar a saída (`12.abc…` entra, `12.ABC…` sai)
**perde o RT byte-canonical**, que é constituição do projeto. É exatamente a classe
CONTRATO do `sort_by`/`drop_names`: lossless como *identificador*, não como *string*.
Registrado como **H-15-06**, aguardando a assinatura de contrato
(`T-FMT-CONTRACT-SIGNATURE`). Hoje minúscula cai em literal: não ganha, nunca corrompe.

## Revisão adversarial PRÉ-commit (workflow, 11 agentes) — 5 achados, 5 consertos

Três lentes independentes sobre o diff + refutação adversarial de cada achado (8 brutos →
5 confirmados por execução, 3 refutados). Todos consertados **antes** do commit:

1. **[média] Sub-alfabeto base 1 → decode NÃO TERMINA.** `alfabeto_compacto='0'` construía;
   payload adulterado de 1 char travava o processo para sempre (`n%1=0, n//1=n` — provado
   por timeout). Guarda nova: `len(alfabeto_compacto) >= 2`.
2. **[média] Sub-alfabeto vazio + comprimento 0 → IndexError.** Construía por vacuidade
   (`0**12=0 ≤ 80**0=1`); `decode_value('')` roteava pro ramo compacto e crashava em
   `abc[0]`, onde o contrato é pass-through. Guardas: não-vazio + `encoded_length_compacto ≥ 1`.
3. **[baixa ×2] "Subconjunto próprio" prometido, check não-estrito.** `set(ac) <= set(alfabeto)`
   aceitava igualdade — o ramo pleno virava código morto calado. Agora `<` estrito, casando
   mensagem com código.
4. **[baixa] Docstring do módulo desatualizada** — dizia "5-7 chars"; agora declara o
   por-valor (7/10) do ADR-0043.
5. **[baixa] O "+1 B" dos docs não tinha teste.** Verificador confirmou o fato por execução
   e agora `test_header_e_o_unico_byte_de_diferenca_no_numerico` o pina.

Nenhum dos 5 atingia os specs embarcados (as guardas barram specs *novos* malformados) — mas
o `__post_init__` existe exatamente para isso, e não barrava. Os 3 refutados eram
comportamento contratado (decode tolerante de não-canônico; literal fallback).

## Não medido (declarado)

- Volume futuro (H-15-03) e corpus real alfanumérico (H-15-04) seguem abertos.
- O interior do wire da nature (payloads passam pelo core) segue não-dissecado.
- Prevalência real de CNPJ minúsculo em dados brutos — o G4 é sintético de controle.

## Evidência

38 arquivos em [`inputs/`](inputs/)+[`outputs/`](outputs/), wires com roundtrip, portão
anti-órfão por conjuntos. [`resultado.json`](resultado.json) com os 4 gates. Asserts duros
no próprio run (`b2−b1 ≤ 1` em todo k; chooser sem erro; paridade valor a valor).

## Conexões

- [ADR-0043](../../../../../../docs/adr/0043-cnpj-um-so-compacto-por-valor.md) ·
  [ADR-0042](../../../../../../docs/adr/0042-cnpj-alfanumerico-dois-specs.md) (o desenho que este refina)
- Labs anteriores do arco: [`2350`](../../2026-08-20/2026-08-20-2350-cnpj-alfanumerico/) (descoberta) ·
  [`0030`](../2026-08-21-0030-cnpj-alfa-controle/) (controle)
- `T-FMT-CONTRACT-SIGNATURE` (a assinatura que o H-15-06 espera)
