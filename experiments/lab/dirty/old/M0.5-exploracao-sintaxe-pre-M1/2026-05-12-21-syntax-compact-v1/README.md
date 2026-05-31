# 21 — sintaxe compacta v1 (marcadores explícitos de 1 char)

## Princípio / motivação

O exp 20 estabeleceu a interface `Syntax` que desacopla algoritmo
de sintaxe. Este experimento é a primeira **alternativa real** —
implementa marcadores compactos explícitos da Direção 1 da nota
[`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md).

O algoritmo (`online.py`) **não muda**. Os tokens produzidos são
os mesmos. Só a serialização muda — testando a hipótese central
do exp 19 de que a "perda em bytes verbosos" de variantes
algorítmicas se diluiria em sintaxe compacta.

## Propósito

1. **Validar a hipótese da nota** `marcadores-compactos`:
   marcadores compactos reduzem bytes mantendo unidades.
2. **Medir o ganho real em bytes** vs verbose nos 21 datasets já
   estudados (3 do exp 15 + 6 do exp 17 + 12 do exp 18).
3. **Confirmar que `Syntax` é interface boa o suficiente** — a
   nova sintaxe encaixa sem mexer no algoritmo.

## Comparação

- **Compara com**: VerboseSyntax do exp 20 (que reproduz exp 16).
  Ambas as sintaxes rodam **lado a lado** no mesmo `run.py`, com
  o **mesmo algoritmo** produzindo os **mesmos tokens** — a única
  diferença é a serialização.
- **Métricas**: bytes totais do TCF (incluindo macros `[` / `]`
  vs `<body>` / `</body>`), roundtrip por sintaxe, unidades
  (idêntico entre as duas — confere com o tokens).

## Mapeamento dos marcadores

| Verbose | Compact v1 | Redução por uso |
|---|---|---:|
| `noN`             | `@N`           | -1 char |
| `noN[0:K]`        | `@N<K`         | -4 chars |
| `noN[-K:]`        | `@N>K`         | -5 chars |
| `"X"`             | `'X'`          | igual |
| `+` (com espaços) | (omitido)      | -3 chars |
| `noN: forma`      | `@N:forma`     | -1 char (sem espaço) |
| `ref:noN`         | `=N`           | -4 chars |
| `Nx ref:noN`      | `Nx=N`         | -4 chars |
| `<body>` / `</body>` | `[` / `]`   | -5 chars cada |

Concatenação entre tokens é **implícita** — cada token começa com
char distintivo:
- `@` → ref (pref ou suf)
- `'` → literal

Decoder parsea sequencialmente pela posição.

## Exemplo lado a lado (D2-mini)

**Verbose** (208 bytes):
```
<body>
  no1: "maria.silva@gmail.com"
  no2: no1[0:12] + "hot" + no1[-8:]
  no3: no1[0:12] + "yahoo" + no1[-4:]
  no4: "joao.souz" + no1[-11:]
  no5: no4[0:11] + no2[-11:]
  no6: no4[0:11] + no3[-9:]
</body>
```

**Compact v1** (116 bytes — redução de 44%):
```
[
@1:'maria.silva@gmail.com'
@2:@1<12'hot'@1>8
@3:@1<12'yahoo'@1>4
@4:'joao.souz'@1>11
@5:@4<11@2>11
@6:@4<11@3>9
]
```

## Resultado observado

Roundtrip **21/21 OK em ambas as sintaxes.**

### Bytes por sintaxe

| Dataset | unid | verbose | compact | redução | razão |
|---|---:|---:|---:|---:|---:|
| D2-mini | 47 | 208 | 116 | -92 | 0.558 |
| D2-completo | 78 | 456 | 232 | -224 | 0.509 |
| D4 | 75 | 414 | 222 | -192 | 0.536 |
| urls | 128 | 448 | 270 | -178 | 0.603 |
| uuids | 430 | 578 | 512 | -66 | **0.886** |
| iso-timestamps | 49 | 395 | 197 | -198 | 0.499 |
| ips | 52 | 319 | 170 | -149 | 0.533 |
| cpfs | 168 | 306 | 247 | -59 | **0.807** |
| codigos | 38 | 322 | 166 | -156 | 0.516 |
| urls-N0050 | 228 | 1636 | 894 | -742 | 0.546 |
| urls-N0200 | 553 | 6201 | 3379 | -2822 | 0.545 |
| urls-N1000 | 2255 | 31299 | 17509 | -13790 | 0.559 |
| iso-N0050 | 269 | 1876 | 979 | -897 | 0.522 |
| iso-N0200 | 648 | 7054 | 3724 | -3330 | 0.528 |
| iso-N1000 | 2264 | 33581 | 18209 | -15372 | 0.542 |
| ips-N0050 | 184 | 1237 | 703 | -534 | 0.568 |
| ips-N0200 | 553 | 5025 | 2868 | -2157 | 0.571 |
| ips-N1000 | 2092 | 28457 | 15043 | -13414 | 0.529 |
| codigos-N0050 | 119 | 1353 | 707 | -646 | 0.523 |
| codigos-N0200 | 427 | 5665 | 3069 | -2596 | 0.542 |
| codigos-N1000 | 2067 | 29296 | 16292 | -13004 | 0.556 |
| **TOTAL** | | **156126** | **85508** | **-70618** | **0.548** |

**Compact v1 produz 54.8% dos bytes da verbose.** Em outras
palavras, **redução de 45.2%** mantendo lossless roundtrip.

### Custo por unidade de informação (bytes/unidade)

| Sintaxe | médio | mínimo | máximo |
|---|---:|---:|---:|
| Verbose | 8.5 | 1.34 (uuids) | 14.83 (iso-N1000) |
| Compact v1 | 4.6 | 1.19 (uuids) | 8.04 (iso-N1000) |

Em regime estável (muitas refs, poucos literais), compact v1
custa ~7-8 bytes/unidade. Verbose custava ~13-15. **A sintaxe
compacta corta o custo por unidade aproximadamente pela metade**.

### Casos onde a redução é menor

| Dataset | Razão | Razão LCP/LCS |
|---|---:|---:|
| uuids | 0.886 (-11%) | cobertura ref ≈ 0% (1 ref total) |
| cpfs | 0.807 (-19%) | cobertura ref ≈ 0% (0 refs) |

Esses datasets do regime B do exp 17 são **quase todo literal**.
Como literais têm o mesmo custo nas duas sintaxes (`"X"` e
`'X'` ocupam mesmos chars), a redução vem só dos overheads
estruturais (`<body>` → `[`, `no` → `@`, `:` sem espaço).

## Observações

1. **Algoritmo intocado**: `online.py` é idêntico ao do exp 20
   (e exp 16). Mesmo arquivo, copiado entre exps.

2. **Tokens idênticos**: a coluna "unid" coincide para ambas
   as sintaxes — confirma que o algoritmo produz o mesmo objeto
   intermediário e só a serialização muda.

3. **O ganho é consistente** em datasets do regime A: razão
   entre 0.499 e 0.603 (~50%). A variação reflete densidade de
   refs vs literais.

4. **A nota** [`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md)
   **previu este resultado**. A métrica de "unidades de
   informação" foi calibrada para ser invariante sob mudança de
   sintaxe, e funcionou: unidades iguais nas duas, bytes
   diferentes.

## Limitações

- **Literais não podem conter `'`**. Em datasets atuais isso não
  ocorre. Strings com aspas simples no conteúdo quebrariam o
  parser — precisaria de escape (deferido).
- **Sintaxe ainda é texto puro**, não chega ao limite teórico.
  Marcadores binários ou inferência pela ordem (Direção 2 da
  nota) podem reduzir mais.
- **Comparação com gzip ainda não foi feita**. O ganho de 45%
  pode ou não sobreviver após compressão estatística do TCF.
- **21 datasets sintéticos**. Datasets reais podem variar.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-21-syntax-compact-v1
python run.py
```

Saída: tabela de 21 datasets × 2 sintaxes, com bytes e razão.
TCFs em `encoded/verbose/` e `encoded/compact_v1/` para
inspeção visual.

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. **Hipótese da nota validada**: marcadores compactos reduzem
   bytes ~45% sem mudar algoritmo
2. **Custo por unidade cai pela metade** (8.5 → 4.6 bytes/unid)
3. **Interface `Syntax` é boa o suficiente** para suportar essa
   troca radical
4. **Próxima direção**: comparar com gzip(verbose) e
   gzip(compact) para ver se o ganho sobrevive — e tentar a
   Direção 2 da nota (inferência pela ordem) como sintaxe v2
