# O delimitador do flip — opções (2026-07-26-0038)

Levanta o espaço de escolha com número em cada eixo. **Não decide nada.** Escopo: uma coluna, single-col.

## Eixo 1 — qual char

### Já tomados no corpo (levantado do `src/tcf`)

| char | papel |
|---|---|
| `\` | escape (literal de dígito, `*`, `~`, `\`) |
| `*` | início de marcador RLE / seq-RLE, e separador de fragmento no literal |
| `|` | separa contador do template no marcador |
| `~` | composição de fragmentos |
| `^` | referência de LINHA (início de linha) |
| `,` | separa unidades num grupo de referências |
| `.` | `..` = range de referências |
| `LF` | delimitador de valor (contrato LF-only) |
| `+` | sinal de delta no marcador seq-RLE |
| `-` | sinal de delta negativo no marcador seq-RLE |

### Candidatos livres — e quanto cada um já aparece no dado

Se o char escolhido ocorre no dado, ele passa a precisar de escape em modo FLIP — o que **cobra de volta** parte do ganho. Frequência medida nas 10 formas (n=500 cada, 70,185 chars):

| char | ocorrências no dado | em quais formas |
|---|---:|---|
| `!` | 0 | — |
| `"` | 2000 | json-ish |
| `#` | 0 | — |
| `$` | 500 | moeda |
| `%` | 0 | — |
| `&` | 0 | — |
| `'` | 0 | — |
| `(` | 500 | telefone |
| `)` | 500 | telefone |
| `/` | 4500 | data-br, url, path |
| `:` | 1500 | url, json-ish |
| `;` | 0 | — |
| `<` | 0 | — |
| `=` | 500 | url |
| `>` | 0 | — |
| `?` | 500 | url |
| `@` | 500 | email |
| `[` | 0 | — |
| `]` | 0 | — |
| `_` | 0 | — |
| ``` | 0 | — |
| `{` | 500 | json-ish |
| `}` | 500 | json-ish |

**12 candidatos com zero ocorrência** nesta amostra: `!` `#` `%` `&` `'` `;` `<` `>` `[` `]` `_` ```.

Ressalva: *zero nesta amostra* não é *zero no mundo*. `%`, `&`, `=`, `?`, `#` aparecem em URL/query; `:` em hora e JSON; `;` em CSV europeu. O char mais seguro é o que **nunca** aparece em dado tabular — mas nenhum é impossível, então o esquema tem que suportar escapá-lo.

## Eixo 2 — onde aplicar o delimitador

**(a) só na posição ambígua** — 1 B por adjacência · **(b) terminar TODA referência** — 1 B por referência (parser mais simples)

| forma | corpo | ganho bruto | adjac. | (a) líquido | refs | (b) líquido |
|---|---:|---:|---:|---:|---:|---:|
| int-ruido | 3922 | +500 | 0 | **+500** | 0 | **+500** |
| data-br | 4905 | +77 | 320 | **-243** | 649 | **-572** |
| telefone | 8244 | +764 | 410 | **+354** | 508 | **+256** |
| moeda | 6226 | +900 | 104 | **+796** | 136 | **+764** |
| versao | 4929 | +114 | 233 | **-119** | 640 | **-526** |
| email | 5743 | -812 | 150 | **-962** | 1179 | **-1991** |
| url | 6563 | -137 | 481 | **-618** | 826 | **-963** |
| json-ish | 5348 | -1333 | 117 | **-1450** | 1513 | **-2846** |
| path | 6319 | -831 | 286 | **-1117** | 1298 | **-2129** |
| hex | 5711 | +1211 | 0 | **+1211** | 0 | **+1211** |

Somando só onde cada esquema ganha: **(a) 2861 B** · **(b) 2731 B**.

A opção (b) é mais simples de parsear (toda referência tem terminador, sem olhar o que vem depois), mas paga em **toda** referência — e em coluna de texto as referências são muitas. A (a) paga só onde precisa, ao custo de o parser decidir por contexto.

## Eixo 3 — alternativas que NÃO gastam um char do namespace

| alternativa | como funciona | custo | observação |
|---|---|---|---|
| escape duplo | na posição ambígua, o literal vira `\\` + dígitos | **2 B** por adjacência (o dobro de (a)) | não gasta char novo; `\\` já é escape de `\` hoje, então colide — precisaria de outra grafia |
| referência de largura fixa | `\` + N dígitos fixos, sem terminador | custo = (largura − dígitos reais) por referência | só compensa se a tabela for pequena e as refs curtas; some o ganho em coluna com muitas refs |
| flip só onde não há adjacência | o detector já existe; desiste da coluna | **0 B** | cobre 20 das 33 colunas que ganhariam — deixa na mesa os casos valiosos (telefone, moeda) |

Números da terceira linha vêm do lab `2026-07-25-2337` parte 2.

## Amostras dos corpos (para inspeção)

```
int-ruido   '\\168116'
data-br     '\\13*/\\10/\\20*\\3*\\8'
telefone    '(\\46) \\9*\\6*\\333-\\5938'
email       'user\\81*\\1*\\6*@d\\3.com'
```

