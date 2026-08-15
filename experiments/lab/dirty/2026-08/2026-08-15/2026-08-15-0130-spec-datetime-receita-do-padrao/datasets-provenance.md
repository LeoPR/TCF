# Procedência dos dados — e o viés declarado

## Inteiramente sintético

O lab roda **sem `Z:`**. Os 8 regimes vêm do `casos.py` do lab irmão
[`…-0020`](../2026-08-15-0020-datetime-grafias-regimes-mecanismos/) — importados, não
duplicados, para que os dois labs falem do **mesmo dado**.

Geração determinística (LCG, **sem `random`**), instante base `2026-03-02 08:26:00`.

## Por que a grafia é uniforme em cada coluna

Decisão sua (2026-08-15): a coluna vem **pré-formatada** de um banco, que já trata datetime
como canônico; mistura seria **corrupção de transmissão**, não regime. Então cada coluna aqui
tem **uma** grafia, e há **um** caso de mistura (`b-mista`) apenas para verificar o fallback.

## O viés dos regimes (herdado, e vale repetir)

Quatro dos oito têm estrutura aritmética ou repetição alta — **são o melhor caso** dos
mecanismos que o lab mede, e existem para exibir o comportamento. **Nenhum estima frequência no
mundo.** A leitura honesta é sempre *"neste regime, X"*.

O `r1-comercial` é o único calibrado para imitar dado real (o `InvoiceDate`), e imita **uma**
coluna.

## Uma ressalva que o levantamento trouxe, e que muda a leitura do corpus

O `online_retail.InvoiceDate` tem separador **espaço** em 541.909/541.909 linhas — mas esse
espaço **não é do dado**: nasceu em `scripts/setup_online_retail.py:109-110`, quando o pandas
re-emitiu `datetime64` pela rota `str()`. A origem do dataset é `M/D/YYYY HH:MM` (Excel/UK).

Portanto **o corpus não é evidência sobre qual separador o mundo emite** — contá-lo assim seria
contar o default do `str()` do Python duas vezes. Está registrado no `result.md` §3 e é a razão
de o lab não usar o corpus para decidir a grafia canônica.

## As 13 bordas

Não são invenção: cada uma é uma grafia que alguma norma admite ou algum sistema emite —
ISO 8601 forma básica, RFC 3339 com `Z`/offset, PostgreSQL `.ffffff`, SQL Server `.fff`,
mainframe compacta, pt-BR, epoch, `24:00:00` (ISO permite, Python recusa). O objetivo é ver
**qual dos três gates** pega cada uma, não estimar frequência.
