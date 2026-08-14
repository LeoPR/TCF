# O OFFPAD, detalhado — e por que ele sai de cena

**2026-08-14** · o owner pediu o detalhamento do OFFPAD antes de decidir, e observou:
*"eu penso que tem int embutido no date, o que faz sentido em parte."* A observação está
certa, e é ela que resolve o dilema.

---

## 1. O que é o OFFPAD

Um dos três alvos protótipos de spec de inteiro. Ele subtrai de cada valor o **mínimo da
coluna** e preenche com zeros à largura do intervalo:

```
entrada  9223372036854775808, 9223372036854775809, …   (19 dígitos cada)
base     9223372036854775808                            (o mínimo)
corpo    000, 001, 002, …                               (3 dígitos)
wire     #TCF.8 :xioff  /  *600+1|\000                  26 bytes
```

O ganho é real e grande — mas **a base não está no wire**. Ela vivia no objeto do spec, e foi
o que o owner pegou ao abrir `gigante-64bit.str-spec.tcf`. Contabilizando a base, o wire
honesto é 46 B, não 26.

## 2. A observação do owner: o int embutido no date

O `data-iso` faz **exatamente a mesma coisa**:

```
'2026-01-01'  →  '739617'      ordinal = dias desde 0001-01-01
```

O ordinal **é um inteiro**, e ele é um **offset**. A diferença é qual base:

| | base | está no wire? | auto-contido? |
|---|---|---|---|
| `data-iso` | a **época** (0001-01-01) — convenção universal | não precisa, ambos os lados a conhecem | **sim** |
| seq-RLE | a **âncora**, emitida no marcador (`*600+1\|\739617`) | **sim, explicitamente** | **sim** |
| `OFFPAD` | o **mínimo da coluna** — derivado dos dados | **não** | **não** |

Ou seja: o projeto já resolve "offset" de duas formas, e **as duas fazem a informação viajar**
— uma por convenção conhecida, outra por emissão explícita. O OFFPAD era a única que não
fazia nem uma coisa nem outra.

*(De carona, uma tentação descartada com medida: e se o ordinal do date fosse base-94 em vez
de decimal? **2196 B contra 22 B**. A base densa destrói a progressão que o seq-RLE enxerga.
Densidade e aritmética são antagônicas — o `data-iso` escolheu certo ao ficar em decimal, e a
docstring dele já dizia isso.)*

## 3. E aí a pergunta certa: o OFFPAD é necessário?

Testei os cinco casos em que ele ganhava, contra a alternativa mais simples possível — **só
ajustar o `min_len`**, sem spec nenhum:

| caso | núcleo | OFFPAD (honesto) | só `min_len` | quem resolve |
|---|---:|---:|---:|---|
| epoch (+60) | 81 | 40 | **27** (ml=12) | **`min_len`** |
| base alta (1e9+i) | 65 | 37 | **26** (ml=12) | **`min_len`** |
| gigante (2⁶³+i) | 82 | 46 | **35** (ml=20) | **`min_len`** |
| `1..600` | 36 | 26 | 36 | **PAD** (também dá 26) |
| passo 7 | 48 | 27 | 48 | **PAD** (também dá 27) |

**Em nenhum caso o OFFPAD é a única resposta.** E o wire que o `min_len` produz é limpo e
auto-contido:

```
#TCF.8
*600+60|\1750000000        ← a âncora ESTÁ no wire
```

O que os três primeiros casos tinham não era problema de base — era o **OBAT fragmentando os
dígitos antes do seq-RLE enxergar a progressão**. O offset "resolvia" por acidente: encurtar
os números reduzia a fragmentação.

## 4. Conclusão sobre o OFFPAD

**Sai de cena.** Não porque o ganho fosse falso, mas porque:

- onde ele ganhava por **largura variável**, o **PAD** dá o mesmo resultado e é auto-contido;
- onde ele ganhava por **base alta**, o problema era fragmentação, e o **`min_len`** resolve
  melhor **sem spec nenhum**;
- e ele era o único alvo que quebrava o self-describing do ADR-0027.

Com isso, **os três caminhos que eu tinha listado (A/B/C) deixam de ser necessários** — a
decisão que você ia tomar desaparece. Os dois alvos que sobram (`PAD` e `B94`) são
auto-contidos, e o terceiro mecanismo (`min_len`) nem é spec.

## 5. O que isso muda na fila — e uma reversão minha

No levantamento de 2026-08-13 eu recomendei **não abrir** o `T-MIN-LEN-CANDIDATO` agora,
porque "a maior parte do que ele pegaria é o que o spec de número resolveria melhor". **A
medição de agora inverte isso**: o `min_len` resolve 3 dos 5 casos, e resolve *melhor* que o
spec. Ele deixa de ser redundante com o spec de int e passa a ser **complementar** — cada um
cobre um regime diferente:

| regime | quem resolve |
|---|---|
| progressão + largura variável | **PAD** (spec) |
| progressão + base alta / dígitos que não informam | **`min_len`** (núcleo, sem spec) |
| sem progressão + largura fixa | **B94** (spec) |
| baixa cardinalidade | bN (já funciona) |

## 6. Falta algo antes de um lab clean?

**Sim, duas coisas** — e por isso eu não abriria o clean ainda:

1. **A frequência dos gatilhos em corpus real.** Tudo até aqui é sintético controlado, por
   escolha. O corpus dita o default — foi a regra que valeu para data, e vale aqui. Sem isso,
   um weld estaria escolhendo default no escuro.
2. **O desenho mudou hoje.** O OFFPAD saiu, o `min_len` entrou. Levar ao clean um desenho que
   acabou de mudar é o caminho para refazer o clean.

O clean é para **prototipar o que já vai soldar** (é a definição que você deu). Ainda não
estamos aí: falta o corpus real dizer quais gatilhos importam, e falta decidir se `PAD`+`B94`
viram um spec com parâmetro ou dois specs irmãos.

**O que eu faria a seguir**: medir os gatilhos em `Z:/tcf-data/` (dirty, barato, fecha a
lacuna que os três labs declararam), e só então o clean.
