---
title: "T-QA-083-REVALIDACAO: reavaliar a superfície 0.8.3 com evidência em disco"
type: review
status: closed
priority: P1
created: 2026-08-29
updated: 2026-08-29
blocked-by: []
related:
  - experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/
  - tickets/BUG-BB-CR-CRU.md
  - tickets/BUG-MENSAGEM-COLUNA-VAZIA-MISTA.md
  - tickets/T-DOC-RELEASE-083-SUPERFICIE.md
  - tickets/T-DOC-TIPOS-MISTOS.md
  - tickets/T-QA-8-material-comprobatorio.md
---

# T-QA-083-REVALIDACAO

**[probatório]** Este registro substitui a revisão feita por sondas efêmeras. Nenhum achado
técnico desta reavaliação é aceito só porque apareceu no terminal ou no diálogo: o owner da
evidência é o lab
[`2026-08-29-2320-revalidacao-083-evidencia`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/).

## Objeto medido

- commit: `22cf319223f4e4f7739510c2259acf496ddc6fac`;
- versão do pacote no repo: `0.8.3`;
- comparação histórica: fonte extraída da tag `v0.8.2`, executada em processo isolado;
- comando: `python run.py` na raiz do lab;
- resultado: **7 casos, 0 falhas**;
- mudanças em `src/tcf/`: **nenhuma**.

O runner limpa os derivados, canonicaliza os inputs em LF e exige round-trip byte-idêntico em
arquivo. Cada caso liga entrada, wire, round-trip e observação em
[`outputs/INDEX.md`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/outputs/INDEX.md).
O manifesto SHA-256 impede que um arquivo sem proveniência seja confundido com resultado da rodada.

## Vereditos sustentados

| assunto | observação falsificável | classificação |
|---|---|---|
| CR na união `bB` | `encode([True, "a\rb"])` grava `0d` no offset 12; single string e multi recusam CR; `.8H` escapa | **defeito de canonicidade**, owner em [`BUG-BB-CR-CRU`](BUG-BB-CR-CRU.md) |
| nome vazio no erro misto | `{"": [1, "x"]}` omite a coluna; `{"v": [1, "x"]}` escreve `coluna 'v'`; `""` é nome válido e faz RT no controle | **defeito de diagnóstico**, owner em [`BUG-MENSAGEM-COLUNA-VAZIA-MISTA`](BUG-MENSAGEM-COLUNA-VAZIA-MISTA.md) |
| emissão de `{"v": []}` | 0.8.2 emite `#TCF.8H#Ov...` (18 B); HEAD emite `#TCF.8M@v` (12 B); ambos fazem RT | **erro factual no changelog**, não bug de wire |
| publicação | PyPI responde 0.8.3 e a tag remota existe; STATUS/ROADMAP ainda declaram 0.8.2/preparada | **superfície desatualizada** |
| tipos mistos nas famílias | single `bB` aceita com RT; `.8M` e `.8H` recusam | **assimetria deliberada**; o título universal da release excede o contrato |
| post-its em docs vivas | cinco ocorrências dirigidas, com arquivo e linha gravados | **dívida I1**, já tem owner em [`T-DOC-TIPOS-MISTOS`](T-DOC-TIPOS-MISTOS.md) |

## Alegações retiradas ou rebaixadas

### `view.count()` sobre `n_rows` divergentes

O fato é reproduzido: o `decode` recusa, a primeira chamada da `view` avisa e devolve `3`, e a
segunda devolve `3` sem novo aviso. Isso **não autoriza classificá-lo como bug novo**. O
[`T-QA-8`](T-QA-8-material-comprobatorio.md) registra explicitamente a divergência da `view` como
deliberada. O veredito correto é **risco aceito por decisão vigente**. Alterá-lo exige nova decisão,
não uma correção clandestina.

### Wire denso-nulo da 0.8.2 na `view`

O decoder 0.8.3 lê o wire antigo e reconstrói o input. A `view` 0.8.3 o recusa, mas a própria
`view` 0.8.2 também o recusava com a mesma mensagem. Logo, o caso prova **limitação preexistente da
view**, não regressão. A frase de compatibilidade precisa nomear o decoder; este caso não prova a
universalidade “todo wire”.

### Custo de `count()` em `@dict`

Com seis colunas, `count()` abre as seis tabelas de únicos e preenche os seis `_dict_cache`, mas
`report()` devolve `materialized_bytes=0` e `touched=[]`. A contagem retornada está correta e o
próprio código declara a telemetria como aproximação. Classificação: **dívida de custo/telemetria
para `.9`**, não bug de correção.

## Critérios de fechamento

- [x] Todos os casos têm input em disco.
- [x] Todos os casos aceitos têm `.tcf` e `roundtrip.json` byte-diffável.
- [x] A fonte 0.8.2 é extraída da tag e seu caminho importado fica registrado.
- [x] Claims normativas têm arquivo, contexto e SHA-256 em `contratos-verificados.json`.
- [x] Resultados externos registram URL/comando, resposta e hash.
- [x] Alegações sem sustentação normativa foram retiradas ou rebaixadas.
- [x] Defeitos confirmados e correções documentais têm owner próprio.
