# Datetime — os cinco planos, e o que a medição faz com eles

**2026-08-15** · ciclo de avaliação pedido pelo owner, **antes** de um novo lab.

> *"uma coisa é o tipo da fonte, outra é ele já transportado pra dentro da linguagem no
> dataset, outra é o spec ter facilidade de ler um padrão (ou um padrão limitado que podemos
> eleger), outra é ele transformar essa data só para tratar internamente, por fim é a forma do
> decode, que pode entregar a forma nativa da entrada, ou entregar como tipo datetime **sem
> compromisso com a entrada, bastando manter um formato com mesma resolução**."*
>
> *"o tcf pode tratar datetimes de forma barata, igual ao date — ou seja, uma lib nativa bem
> objetiva que, **se for muito rápida** (assim como no date), pode aceitar os formatos que
> tiver."*

**Tipo**: [probatório] avaliação. Nenhum lab novo, nenhum weld, `src/tcf` intocado.

> ## ⚠️ 2º ciclo — a dinâmica RECUPERADA corrige este documento
>
> O owner, depois da 1ª versão:
>
> > *"já foi discutida muitas vezes no bool, no bN e inclusive no date, então já está decidido,
> > bem entendido e inclusive **feito**. O datetime basta seguir a mesma lógica. Não precisa
> > reentender nada, só precisa **pesquisar e recuperar a dinâmica** disso. Lembre: o `date` já
> > está fazendo exatamente isso e **já está welded**."*
>
> **Ele está certo, e o meu erro foi de método**: tratei como pergunta aberta o que já está
> soldado, e a 1ª versão desta nota terminava em *"pendente de decisão do owner"* quando a
> dinâmica **já responde**. O que muda está na **§6**, escrita depois. As medições das §§2–5
> continuam válidas — elas medem o custo, não a decisão.

---

## 1. O que eu estava colapsando

Eu vinha usando três planos (CORE × API × WIRE). O owner separa **cinco**, e os dois que eu
colapsava são justamente os que decidem:

| plano | o que é | o TCF vê? |
|---|---|---|
| 1 · **fonte** | o banco (SQLite `DATETIME`, PG `timestamp`) | **não** — só contextualiza |
| 2 · **dataset na linguagem** | o que chega ao `encode()`: `str`? objeto? | **sim — é só isto** |
| 3 · **leitura do spec** | qual padrão ele lê, e a que custo | — |
| 4 · **transformação interna** | o ordinal/epoch — nunca sai | — |
| 5 · **forma do decode** | devolve a **grafia de entrada** ou um **datetime de mesma resolução** | **é a decisão nova** |

Eu tratava 2 e 5 como um só ("entra string, sai a mesma string"). São independentes — e é a
independência deles que abre a saída.

---

## 2. Os fatos medidos

### (a) O TCF **recusa** `datetime`, `date` e `time` hoje

```
str      ACEITA  #TCF.8!    tipo preservado
int      ACEITA  #TCF.8n    tipo preservado
float    ACEITA  #TCF.8n!!  tipo preservado
bool     ACEITA  #TCF.8b    tipo preservado
datetime RECUSA  HierarchicalError: valor escalar de tipo não suportado: datetime
date     RECUSA  idem
time     RECUSA  idem
```

Os quatro que entram são **exatamente os escalares do JSON**. E é a confirmação empírica da sua
observação: *"não tem um tipo nativo de relógio (tirando timestamp, que é praticamente um
inteiro)"* — no JSON não há datetime, e o TCF herda isso.

**Consequência**: o plano 5 na forma "devolver um `datetime`" **não existe nem em potencial
hoje**, porque o tipo nem entra.

### (b) A sua premissa de velocidade **se confirma** — mas o caro não é o parse

| operação | ns/chamada | vs `date.fromisoformat` |
|---|---:|---:|
| `date.fromisoformat` | 149,5 | 1,00× |
| **`datetime.fromisoformat`** | **220,5** | **1,48×** |
| `datetime.strptime` | 13.541 | **90,6×** |

*"Se for muito rápida"* → **é**. O `datetime.fromisoformat` é 61× mais barato que o `strptime`,
e só 48% mais caro que o do date. A porta que você abriu está aberta.

**Mas o guard sim é caro**, e isso é novo:

| verificação de canonicidade | ns |
|---|---:|
| **re-emissão** (`d.isoformat(sep) != v`) — a do `data_iso` | **2056** |
| posicional (sem chamar `isoformat`) | 1428 |
| **regex compilada** | **871** |
| *(o parse, para referência)* | 443 |

No `data_iso` o guard era barato. **Aqui a re-emissão custa 4,6× o parse** — e passa a dominar.
A regex faz a mesma triagem por **2,4× menos**, e recusa corretamente `T`, `_`, week-date e
`HH:MM` sem segundo.

### (c) Ele aceita 16 de 20 grafias — inclusive as absurdas

Aceita: `T`, `t`, **espaço**, **`_`**, **`x`**, **tab** como separador; `HH:MM` sem segundo; só
a data; forma básica com `T`; frações; `Z`; offset; e **week-date** (`2026-W10-1 08:26:00`).
Recusa só: compacta sem `T`, `24:00:00`, pt-BR, e sem zero-padding.

