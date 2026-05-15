# Apendice A: Especificacao do Formato TCF

*Sera preenchido com a especificacao formal completa (BNF/EBNF) do TCF.*

## A.1 Gramatica

```
tcf_document   ::= header newline+ table_block+
header         ::= "# TCF v0.1" newline hint_line*
hint_line      ::= "> " text newline
table_block    ::= table_header newline column_line+ newline?
table_header   ::= "## " name " n=" integer
column_line    ::= name tag? ": " value_list
tag            ::= "[key]" | "[sorted]"
value_list     ::= value (" " value)*
value          ::= rle_value | plain_value
rle_value      ::= integer ":" plain_value
plain_value    ::= number | string
```

## A.2 Exemplos

*Exemplos completos para cada variante de encoding.*
