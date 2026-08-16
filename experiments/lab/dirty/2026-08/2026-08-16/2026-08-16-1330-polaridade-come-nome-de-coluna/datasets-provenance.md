# Procedência — sintético, e o dado não é a variável

Nenhum dado de `Z:`. O lab varia o **NOME** da coluna, não os valores: 26 valores sintéticos
`v0..v25` fixos em todos os casos, e o nome percorre `'ab' + p` e `'ab' + p + p` para cada `p`
em `string.punctuation` (32 chars ASCII → 64 nomes).

**A CONSTANTE**: os mesmos 26 valores em todos os braços. Muda só o(s) último(s) caractere(s)
do nome — e, no Bloco 1, o número de valores (3/5/10/26/100) para expor a dependência de modo.

## Por que sintético é o certo aqui

O defeito é de **gramática de header**, não de dado. Dado real acrescentaria ruído sem
acrescentar cobertura: o que importa é o alfabeto de nomes, e ele é enumerável.

## Viés declarado

- **Só ASCII.** `string.punctuation` são 32 caracteres; nomes reais podem ter Unicode
  (`ç`, `°`, `€`) e isso **não foi varrido**.
- **Nome com prefixo fixo `ab`.** Não testei nome de 1 caractere, nem nome que seja só
  pontuação, nem nome vazio.
- **Uma coluna e duas colunas.** Não testei 3+, nem `drop_names=True`, onde a última coluna é
  anônima e o fim da linha 1 é outro.