### (d) E aqui está o preço de "aceitar os formatos que tiver"

Se aceito as 16 e devolvo **uma** canônica:

| canônica de saída | sobrevivem ao RT byte-exato |
|---|---|
| espaço | **3 de 16** |
| `T` | **1 de 16** |

**Aceitar generosamente e devolver canônico destrói o RT byte-exato em 13 a 15 dos 16 casos.**
Elas só sobrevivem se o compromisso for **resolução**, não grafia — que é exatamente o plano 5.

### (e) "Mesma resolução" **não vem de graça**

O objeto `datetime` **não sabe** de que grafia veio: `2026-03-02 08:26`, `2026-03-02 08:26:00`
e `2026-03-02` colapsam no mesmo objeto, e `microsecond=0` não distingue *"não tinha fração"*
de *"tinha `.000000`"*.

Logo **a resolução teria de viajar à parte** — não é dedutível do valor.

---

## 3. A estrutura repensada — três caminhos, e o plano 2 decide qual

O que o dataset entrega **determina** qual compromisso o decode pode assumir:

| | o dataset entrega | compromisso do decode | RT | existe hoje? |
|---|---|---|---|---|
| **A** | `str` na grafia canônica | **a mesma string** | byte-exato | **sim** — é o `data_iso` |
| **B** | `int` (timestamp) | o mesmo int | tipo+valor | **sim** — tag `n`, sem spec |
| **C** | objeto `datetime` | um `datetime` de **mesma resolução** | tipo+valor+**resolução** | **não** — o tipo é recusado |

**E aqui está o ponto que fecha a sua ideia**: o plano 5 — *"entregar como datetime sem
compromisso com a entrada"* — **só é possível no caminho C**. Nos caminhos A e B o dado **é**
uma string ou um int, e esses tipos têm RT por construção; não há liberdade a exercer.

Ou seja: *"aceitar os formatos que tiver"* e *"RT byte-exato"* são **incompatíveis no caminho
A**, e **compatíveis no caminho C** — porque lá o compromisso deixa de ser a grafia.

---

## 4. O que muda na receita, em cada caminho

### Caminho A (string canônica) — o que cabe no `.8` hoje

A receita do `data_iso` vale inteira, com **uma troca medida**: **regex no lugar da re-emissão**
(871 ns contra 2056), porque a canonicidade do datetime é posicional e o `isoformat()` dele é
caro. Aceita **uma** grafia; as variantes viram literal — e o lab `…-0130` já mediu que isso
ganha em 7 de 8 regimes e **errar a grafia custa zero**.

### Caminho B (timestamp inteiro) — já funciona, e não precisa de nada

Chega como `int`, vira tag `n`, e o núcleo já comprime. É a sua observação: *"praticamente um
inteiro"*. **Nenhum spec necessário.** Vale registrar como recomendação de manual: quem puder
entregar epoch, entrega — e o lab mediu por quê (batimento: **58 B contra 19.786** do texto).

### Caminho C (objeto datetime) — é decisão de FORMATO, não de spec

Exigiria: aceitar o tipo (hoje `HierarchicalError`), tag nova no índice 6, e **a resolução
viajando** (minuto/segundo/milissegundo/micro), porque o objeto não a carrega. Isso cai no
`T-TIPOS-CONFORTO-MAP`, que está **bloqueado em você**.

O detalhe barato: a resolução pode viajar **no próprio `wire_id`** — `:dtm` (segundo),
`:dtmm` (minuto), `:dtmu` (micro) —, que já viaja e já é fail-loud em id desconhecido. Não
precisa de campo novo.

---

## 5. E a recomendação de manual, que você levantou

> *"é interessante que ele já venha formatado por recomendação de manual, pro tcf não ter que
> tratar qualquer data"*

Já existe o precedente exato: `docs/how-to/normalizar-data-antes-do-tcf.md`, que o `data_iso`
cita. Um irmão para datetime teria de resolver o que o levantamento achou e eu não sabia:

- **nenhuma das duas grafias de 19 chars é RFC 3339** (o `time-offset` é obrigatório na
  gramática) — o argumento de norma que elegeu o `YYYY-MM-DD` **não transfere**;
- o **`T` tem a norma** (ISO 8601 removeu a omissão em 2019), os **bancos têm o espaço**
  (SQLite, PG, MySQL, SQL Server), e o **Python se divide**: `str(dt)` dá espaço,
  `dt.isoformat()` dá `T` — para `date` os dois coincidem, para datetime **não**;
- e **o corpus não vota**: o espaço do `InvoiceDate` foi fabricado pelo pandas no setup.

---

---

# 6. A DINÂMICA recuperada — e ela dissolve a pergunta que eu deixei aberta

## 6.1 A regra, e ela não é "a lib re-emite"

O guard do `data_iso` **é literalmente a função de emissão do `decode_value` do próprio spec**:

