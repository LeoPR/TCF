# Data como spec — análise crítica antes de montar o lab

**2026-08-08 · análise, não lab. Nenhum código mexido.**

Owner: *"talvez pro fluxo, tratar a data como um spec seja um bom ponto de vista, veja se
podemos fazer isso"* — e, antes do lab, *"faça mais uma rodada de análise crítica"*.

---

## 1. A observação que mais simplifica (e está certa)

> *"mesmo que uma data que na origem era nativamente data, como o SQL, entre convertida pra
> string, essa string é bem sólida e não dará problemas… ele é 'por origem hard' mas o TCF
> não precisa se preocupar com isso"*

Isto reenquadra o problema e **derruba a prioridade que eu tinha dado ao ramo hard-nativo**.

"Origem hard" é propriedade do **pipeline a montante**, não do tipo Python. Um `DATE` do SQL
serializado em ISO produz uma coluna em que **100% dos valores parseiam** — e o lab de ontem
já mediu esse caso: `limpo-diario`, 100% compressível, **−93,7%**.

Ou seja: **o caminho lazy já entrega o desempenho do caminho hard**, quando a origem é sólida.
O que o ramo hard-nativo (`datetime.date` entrando cru) acrescentaria seria evitar o
`strptime` — CPU, que é assunto do `.9`.

**Consequência prática:** `T-DATA-TIPADA-NATIVA` cai de prioridade. Não é pré-requisito de
nada; é conforto de API.

## 2. "Data como spec" cabe na FORMA — o problema é a ESTRATÉGIA

O contrato do spec (`classify_value` → `encode_value` → literal com 1 char → `decode_value`)
serve pra data sem adaptação. O que **não** serve é copiar o *alvo* da transformação.

O CPF transforma pra **denso de largura fixa** (BASE94). Medi os dois alvos sobre as mesmas
colunas:

| coluna | ISO | ordinal **decimal** | ordinal **denso-fixo** |
|---|---:|---:|---:|
| diário n=120 | 97 B | **22 B** | 565 B |
| mensal n=120 | 1051 B | **23 B** | 609 B |
| diário n=1200 | 829 B | **23 B** | 5433 B |
| **espalhado n=1200** | 11091 B | 8269 B | **5987 B** |

**A inversão na última linha é o achado.** Os dois alvos não competem — eles cobrem regimes
opostos:

- **regular** → o decimal ganha até **236×**, porque o `*N+M|` (seq-RLE multi-delta)
  *enxerga a aritmética*: `#TCF.8\n*120+1|\739617`;
- **espalhado** → o denso ganha **27%**, porque não há aritmética a explorar e o que paga é
  densidade.

E isso **explica** a escolha do CPF em vez de contradizê-la: CPF não tem sequência aritmética
— CPFs não vêm ordenados —, então denso é o alvo certo *para o regime dele*. **Data tem os
dois regimes.**

> Um `SPEC_DATA` com um alvo só deixa dinheiro na mesa em um dos dois regimes. E escolher
> entre dois alvos por `min()` é literalmente o padrão do projeto.

## 3. Onde data encaixa no spec sem atrito

| peça | encaixa? | evidência |
|---|---|---|
| `classify_value` → status | ✅ | o protótipo já produz `comprimento`/`nao-parseia`/`grafia-nao-canonica` |
| literal com 1 char | ✅ | teto do prejuízo medido: **+4,9%** |
| `SPEC_REGISTRY` + header self-describing | ✅ | **custo medido: 5 B** (`#TCF.8 :cpf` vs `#TCF.8`) |
| telemetria `nature_apply` | ✅ | `apply_rate` + `by_status`, de graça |
| *"não valida semântica"* | ✅ | pra data: parseia, não julga se a data faz sentido |

O **custo de declarar o spec era o número que faltava** desde o lab de ontem. São **5 bytes
fixos**. Contra −93,7% numa coluna de 500 valores, é ruído.

## 4. Onde encaixa mal — três atritos reais

**a. Dois alvos, não um** (§2). O `TemplatedCheckedSpec` assume um alvo denso e calcula
`encoded_length` a partir de `body_length`. Data precisa escolher o alvo por regime.

**b. CPF tem UMA grafia; data tem muitas.** O precedente do projeto é **um spec por grafia
concreta** — `SPEC_CPF` e `SPEC_CNPJ` são dois objetos, não um parametrizado. Aplicado a
data, isso dá `SPEC_DATA_ISO`, `SPEC_DATA_BR`, `SPEC_DATA_US`, `…` — 6 a 8 specs.

A alternativa (um spec parametrizado por `fmt`) esbarra no header: `:cpf` identifica o spec
inteiro, então um spec parametrizado precisaria de `:data-iso`. **Isso o CPF nunca enfrentou**,
e é a única decisão de design aqui que precisa do owner.

**c. Data não tem dígito verificador — tem validade de calendário.** O papel é o mesmo
(rejeitar o malformado), mas a implementação é outra: a validade está *dentro* do parse, não
num `check_fn` separado. Os campos `check_fn`/`check_length` do dataclass ficam vazios. Isso
sugere que data é irmã do `TemplatedPaddedSpec` (o do IP), não do `TemplatedCheckedSpec`.

## 5. Revisão do que já fizemos

| o que | veredito |
|---|---|
| alvo decimal no protótipo | **certo** — confirmado por medição |
| conclusão do lab sobre `limpo-espalhado` (−22,7%, "vence lazy") | **incompleta**: vence o ISO, mas o denso venceria o decimal em 27%. Não estava errado; estava faltando um candidato |
| guarda de re-emissão | certa, provavelmente inalcançável no ISO — fica pros outros `fmt` |
| custo do header | **estava faltando; agora medido: 5 B** |
| "a ambiguidade não precisa ser resolvida" | sustenta-se — e vale mais ainda no spec, porque o registry já nomeia qual grafia foi usada |

## 6. O que eu proporia atacar, em ordem

1. **Adotar a forma de spec** — sem discussão, encaixa.
2. **Dois alvos escolhidos por `min()`** — decimal e denso. É o padrão do projeto, e a
   medição diz que os dois são necessários.
3. **Um spec por grafia, começando por ISO** — segue o precedente CPF/CNPJ, evita a decisão
   do header por enquanto.
4. **A decisão que precisa do owner**: `:data-iso` no header (spec por grafia, registry
   cresce) *ou* `:data` + parâmetro (registry enxuto, header novo). É a única bifurcação real.

## 7. Achado lateral, pequeno

`BASE94` (`natures/templated_checked.py`) tem **80 caracteres**, não 94 — é
`chr(33..126)` menos os reservados, e o próprio `assert` só exige `>= 50`. O nome engana quem
for calcular largura de payload. Custo de corrigir: um rename.

---

## Nada foi construído

O lab de "data como spec" **não** foi montado — a análise foi pedida antes, e ela mudou o
desenho dele: precisa comparar **dois alvos**, não validar um. Volto quando você disser.
