# EXP-017 — alvos mensais de data: bateria probatória [clean]

Testa **alvos mensais** de data (`mês×31+dia`, fim-de-mês, `YYYY-MM`) contra o
`SPEC_DATA_ISO` soldado, em **corpus real + sintético**. Consolida os labs dirty
`1853`/`2228` e incorpora duas caçadas adversariais.

```
python extrai.py    # (requer Z:) congela o corpus real em inputs/fontes/
python run.py       # (não requer Z:) regenera inputs/, intermediates/, outputs/, report.md
```

**27 casos, 0 falhas.** `src/tcf` **não é tocado** — os alvos são protótipos em
[`specs.py`](specs.py); o núcleo entra pelos `encode()`/`decode()` reais.

Conclusões: [`report.md`](report.md) · Inspeção artefato-a-artefato:
[`outputs/INDEX.md`](outputs/INDEX.md) · Proveniência dos dados:
[`datasets-provenance.md`](datasets-provenance.md)

---

## Como achar o que você quer, só pelo nome

```
EXP-017-data-alvos-mensais/
├── casos.py ............ O CATÁLOGO: 27 casos, cada um declara a IDEIA e o PIN
├── specs.py ............ os alvos-protótipo (A4 mês×31+dia · A2f fim-de-mês · YM ano-mês)
├── extrai.py ........... lê Z:/tcf-data e congela o corpus real (roda separado)
├── run.py .............. roda, aplica as 6 provas, gera todos os artefatos
├── datasets-provenance.md .. de onde vem cada coluna real + VIÉS declarado
├── report.md ........... GERADO: as conclusões
│
├── inputs/
│   ├── <caso>.entrada.json ... o que entrou — array PURO (diffável)
│   ├── <caso>.fonte.json ..... procedência: gerador, ideia, pin, n/k, hash, amostra
│   └── fontes/ ............... o corpus BRUTO extraído de Z: (10 colunas × 2 ordens)
│
├── intermediates/
│   ├── <caso>.candidatos.json .. TODOS os candidatos: bytes, como cada um foi gerado,
│   │                             o que ficou CONSTANTE na comparação, e quem venceu
│   └── <caso>.payloads.json .... a coluna transformada por cada alvo (amostra + hash)
│
└── outputs/
    ├── INDEX.md .............. o índice de inspeção (nome → ideia → input → veredito)
    ├── <caso>.tcf ............ o wire VENCEDOR
    ├── <caso>.roundtrip.json . a CONTRA-PROVA (diff contra a entrada = vazio)
    ├── <caso>.meta.json ...... procedência do wire: input, params, bytes, quem venceu
    └── medicoes.json ......... tudo em máquina
```

### Guia de nomes

| token | significa |
|---|---|
| `sint-*` | sintético construído para exercer um regime |
| `ctrl-*` | **controle** — onde o alvo mensal **não pode** ganhar |
| `valv-*` | **válvula** — dado que não casa (sujo, null, Unicode) |
| `real-*` | coluna real do corpus (`Z:/tcf-data`) |
| `*-nat` / `*-ord` | ordem **natural** (de armazenamento) / **ordenada** |
| `.entrada.json` | o input, array puro — é o lado esquerdo do `diff` |
| `.fonte.json` | os metadados do input (não entra no `diff`) |
| `.roundtrip.json` | o decode do wire — o lado direito do `diff` |
| `.meta.json` | procedência do wire |
| `.candidatos.json` | a decisão do `min()`, aberta |

## Conferir um caso — sem ler código

```bash
cd experiments/lab/clean/EXP-017-data-alvos-mensais

cat inputs/valv-ym-unicode.fonte.json          # o que é este caso, e o que se esperava
cat intermediates/valv-ym-unicode.candidatos.json   # todos os candidatos e quem venceu
cat outputs/valv-ym-unicode.meta.json          # a procedência do wire
diff inputs/valv-ym-unicode.entrada.json \
     outputs/valv-ym-unicode.roundtrip.json    # <- VAZIO = round-trip provado
```

O `run.py` faz esse `diff` como assert (prova 3) e **falha** se divergir.

## As seis provas

| prova | o que garante | vale o quê |
|---|---|---|
| **RT estrito** | `decode(encode(v)) == v` contra os dados originais | falsificável |
| **RT do espelho** | `decode_col(encode_col(v)) == v` — o alvo isolado | falsificável (achou o bug do YM Unicode) |
| **RT em arquivo** | `roundtrip.json` byte-idêntico à `entrada.json` | falsificável, e **inspecionável à mão** |
| **determinismo** | `encode` 2× byte-idêntico | falsificável |
| **artefato é o wire** | o `.tcf` lido em **binário** == o wire medido | falsificável (pega CRLF do Windows) |
| **nunca-pior** | o FLOOR com alvos nunca excede o melhor de hoje | **tautologia neste harness** (min sobre superconjunto) — documenta a invariante; a prova real é pós-weld |

Mais o **PIN**: `espera` em [`casos.py`](casos.py) fixa quem deve vencer o FLOOR. Mover a
fronteira de propósito **quebra o lab**, que é o ponto.

## O que este lab respondeu

**Nas colunas de fato cruas do corpus, os alvos mensais não pagam** — nenhuma das 9
colunas lógicas de data tem cadência mensal. Mas o resultado vem com três ressalvas
medidas (o "0%" depende do `n`; o regime é alcançável por derivação; o ganho sintético é
`O(n)` e frágil), e **folha de pagamento fica negativa nos 3 alvos enquanto um 4º eixo —
dia útil — recupera 99%**. Esse é o argumento empírico de que **spec deve orientar eixos,
não mandar alvo** ([triagem](../../../../docs/theory/spec-orienta-nao-manda-triagem.md)).

E o método corrigido expôs um achado transversal: o candidato interno da nature **não
passa pela rota plena** (sem polaridade, sem bN) — mediana ~5,7% desperdiçado em dado
real, válido para **qualquer** nature (`T-NATURE-CANDIDATO-BN`).

## Nota de processo

A primeira versão deste lab **falhava a inspeção**: sem `intermediates/`, sem
`datasets-provenance.md`, zero `roundtrip.json`, inputs nomeados por fonte e não por caso,
`outputs/` acumulando órfãos — e, o mais grave, **`outputs/` inteira era invisível ao git**
(`.gitignore:49 output*` engolia tudo; só o EXP-016 tinha exceção nominal). Refeito em
2026-08-10 a pedido do owner. O diagnóstico e a convenção que saiu dele:
[`labs-rastreabilidade-convencao.md`](../../dirty/notas/2026-08/2026-08-10-labs-rastreabilidade-convencao.md).
