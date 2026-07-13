# Specs cadastrais v1 — exploracao fora do core

**Data**: 2026-07-12
**Forca**: probatorio; nao constitui spec welded.
**Runner**: `run.py`
**Regra**: todos os candidatos medem o blob completo do FLOOR e validam
`decode(encode(x)) == x` com o spec declarado out-of-band.

## Metodo

Os prototipos locais usam o alfabeto seguro atual (`len(BASE94) = 80`),
sem tocar `src/tcf`. Os dados de hubs sao normalizados para `str`/`''` antes
da medicao. `br-identidades` e' sintetico; TPC-H e' benchmark sintetico.
RG, CEP e codigo fixo sao gerados apenas como formas de estresse, nao como
prova de formato oficial ou ganho real.

## Medicoes

| caso | linhas | baseline | candidato | delta | leitura |
|---|---:|---:|---:|---:|---|
| data ISO, pessoas, single | 5000 | 46417 | 25979 | -44.0% | forte candidato tecnico |
| data ISO, pessoas, multi | 5000 | 284386 | 284386 | 0.0% | split existente ja vence |
| data ISO, empresas, multi | 5000 | 176510 | 176510 | 0.0% | split existente ja vence |
| data ISO, TPC-H orders, multi | 15000 | 1042775 | 1038780 | -0.4% | ganho de tabela pequeno |
| datetime ISO, online-retail, single | 100 | 165 | 124 | -24.8% | formato fixo de amostra |
| telefone TPC-H, multi | 1500 | 180006 | 170851 | -5.1% | formato do benchmark, nao cadastro real |
| CEP mascarado random, single | 5000 | 59665 | 32425 | -45.7% | preserva zeros; falta dado real |
| CEP mascarado cluster, single | 5000 | 33818 | 31755 | -6.1% | FLOOR evita regressao |
| RG SP-shaped random, single | 5000 | 82578 | 34127 | -58.7% | apenas forma homogenea sintetica |
| RG SP-shaped sequencial, single | 5000 | 69669 | 30460 | -56.3% | nao representa politica nacional |
| codigo decimal fixo 11 random, single | 5000 | 69465 | 39308 | -43.4% | proxy CNH/RENAVAM, sem semantica |
| codigo decimal fixo 11 sequencial, single | 5000 | 77 | 77 | 0.0% | OBAT/HCC ja captura a estrutura |

Os prototipos de data, telefone, CEP e RG foram specs mascarados de zero
check-digit. O codigo fixo 11 usou uma classe local minima para demonstrar a
lacuna atual: `TemplatedCheckedSpec` deliberadamente trata valor sem mascara
como `format_unmasked` e faz fallback.

## Base 64/80/96

Comprimento teorico para um dominio decimal de `d` digitos:

| digitos | base64 | base80 seguro atual | base96 |
|---:|---:|---:|---:|
| 8 | 5 | 5 | 5 |
| 9 | 5 | 5 | 5 |
| 10 | 6 | 6 | 6 |
| 11 | 7 | 6 | 6 |
| 12 | 7 | 7 | 7 |
| 15 | 9 | 8 | 8 |
| 18 | 10 | 10 | 10 |

O nome historico `BASE94` representa hoje 80 caracteres seguros: os
caracteres reservados pela gramatica TCF foram removidos. Base64 nao traz
vantagem nesses dominios e perde para base80 em 11 digitos. Base96 exigiria
caracteres reservados, escaping adicional ou abandonar a promessa ASCII;
nao ha' ganho pratico demonstrado. A decisao recomendada e' manter o
alfabeto seguro atual e estudar uma `FixedAlphabetSpec` generica em `.9`.

## Decisao de escopo

- **`.8`**: nao adicionar RG/CNH/RENAVAM/PIS/telefone como specs canonicos sem
  formato nacional estavel e dataset real. Atualizar a documentacao para
  explicar que datas ISO/CEP sao candidatos medidos, nao features welded.
- **Candidato de menor risco para uma revisao do `.8`**: `DateSpec` ISO
  calendar-aware, se o owner aceitar uma mudanca adicional no core e o gate
  real-world; o ganho existe sobretudo em single-col, enquanto split ja'
  cobre varias tabelas.
- **`.9`**: `FixedDigitsSpec`/`FixedAlphabetSpec` generica, CEP com zeros
  preservados, identificadores fixos sem mascara, telefone var-width, RG por
  UF, CNH/RENAVAM/PIS com regras de validacao, registry carregavel e novos
  dados reais.
- **Nao fazer**: base96 no wire-format atual; transformar todo codigo
  cadastral em natureza apenas por ser numerico.

A massa de dados so' deve rodar depois do closeout e do smoke do `.8`. A
primeira janela deve usar o runner F3/F4 existente, amostras deterministicas,
RT, byte-canonicalidade, tempo, memoria e modo paralelo; depois, uma janela
separada para populacao total, sem misturar resultados de fechamento com
pesquisa de specs.
