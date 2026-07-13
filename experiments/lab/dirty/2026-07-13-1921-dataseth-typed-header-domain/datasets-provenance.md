# Proveniencia dos dados

**Tipo**: fixtures sinteticos construidos para falsificacao semantica.

Nenhum dataset externo, arquivo em `Z:/tcf-data/` ou dado pessoal foi usado.
Os cinco perfis vivem em `run.py` e sao reproduzidos para exercitar:

- pares que devem permanecer distintos: `null`/`"null"`, `NaN`/`"NaN"`,
  infinitos/literais, `-0.0`/`0.0`, inteiro/numero/string e bool/integer;
- dominio pequeno repetido, onde um `bN` de dominio total pode pagar;
- 100 strings distintas com poucos especiais, onde o dominio total deixa de
  caber em `b4` e o stream de kinds permanece pequeno;
- numericos e strings de mesma superficie.

O vies e deliberado: esses perfis foram construidos para falsificar colisoes e
caracterizar custos mecanicos. Eles nao medem frequencia de especiais em dados
reais, compressao weighted, comportamento sob brotli, nem capacidade de uma
arvore ragged. Qualquer decisao de formato continua dependente dos gates P4/P5
do plano e do ticket de weld.
