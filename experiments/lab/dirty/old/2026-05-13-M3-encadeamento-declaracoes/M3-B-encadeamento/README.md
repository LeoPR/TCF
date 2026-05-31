# M3.B — Encadeamento de declaracoes (`&N=&P+ext`)

## Tecnica

Estende M3.A. Detector identifica substrings compartilhadas e
verifica se existe alias ja' declarado cujo texto e' prefixo desta.
Se sim, declara encadeada (`&N=&P+ext`); senao, absoluta
(`&N=texto`).

## Sintaxe

Preambulo:
```
&1=texto_raiz
&2=&1+ext     (= texto_raiz + ext)
&3=&2+ext2    (= texto_raiz + ext + ext2)
```

Body usa `&N` em qualquer nivel.

## Custos

- Decl absoluta: `&N=texto\n` = 4 + Lt
- Decl encadeada: `&N=&P+ext\n` = 5 + len(str(P)) + len(ext)
- Encadeada compensa absoluta quando: len(ext) < Lt - 1 - len(str(P))

## Resultado nos canonicos D1-D4

| Dataset | M1.E | M3.A | M3.B |
|---|---:|---:|---:|
| D1-D4 (total) | 676 | 676 | 676 |

**Net 0 em todos.** Detector nao seleciona aliases (mesma razao
de M3.A: M1.E ja' comprime refs).

## Resultado em DE7 (hierarquia profunda)

| Sintaxe | DE7 bytes |
|---|---:|
| M3.A | 119 |
| M3.B | 119 |

**Net 0 tambem em DE7** desenhado para favorecer M3.

## Diagnostico estrutural

DE7 tem unico candidato com R>=2: substring "https://api.example.com/v1/users/00"
(Lt=35) usada por 2 eids. Refs M1.E para essa substring:
- `1..5` (4 chars) porque frags consecutivos 1,2,3,4,5

Net absoluto = 2 * (4 - 2) - (4 + 35) = 4 - 39 = **-35**.
Net encadeado teorico = mesma economia, custo proximo. Tambem
negativo.

## Comparacao com Lab 20-21 antigo

Lab 20 antigo (`old/2026-05-20-hierarquia-profunda/`) reportou
ganho substancial em datasets com hierarquia profunda (C7
URLs -72% vs literal). Diferenca metodologica:

- **Lab 20**: NAO tinha range (`a..b`). Refs vinham como
  `1,2,3,4,5` (9 chars).
- **M3 atual**: M1.E (range) ja' comprime para `1..5` (4 chars).

A funcao de eficiencia do encadeamento depende de Lr (chars da
serializacao M1.E da substring). Em Lab 20, Lr era alto, dando
espaco para aliases. Em M3 atual com M1.E como base, Lr e' baixo
e o nicho desaparece.

## Implicacao matematica

Para alias compensar, exige:
    R * (Lr - 2) > 4 + Lt   (caso absoluto)
    R * (Lr - 2) > 5 + len(P) + len(ext)   (caso encadeado)

Quando Lr e' pequeno (range comprime), o lado esquerdo cresce
devagar com R. Custo de declaracao (Lt grande para hierarquia
profunda) domina.

Encadeamento ajudaria reduzindo lado direito (ext curta vs Lt),
mas apenas se houver chain de pais ja declarados. No DE7 ha'
apenas 1 candidato — sem chain disponivel.

## Regime onde M3.B compensaria (teorico)

1. Algoritmo base SEM range (Lr cresce com K refs)
2. OU substrings compartilhadas com R muito alto (>> 10)
3. OU cadeia profunda de 4+ niveis com pais ja declarados

Nenhuma condicao ocorre nos canonicos D1-D4 nem em DE7 (que tem
apenas 3 niveis hierarquicos).

## RT
4/4 canonicos OK + 1/1 DE7 OK.

## Estrutura

```
M3-B-encadeamento/
  README.md          (este)
  syntax.py          implementacao
  conclusoes.md      analise completa
  output/            TCFs canonicos
  decoded/           contra-prova canonicos
  debug/             detalhes canonicos
  output_extra/      TCFs DE7
  decoded_extra/     contra-prova DE7
  debug_extra/       detalhes DE7
```

## Limitacoes

- Detector greedy (R decrescente). Combinacoes melhores podem
  existir, mas o regime ja' nao compensa.
- `&` e `+` reservados em literais (escape `\&`, `\+`)
- Apenas pref/suf de eids existentes — nao busca substrings
  arbitrarias
- Para regime onde compensaria, precisaria algoritmo base SEM
  range, o que e' regressao

## Como rodar

```bash
cd 2026-05-13-M3-encadeamento-declaracoes
python run_lote.py          # canonicos
python run_lote_extra.py    # DE7
```
