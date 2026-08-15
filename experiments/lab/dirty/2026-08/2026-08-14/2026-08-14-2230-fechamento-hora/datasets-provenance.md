# Procedência dos dados — e o viés declarado

## Por que este lab é quase todo sintético

A varredura do corpus (9 bancos, 21 tabelas, **102 colunas**, confirmação por full-scan) achou:

> **Hora pura NÃO EXISTE.** Zero colunas com `HH:MM:SS`, `HH:MM` ou variantes.

A única parte-hora do corpus vive **dentro de um datetime** — `online_retail.InvoiceDate`,
grafia única `YYYY-MM-DD HH:MM:SS`, com **segundo constante `00`** (resolução de minuto), 774
valores distintos, regime comercial (97,61% entre 08h e 18h, **nenhum sábado**), **sem batimento
de minuto** (os 60 minutos aparecem todos; múltiplos de 5 são 19,02%, *abaixo* dos 20%
uniformes — é ruído de tráfego, não relógio), e **95,71% de repetição adjacente**.

E o banco que traria hora de verdade — `beijing-pm25.db`, telemetria horária — **está com 0
bytes**.

Então os regimes onde a hora tem comportamento próprio **têm de ser construídos**.

## Sintéticos (7 regimes + 9 bordas)

Gerados em `casos.py`. **Sem `random`**: o regime `expediente` usa um LCG determinístico, para
o lab ser reprodutível byte-a-byte. Gravados em `inputs/<caso>.entrada.json` com
`<caso>.fonte.json`.

**Viés, declarado e forte:**

- **Batimento perfeito é o melhor caso possível** para qualquer mecanismo de regularidade. Os
  regimes de 15 min / 1 min / 1 s existem para **ver o comportamento**, não para estimar ganho
  no mundo. O corpus real, quando tem hora, **não tem batimento** (medido acima).
- **`regime-batimento-15min-2dias` é o par de contra-prova** de `regime-batimento-15min`: mesma
  série, mesmo passo, só que atravessando a meia-noite. Sem esse par, a diferença de bytes não
  poderia ser atribuída à ciclicidade.
- **`regime-so-hora-e-minuto`** é o par de grafia: a mesma sequência em `HH:MM`.
- As **9 bordas** vêm das normas (ISO 8601, RFC 3339, RFC 9557) e do comportamento medido do
  Python 3.13 — não são invenção. Várias são grafias que a norma admite e a biblioteca recusa.

## Real (1 coluna)

`Z:/tcf-data/interim/online-retail.db`, a **parte de hora** extraída de `InvoiceDate` por split
no espaço. Amostra por passo espalhado, alvo 2000. **Não versionado**; o lab roda sem `Z:`.

**Viés**: é uma coluna, de uma fonte, e ela **não é hora pura** — é o campo de hora de um
timestamp de varejo, com segundo constante. Nenhuma conclusão sobre "hora no mundo" se apoia
nela; ela serve como o único ponto de contato com dado observado.

## Nota sobre falsos positivos (por que não fui procurar hora "escondida" em inteiros)

A varredura testou e descartou: **`0..86399` como heurística de "segundos desde meia-noite"
pega 44 colunas** do corpus, nenhuma delas hora (inclui `wine.pH`, `adult.age`,
`l_discount`). `HHMMSS` sobre inteiro pega chaves (`o_orderkey`, `fnlwgt`). E `AM`/`PM` por
substring pega **`uf_sigla = 'AM'` — a sigla do Amazonas**, além de `LAMP` e `Not-in-family`.

Qualquer detecção automática de hora precisaria de âncora estrutural, não de faixa nem de
substring. Isto está registrado como caracterização, não como proposta.
