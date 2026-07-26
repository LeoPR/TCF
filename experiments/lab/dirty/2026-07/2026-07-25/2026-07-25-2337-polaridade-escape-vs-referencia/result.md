# Polaridade do escape — literal x referência (2026-07-25-2337)

`NORMAL` = hoje (`\168116` literal · `1` referência). `FLIP` = invertido (`168116` literal · `\1` referência).

A troca **deveria** ser uma involução (`normal → flip → normal` = identidade). Onde não é, o flip é **inexpressável** — ver a seção de adjacência.

| id | corpo NORMAL | corpo FLIP | Δ | adjacências ambíguas | flip é seguro? |
|---|---:|---:|---:|---:|---|
| `A-ruido1e6-n1000` | 7854 | 6856 | **-998** | 0 | sim |
| `A-ruido1e6-n100` | 793 | 693 | **-100** | 0 | sim |
| `A-cpf-like-n200` | 3800 | 3000 | **-800** | 0 | sim |
| `A-uuid-hex-n200` | 2663 | 2200 | **-463** | 0 | sim |
| `A-precos-n200` | 1175 | 1027 | **-148** | 0 | sim |
| `B-datas-n200` | 1110 | 1131 | **+21** | 74 | **NAO** |
| `C-emails-n200` | 2095 | 2316 | **+221** | 0 | sim |
| `C-texto-n200` | 718 | 743 | **+25** | 0 | sim |
| `D-seq-n1000` | 31 | 28 | **-3** | 0 | sim |
| `D-ruido0a9-n1000` | 3104 | 3094 | **-10** | 0 | sim |

## Leitura

- **7 de 10** colunas ficam menores com o FLIP; **2** ficam maiores.
- ganho somado onde ganha: **2522 B** · perda somada onde perde: **-246 B**
- **1 coluna(s) NÃO podem ser flipadas** com este esquema (adjacência ambígua, abaixo)

As colunas que **perdem** (emails, texto sem dígito) são a razão de isto não poder virar default novo — tem que ser **decisão por coluna**, um `min()` como os outros. É exatamente o que o owner descreveu: *o que tiver mais, troca*.

## Lado a lado — as duas polaridades

```
A-ruido1e6-n100
  normal: '\\168116' …
  flip  : '168116' …
C-texto-n200
  normal: 'palavra*a' …
  flip  : 'palavra*a' …
```