```python
data_iso.py:92    if d.isoformat() != v:                        # o guard
data_iso.py:107   return _FROM_ORD(int(payload)).isoformat()    # o decode
```

**A mesma chamada.** A regra não é *"aceite o que a lib re-emite"* — é **"aceite exatamente o
que o SEU decode consegue devolver"**. O guard existe para garantir que `classify_value` aceite
**o mesmo conjunto** que `decode_value` produz. É o que a ADR-0036 diz em outro vocabulário:
*"`_le_grafia` desfaz exatamente `_grafa`, nem mais"* e *"recusar o que o encoder canônico
nunca produz"*.

Status normativo: **"guard de re-emissão é lei; todo eixo novo nasce com ele"** — 5 aplicações
soldadas, 4 bugs históricos.

## 6.2 Isso DISSOLVE a pergunta do separador

Eu tinha deixado *"espaço ou T?"* como decisão pendente. Pela dinâmica, **não é decisão de
norma — é consequência de qual decode se escreve**:

- decode que emite `isoformat(sep=" ")` ⇒ o guard aceita exatamente o espaço;
- decode que emite `isoformat(sep="T")` ⇒ o guard aceita exatamente o `T`.

**São dois decodes, logo dois specs.** E o precedente para isso já está escrito no próprio
`data_iso`: *"outras grafias, se vierem, são specs nomeados irmãos — **precedente CPF/CNPJ, um
objeto por grafia**"*. CPF e CNPJ não competem por "qual é o canônico": são irmãos, cada um com
seu id.

O lab `…-0130` já mediu que isso custa **1 byte de id**, porque errar o spec dá wire
**byte-idêntico** ao sem-spec. **Não havia decisão sob risco — havia dois irmãos.**

## 6.3 E "o TCF recusa datetime" não é obstáculo — o date está na MESMA situação

Meu erro mais direto na 1ª versão. O TCF recusa `datetime`… **e recusa `date` também**
(medido: os dois dão `HierarchicalError`). E o `data-iso` está **welded e funcionando**.

**Porque o date entra como string.** O caminho A não é uma limitação a contornar — é **a
dinâmica escolhida, exercida e soldada**. O datetime não tem pergunta a fazer aqui: segue.

O caminho C (objeto nativo) continua sendo tipo novo e continua bloqueado no
`T-TIPOS-CONFORTO-MAP` — mas ele **nunca foi a rota do date**, então nunca foi a pergunta.

## 6.4 O que "aceitar os formatos que tiver" significa DENTRO da dinâmica

Não é *"aceite tudo"*. É: **a lib nativa é barata o bastante para ser o leitor** — e a medição
confirma (`fromisoformat` 1,48× o do date; `strptime` **90×**). O conjunto aceito continua
sendo o que o guard deixa passar, que é o que o decode devolve.

O how-to do date já diz o que acontece com o resto, e vale igual: *"**nada quebra**. O TCF
trata data como string e faz round-trip byte-exato de qualquer grafia… você só comprime
menos"*, e o spec *"entrará como **candidato**: quando o palpite dele não ajudar, o wire cai de
volta no que seria hoje. Medido: **nunca pior que hoje**"*.

## 6.5 A minha sugestão de trocar o guard por regex VIOLA a dinâmica

Eu propus regex (871 ns) no lugar da re-emissão (2056 ns). Pela §6.1, **o guard tem de ser o
emissor do decode** — trocar por regex quebra a identidade que é a lei.

Só é legítimo se a regex for **provadamente equivalente** ao emissor, e isso não está provado.
**Retirado como recomendação**; fica registrado como hipótese, com o ônus da prova declarado. O
custo de 2056 ns/valor é o que a lei cobra, e o `data_iso` já paga o análogo.

## 6.6 O que sobra, então

| item | estado |
|---|---|
| grafia canônica | **não é escolha** — é o decode. Dois decodes ⇒ dois specs irmãos (`dtm` e um irmão), precedente CPF/CNPJ |
| caminho | **A**, como o date. O C nunca foi a rota do date |
| leitor | `datetime.fromisoformat` — confirmado barato (1,48×) |
| transformação | inteiro, e **o menor possível** (`T-OBAT-COME-O-SEQRLE`) |
| guard | re-emissão, **como no date**. A regex sai da recomendação |
| manual | um irmão do `normalizar-data-antes-do-tcf.md` |

**Não há pergunta pendente para o owner.** Havia uma pergunta minha, que a dinâmica já
respondia.

## Conexões

## Conexões

lab [`…-0020-datetime-grafias-regimes-mecanismos`](../../2026-08/2026-08-15/2026-08-15-0020-datetime-grafias-regimes-mecanismos/) ·
lab [`…-0130-spec-datetime-receita-do-padrao`](../../2026-08/2026-08-15/2026-08-15-0130-spec-datetime-receita-do-padrao/) ·
`T-DATETIME-TIPO` · `T-TIPOS-CONFORTO-MAP` (⛔ owner) · `T-OBAT-COME-O-SEQRLE` ·
ADR-0041 (`dtm` reservado) · `docs/how-to/normalizar-data-antes-do-tcf.md` (o precedente de manual)
