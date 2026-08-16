# Ordem de colunas no `.8M` — o que a ordem prende, e o nome implícito que vira explícito

> **Owner (2026-08-16)**: *"um dataset pode não precisar respeitar isso... se não tiver nomes,
> ele tem que aceitar o padrão de entrada — mas mesmo nesse caso dá pra 'burlar', colocando um
> nome implícito... se eles mudam de ordem, então o número/nome implícito ficaria explícito,
> não? apenas pesquise o que daria pra fazer nesse caso."*

Par do [`1400-cadastro-popular-header-do-M`](../2026-08-16-1400-cadastro-popular-header-do-M/)
— **os mesmos 500 registros** (gerador importado; precedente `0530`←`0400`), só a ordem muda.

## As 4 predições declaradas, e o que aconteceu

| # | predição | veredito |
|---|---|---|
| P1 | RT em qualquer permutação; corpo por coluna byte-idêntico em qualquer posição | **confirmada** — 5 permutações + 7 escolhas de última, tudo RT ok; variação total de **3 B**, só header |
| P2 | com `drop_names`, reordenar troca os donos dos valores CALADO | **confirmada** — o consumidor lendo `'0'` recebe `id` numa ordem e `nome` na outra, sem erro |
| P3 | nome numérico explícito funciona como âncora de posição | **confirmada** — `"3"` decoda como `"3"` em qualquer posição; custo **1,9 B/coluna** sobre o anônimo |
| P4 | anônima + nome `"0"` explícito colidem no decode | **REPRODUZIDA** — header declara 3 colunas, decode devolve **2**, valores somem calados |

## A resposta à pergunta do owner, em três frases

**A ordem das colunas no `.8M` é livre** — os corpos são independentes e a única posição com
significado é a última (size omitido, no máximo 3 B aqui). **Para colunas anônimas a ordem É o
nome** (posicional `str(i)`), e aí reordenar é renomear — o P2 mostra o estrago. **A "burla"
que você propôs já é representável hoje**: nomear pela posição canônica (`"0"`,`"3"`…) ancora
a coluna ao índice independente da ordem física, por ~2 B/coluna — o que falta é só o guard do
P4 (1 linha de fail-loud no decode, `len(result) == len(pares)`), senão a mistura
anônimo+numérico perde coluna calada.

## Como rodar

```
python run.py    # sai 0 só se todos os RTs fecharem e as invariantes baterem
```

`src/tcf` intocado. Bloco 3b usa **fluxo invertido** (wire à mão em
`inputs/colisao-anonima-vs-0.wire-de-entrada.tcf`) — é lab de decoder, documentado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `outputs/perm-*.tcf` | as permutações (compare as linhas 1) |
| `outputs/sem-nomes-ordem-{canonica,rodada}.tcf` | o par do P2 |
| `outputs/nomes-numericos-explicitos.tcf` | a proposta do owner, funcionando |
| `inputs/colisao-anonima-vs-0.wire-de-entrada.tcf` | o wire adversarial do P4 |
| `resultado.json` | os números |

## Vínculo

Nota-mãe: [`estagios-e-soldas-do-M`](../../../notas/2026-08/2026-08-16-1510-estagios-e-soldas-do-M.md)
(§4.4 = o P4) · `T-UM-CAMINHO-SO` · ADR-0023 (min_header) · ADR-0029 (posicionais) ·
O-FMT-02/`sort_by` (o precedente de "ordem é descartável" nas LINHAS)
