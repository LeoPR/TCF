# 2026-07-26-1853 — O delimitador de POLARIDADE

> *"no caso do `56\033-\0910-\4383` não bastaria usar um `/56/033-0910-4383`? aqui ele separa
> o 56 como ref, o que vier depois é literal. ainda simplificado `56/033-0910-4383`. e se
> alguma ref no meio: `56/033-09/10-4383` (…) é disso que falo como uma troca barata, rápida."*

Sim. E é melhor do que a máscara do lab `0330` em quase tudo.

## Por que funciona

O delimitador não marca um valor — marca uma **troca de estado**. Custa por **transição**,
não por ocorrência. E, por estar *entre* as duas corridas, ele carrega a **fronteira** junto:
`56/033` não funde, que era exatamente o bloqueador que derrubou a máscara, o flip e o
sem-escape.

```
#TCF.8                       #TCF.8d/L
\000.\000.\000-\00           000.000.000-00
\001.\007.\013-\01           001.007.013-01
\002.\014.\026-\02           002.014.026-02
```
(`outputs/cpf-wire-normal.tcf` × `outputs/cpf-wire-delim.tcfp` — **800 escapes → 0**)

## Medição

| forma | corpo | hoje | trans. (R) | trans. (L) | char | início | custo | Δ corpo |
|---|---:|---:|---:|---:|:-:|:-:|---:|---:|
| `cpf` | 3800 | 800 | 200 | **0** | `/` | L | **0** | **−800** |
| `cartao` | 11960 | 2000 | 513 | 25 | `/` | L | 25 | **−1975** |
| `cnpj-mascara` | 9774 | 1714 | 975 | 515 | `!` | L | 515 | **−1199** |
| `cep` | 5990 | 997 | 500 | 5 | `/` | L | 5 | **−992** |
| `telefone` | 8244 | 1272 | 504 | 824 | `/` | R | 504 | **−768** |
| `data-br` | 4905 | 726 | 457 | 681 | `!` | R | 457 | **−269** |
| `ip` | 2851 | 256 | 64 | **0** | `/` | L | **0** | **−256** |
| `data-iso` | 5513 | 677 | 458 | 689 | `/` | R | 458 | **−219** |
| `texto` | 1807 | 0 | 0 | 25 | `/` | R | 0 | 0 |
| `email` | 5743 | 367 | 472 | 788 | `/` | R | 472 | **+105** |

- reconstrução byte-exata da grafia canônica **e** RT pelo `decode` REAL: **20/20**
- ganho somado: **−6373 B** · perde em **1 de 10** (`email`, +105)

## Contra a máscara do lab `0330`

| forma | escapes hoje | máscara | delimitador |
|---|---:|---|---:|
| `cpf` | 800 | 4 | **0** |
| `ip` | 256 | 4 | **0** |
| `cartao` | 2000 | n/a (adjacência) | **25** |
| `cep` | 997 | n/a (adjacência) | **5** |
| `telefone` | 1272 | n/a (adjacência) | **504** |
| `data-iso` | 677 | n/a (adjacência) | **458** |
| `email` | 367 | n/a (adjacência) | 472 |

A máscara cobria 3 de 8 formas e precisava de um canal separado. O delimitador cobre **todas**,
é inline, e a linha continua **auto-contida**.

## Ele é mais expressivo que o escape de hoje

Hoje `literal` seguido de `referência` **não tem grafia**: `\03356` lê tudo como um literal
só. Com o delimitador tem — `/033/56`. Não é só mais barato, é uma grafia que não existia.

## O char não é fixo — e a evidência disso está na tabela

Qualquer char pode aparecer no dado (o `\` de hoje tem o mesmo problema), então cada
ocorrência dele passaria a custar escape. Por isso ele entra na conta:

| forma | `/` | `!` | escolhido |
|---|---:|---:|:-:|
| `cpf`, `cartao`, `ip`, `cep`, `telefone`, `data-iso`, `email`, `texto` | 0 | 0 | `/` |
| `data-br` | **116** | 0 | `!` |
| `cnpj-mascara` | **25** | 0 | `!` |

`data-br` e `cnpj-mascara` existem no lab **só para provar que o `min` troca de candidato** —
sem elas a tabela seria toda zero e não provaria nada.

## A escolha é uma conta, não um experimento

```
hoje        = corridas literais
transicoes  = trocas de estado           (2 contadores, um por polaridade inicial)
ocorrencias = o char candidato no dado   (1 contador por candidato)
escolha     = min sobre (candidato x polaridade)
```

Todos são contadores da **mesma passada** que já percorre o corpo. Nada é materializado duas
vezes para comparar — que era a restrição sobre os vetores ortogonais.

## Limites

- **Nada soldado.** `src/tcf` intocado. `d<char><polaridade>` no cabeçalho é notação do lab.
- **Aberto e não medido**: se o delimitador virar grafia **canônica** (e não camada de
  borda), o seq-RLE precisa localizar o dígito incrementável **pela polaridade** em vez de
  pelo escape. Como camada de borda o corpo canônico é reconstruído antes de tudo, e isso foi
  verificado com `find_escape_digit_runs` do próprio core: **0** marcadores divergentes.
- O `email` **perde** (+105 B): fluxo muito alternado, mais transições que literais. A regra
  recusa sozinha e cai no comportamento de hoje.
- Estado reseta por linha (mantém a linha auto-contida). Estado global entre linhas não foi
  medido — pouparia mais no `cpf`-like, mas quebraria a auto-contenção.
- Formas **sintéticas por LCG** — ver `datasets-provenance.md`. Nenhum CPF/CNPJ válido.

## Rodar

```
python run.py
```
`polaridade.py` tem os contadores, o `min` e as duas direções.
