# Resultado — a ordem no `.8M`: livre nos corpos, carregada nos nomes

Mesmos 500 registros do lab `1400`; 0 falhas; invariante de fronteira em todas as formas.

## 1. P1 — a ordem não muda os corpos, só o header (3 B de amplitude)

5 permutações: RT ok em todas, **corpo de cada coluna byte-idêntico em qualquer posição**
(comparado por nome via `_parse_meta` + fatias). Totais: 25.496–25.499 B.

A única alavanca real é **qual coluna fica por último** (size omitido):

| última | total | economia vs pior |
|---|---:|---:|
| cpf / email / telefone (size de 4 hex) | 25.496 | 3 B |
| nome / nascimento / ativo | 25.497 | 2 B |
| id (size `f`, 1 hex) | 25.499 | 0 B |

Regra emergente: **a melhor última é a de size mais longo em hex** — economiza
`len(size_hex)+1` B. Teto aqui: 3 B. É real, é pequeno, e é a única dependência de ordem do
formato em si.

## 2. P2 — para anônimas, a ordem É o nome (e reordenar é renomear, calado)

```
ordem canônica: decode()['0'][:1] = ['000001']       (a coluna id)
ordem rodada  : decode()['0'][:1] = ['Carla Silva']  (a coluna nome)
```

Mesmo consumidor, mesma chave `'0'`, outra coluna. Nenhum erro. É o comportamento correto do
formato (posicional é posicional) — o registro aqui é o **custo de contrato**: `drop_names`
só serve quando as duas pontas fixam a ordem fora do fio. É a versão em colunas do que o
`sort_by` (O-FMT-02) já assume nas linhas: ordem é descartável **quando declarada
descartável**.

## 3. P3 — a proposta do owner funciona hoje, por ~2 B/coluna

Nomear cada coluna pelo **índice canônico** (`"0"`…`"6"`) ancora a coluna à posição lógica,
independente da ordem física:

```
#TCF.8Mf=0,a56=1,%1d1c=2,%15ba=4,%7fb=5,@202=6,3
```

- a coluna movida (`"3"`, o email) foi parar no fim físico e **continua achável por nome**;
- decode devolve `['0','1','2','4','5','6','3']` — a posição lógica sobrevive à física;
- custo: 25.466 B contra 25.453 do anônimo puro = **+13 B (1,9 B/coluna)**.

Ou seja: não precisa de mecanismo novo — a gramática atual já expressa "posição como nome".
O que NÃO existe hoje é a forma **mista** (só a coluna movida com nome, as demais anônimas):
`''` anônima é limitada a uma por tabela (guard de colisão, `core.py:316-326`) e `drop_names`
é tudo-ou-nada. Se um dia valer a pena, é kwarg, não formato.

## 4. P4 — o risco reproduzido: colisão de nome posicional PERDE COLUNA CALADA

Wire à mão: coluna ANÔNIMA na posição 0 + coluna NOMEADA `"0"`:

```
#TCF.8M!3,!3=0,!fim
```

**Header declara 3 colunas; decode devolve 2.** A anônima decoda como `'0'`, a nomeada `"0"`
sobrescreve no dict, e os valores da primeira somem — sem warning, sem erro. Os cheques do
BUG-05 não pegam (bytes e n_rows fecham).

O encode não emite essa forma (chaves de dict são únicas; `''` tem guard próprio). É
decode-de-wire-estrangeiro — mas a régua do próprio BUG-05 ("integridade deduzida de graça")
cobre: **`len(result) == len(pares)` é 1 linha de fail-loud**. Registrado na nota-mãe §4.4;
mexe em src, aguarda aprovação.

## 5. O que isto responde da pergunta original

1. **"Um dataset pode não precisar respeitar a ordem"** — o formato já concorda: corpos
   independentes, RT em qualquer permutação. A ordem só carrega significado (a) na escolha da
   última (≤3 B aqui) e (b) quando as colunas são anônimas.
2. **"Fonte CSV / sem nomes"** — é o caso (b): posicional. Funciona, com o contrato de ordem
   fixado fora do fio — e o P2 é o que acontece quando esse contrato quebra.
3. **"O nome implícito ficaria explícito"** — sim, e **já é representável**: índice canônico
   como nome, 1,9 B/coluna. Falta só o guard do P4 para a mistura ser segura.
