# Decode direto ao tipo — a proposta do owner, medida

> **Owner (2026-08-15)**: *"no decode, ele sai de string e vai passar por uma função de
> date/datetime de qualquer forma. Fazer isso num formato para depois o dev passar novamente
> para um segundo formato — é mais barato se fizer já na primeira vez:*
>
> *hoje:     `datetime comprimido` → decode → date-padrão → date que o cliente quer*
> *proposta: `datetime comprimido` → decode(alguns formatos) → date que o cliente quer*
>
> *Use o barato/nativo. A ideia é padronizar antes — não quero que vire um datatransform
> portátil. Se o tcf for feito em outra linguagem, cuidado pra não inflar o núcleo."*

**Uma pergunta**: entregar o objeto direto do decode economiza de verdade, e cabe nas regras
já decididas?

**Resposta curta**: sim — **17,5–19,3% do decode completo** em n≥500, com `src/tcf` intocado,
porque o objeto **já existe no meio do decode** e é jogado fora. Ver [`result.md`](result.md).

## Estado — era / foi / é / será

- **Era**: o decode do spec serializa (`fromordinal(...).isoformat()`) e o cliente re-parseia
  a mesma string. Duas conversões para chegar onde o decode já esteve.
- **Foi**: a proposta do owner de cortar o caminho, com as quatro ressalvas dele.
- **É**: protótipo de **9 linhas** (um spec cujo `decode_value` devolve o objeto), 0 falhas.
  A união com literal no meio sai `['date','str']` — o **CONTRATO UNIÃO do ADR-0039** herdado
  pronto. O caso pequeno deu −5,9% e é **ruído declarado** de dev-run.
- **Será**: registrado como proposta `T-DECODE-SAIDA-TIPADA` — kwarg da API do host
  (`saida="date"`), wire **idêntico**, string continua o default byte-exato.

## As descobertas de mecânica (que o protótipo precisou)

1. **O registry tem precedência na resolução do `:id`** (`decoder.py:73-77`): o spec passado
   em `nature=` só é usado quando o id do header **não** resolve no registry. Por isso o
   protótipo usa id próprio (`dtobj`) — é veículo de lab, não desenho de weld.
2. **O contrato `decode_value -> str` é convenção, não checagem**: um decode que devolve
   objeto atravessa a rota single-col string sem erro. É o que torna o kwarg barato de soldar
   um dia — a tubulação já não se importa.

## Ressalva da vertente de tempo

**Dev-run** (melhor-de-5, máquina não quiescente): valem as **razões**, não os absolutos. O
−5,9% do n=200 está dentro do ruído — a rota direta faz estritamente menos trabalho, não há
mecanismo para ser mais lenta.

## Como rodar

```
python run.py     # sai 0 só se RT string e volta-objeto fecharem em todos os casos
```

Sem `Z:` — sintético determinístico. `src/tcf` intocado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<caso>.entrada.json` · `.fonte.json` | as colunas e a procedência |
| `outputs/<caso>.tcf` · `.roundtrip.json` | o wire e o RT string (o contrato de hoje) |
| `outputs/<caso>.saida-objeto.json` | a saída-objeto re-serializada (diff contra a entrada) |
| `intermediates/medicoes.json` | as 3 rotas cronometradas, com os avisos |

## Vínculo

`T-DATETIME-TIPO` · ADR-0039 (**CONTRATO UNIÃO** — o precedente da saída mista) ·
`decoder.py::_cast_tipo` (o precedente soldado de decode-que-transforma) ·
nota [`…-0230-datetime-os-cinco-planos`](../../../notas/2026-08/2026-08-15-0230-datetime-os-cinco-planos.md) ·
`docs/how-to/normalizar-data-antes-do-tcf.md` (a regra da entrada, que NÃO muda)
