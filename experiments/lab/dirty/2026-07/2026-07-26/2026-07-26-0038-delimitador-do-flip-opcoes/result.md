# O delimitador do flip — variantes MATERIALIZADAS (2026-07-26-0038)

Correção da 1ª rodada: os ganhos eram **estimativa** (`ganho − contagem × 1 B`) e só o corpo NORMAL ia pra pasta. Agora as três formas são construídas, gravadas **com cabeçalho** e round-trip-adas.

`normal` = wire REAL de hoje · `flipA` = delimitador só na adjacência · `flipB` = toda referência terminada. Delimitador `;` é **placeholder**.

**Bytes do wire INTEIRO** (cabeçalho + corpo), n=500:

| forma | tag | JSON | normal | flipA | Δ A | flipB | Δ B | wire flipado |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `int-ruido` | `n` | 3423 | 3930 | 3431 | **-499** | 3431 | **-499** | ok |
| `int-seq` | `n` | 1891 | 39 | 37 | **-2** | 37 | **-2** | **wire INVÁLIDO** |
| `hex` | `s` | 5501 | 5718 | 4509 | **-1209** | 4509 | **-1209** | ok |
| `data-br` | `s` | 6501 | 4912 | 5157 | **+245** | 5198 | **+286** | ok |
| `telefone` | `s` | 9001 | 8251 | 7899 | **-352** | 7903 | **-348** | ok |
| `moeda` | `s` | 6443 | 6233 | 5439 | **-794** | 5454 | **-779** | ok |
| `versao` | `s` | 4645 | 4936 | 5057 | **+121** | 5182 | **+246** | ok |
| `email` | `s` | 8943 | 5750 | 6714 | **+964** | 7202 | **+1452** | ok |
| `url` | `s` | 15388 | 6570 | 7190 | **+620** | 7207 | **+637** | ok |
| `path` | `s` | 12403 | 6326 | 7445 | **+1119** | 7848 | **+1522** | ok |
| `json-ish` | `s` | 13947 | 5355 | 6807 | **+1452** | 7297 | **+1942** | ok |
| `com-delim` | `s` | 5443 | 3715 | 4650 | **+935** | 4936 | **+1221** | **wire INVÁLIDO** |

## O RT deste lab é CIRCULAR — e a verificação adversarial provou

O lab faz `flip -> des-flip -> decode`. Isso testa a consistência do par de funções do próprio lab, **não a decodabilidade da forma flipada** — nenhum `.tcfp` é passado ao `decode`. Um verificador independente escreveu um leitor do corpo FLIP e achou **2 de 12 colunas com RT=OK e wire corrompido**.

Detector estrutural (independente do round-trip), sobre o corpo FLIP:

| forma | linha `0` = null | seq-RLE perde o escape | linha vira `^` |
|---|---:|---:|---:|
| `int-seq` | 1 | 3 | 0 |
| `com-delim` | 0 | 1 | 0 |

**As linhas marcadas `wire INVÁLIDO` na tabela acima medem bytes de um corpo que nenhum decoder consegue ler.** O número é real; o que ele mede não serve.

RT interno (não-conclusivo): 36/36.

- **flipA** ganha em 5 de 12 colunas; soma onde ganha **-2856 B**, perde **+5456 B** onde perde
- **flipB** ganha em 5 de 12; soma onde ganha **-2837 B**, perde **+7306 B**

O `min(normal, flipA, flipB)` por coluna nunca emite o pior — as linhas positivas seriam simplesmente descartadas, como já acontece no FLOOR do seq-RLE.

## Custo de cabeçalho (o que a 1ª rodada ignorou)

O flag de polaridade mora no char de **modo** (índice 7), que só existe **depois de uma tag**:

| tipo | cabeçalho hoje | com flag | custo |
|---|---|---|---:|
| número | `#TCF.8n` | `#TCF.8nf` | **+1 B** |
| string | `#TCF.8` (implícita) | `#TCF.8sf` | **+2 B** |

Flipar uma coluna de string **força torná-la explícita** — a tag `s`, que hoje o encoder nunca emite, passaria a aparecer. É consequência de desenho, não custo escondido: já está somado nos números da tabela acima.

## Amostra — as três formas lado a lado

```
--- int-ruido
  normal  '#TCF.8n' + '\\168116'
  flipA   '#TCF.8nf' + '168116'
  flipB   '#TCF.8nf' + '168116'
--- data-br
  normal  '#TCF.8' + '\\13*/\\10/\\20*\\3*\\8'
  flipA   '#TCF.8sf' + '13*/10/20*3*8'
  flipB   '#TCF.8sf' + '13*/10/20*3*8'
--- email
  normal  '#TCF.8' + 'user\\81*\\1*\\6*@d\\3.com'
  flipA   '#TCF.8sf' + 'user81*1*6*@d3.com'
  flipB   '#TCF.8sf' + 'user81*1*6*@d3.com'
--- com-delim
  normal  '#TCF.8' + 'a;b*\\5*\\6*\\7;c'
  flipA   '#TCF.8sf' + 'a\\;b*5*6*7\\;c'
  flipB   '#TCF.8sf' + 'a\\;b*5*6*7\\;c'
```

`com-delim` existe para exercitar o caso em que o **delimitador aparece no dado**: em FLIP o `;` vira estrutural e o literal precisa de escape (`\;`). O RT dessa coluna é a prova de que o esquema aguenta o próprio delimitador.

