# Marcadores compactos e inferidos — nota conceitual para resgate

Data: 2026-05-11
Contexto: pedido do user durante a fase exp 17/18.
Status: **direção futura**, não foco do ciclo atual.

---

## O que existe hoje (exp 16)

Sintaxe verbosa por design, escolhida para legibilidade visual:

```
no1: "maria.silva@gmail.com"
no2: no1[0:12] + "hot" + no1[-8:]
no5: no4[0:11] + no2[-11:]
ref:no1
3x ref:no1
</body>
```

Marcadores explícitos:

| Marcador | Função | Bytes hoje |
|---|---|---:|
| `noN` | id de um nó pela posição | 3-4 chars |
| `noN[0:K]` | prefixo de K chars de noN | 8-10 chars |
| `noN[-K:]` | sufixo de K chars de noN | 8-10 chars |
| `"X"` | delimita literal | 2 chars |
| `+` | concatenação | 3 chars (com espaços) |
| `:` | separa decl-head da forma | 2 chars |
| `ref:noN` | referência a nó já declarado | 6-9 chars |
| `Nx ` | RLE adjacente | 3-4 chars |
| `<body>` / `</body>` | marcadores macro | 14 chars total |

A nota [`custo-de-marcadores`](2026-05-11-custo-de-marcadores.md)
discute que esse custo é **elástico** — na fase prototype pode
cair para 1-2 bytes por marcador.

## O que o user quer registrar

Duas direções complementares:

### Direção 1 — marcadores ultra-compactos e previsíveis

Reduzir cada marcador para o mínimo de bytes mantendo
**previsibilidade** (uma sintaxe regular, sem ambiguidade,
parseável por máquina trivialmente).

Exemplos a explorar:

- `no` → símbolo de 1 char (talvez `@` ou `$`)
- `[0:K]` / `[-K:]` → forma curta como `<K` (prefix de K) e `>K`
  (sufix de K)
- `+` → omitido (separação por sintaxe posicional)
- `ref:noN` → símbolo de 1 char + id
- `<body>` → 1 byte sentinela

Exemplo hipotético da mesma linha do exp 15:

```
@1: 'maria.silva@gmail.com'
@2: @1<12'hot'@1>8
@5: @4<11@2>11
=1
3x=1
```

Trade-off: ganho real em bytes, perda de leitura visual.

### Direção 2 — marcadores inferidos pela ordem/gramática

Em vez de explicitar marcadores, **deduzi-los pela posição** dentro
de uma gramática regular sem ambiguidade.

Exemplos a explorar:

- **id implícito por linha**: a 1ª linha é `no1`, a 2ª é `no2`. O
  decoder conta linhas — não precisa do `noN:` no head.
- **prefix/sufix por ordem na sequência**: o 1º token é sempre
  prefix-ou-literal; o último é sufix-ou-literal; o meio é
  literal. Sem precisar de `[0:K]` / `[-K:]` — só `K` (com sinal
  para indicar lado se ambíguo).
- **continuação implícita**: se uma linha começa com chars que
  são números, é ref; se começa com aspas, é literal.

Exemplo hipotético:

```
'maria.silva@gmail.com'
12 'hot' 8
12 'yahoo' 4
'joao.souz' 11
4:11 2:11
4:11 3:9
```

Onde a 1ª linha é no1 (literal puro), a 2ª é no2 (12 chars de
pref de no1 anterior, literal `'hot'`, 8 chars de sufix de no1), e
assim por diante. `4:11 2:11` = pref de no4 com 11 chars + suf de
no2 com 11 chars (sem literal no meio).

Trade-off: muito compacto, mas decoder precisa de gramática rígida.
Qualquer ambiguidade quebra tudo. Risco real de regredir em
inspecionabilidade.

## O que precisa ser cuidado

1. **Ambiguidade zero**: gramática deve permitir parseamento sem
   backtracking. Cada char ou grupo é só uma coisa.
2. **Manter roundtrip**: a transformação para compacto deve ser
   inversível char por char.
3. **Comparabilidade**: o algoritmo do exp 16 e o formato compacto
   precisam medir a mesma coisa em "unidades de informação". A
   métrica existente já é robusta a essa mudança (ver
   `custo-de-marcadores.md`).
4. **Bytes reais vs estimados**: hoje reportamos unidades + bytes
   verbosos. Quando esse tema voltar, precisaremos rodar TCFs em
   ambos os formatos para validar que a estimativa em unidades
   coincide com bytes reais ±constante.

## Quando retomar

Quando o algoritmo lossless tiver:

- Estabilidade em famílias variadas (em curso — exp 17)
- Comportamento medido em escala (exp 18 próximo)
- Variantes algorítmicas exploradas (exps 19, 20, 21)

Marcadores compactos não muda o algoritmo, só a **camada de
serialização**. É experimento de "formato", não de "algoritmo".
Cabe num exp dedicado quando o algoritmo estiver fechado.

## Arquivos relacionados

- [`custo-de-marcadores.md`](2026-05-11-custo-de-marcadores.md) —
  teoria por trás da métrica de unidades
- [`comparacoes-nao-literais.md`](2026-05-11-comparacoes-nao-literais.md)
  — outras camadas (delta, lossy) que podem entrar antes ou
  depois do encoder
