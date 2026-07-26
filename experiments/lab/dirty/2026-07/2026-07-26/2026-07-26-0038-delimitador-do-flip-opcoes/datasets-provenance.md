# Proveniência — delimitador do flip (2026-07-26-0038)

**Fonte**: 100% sintético/determinístico (LCG de seed fixa). Nenhum download, nenhum dado real.

## As 10 formas, e por que essas

Escolhidas para **cobrir os chars candidatos** — não para amostrar frequência real de uso.
Cada uma existe porque introduz um caractere diferente no dado:

| forma | traz o char |
|---|---|
| `int-ruido`, `hex` | nenhum — controle sem char especial |
| `data-br`, `path`, `url` | `/` |
| `telefone` | `(` `)` |
| `moeda` | `$` |
| `versao` | `.` (já estrutural) |
| `email` | `@` |
| `url` | `:` `?` `=` |
| `json-ish` | `"` `{` `}` `:` |

`n = 500` em todas, para a frequência ser comparável entre formas.

## Limite importante da amostra

A tabela de frequência mede **esta amostra**, não o mundo. Um char com zero aqui pode ser
comum em outro domínio — `%` em query string, `;` em CSV europeu, `<` `>` em XML/HTML. A
tabela serve para **eliminar** os obviamente ruins (`/`, `"`, `:`), não para eleger o bom.

## O que é medição e o que é estimativa

- **Medição**: os corpos (`_encode_column` real), a contagem de escapes, de referências e de
  adjacências — tudo percorrendo o corpo com a mesma lógica do parser.
- **Estimativa**: os "líquidos" do eixo 2 são `ganho − (adjacências ou referências) × 1 B`.
  **Nenhuma das opções foi materializada.** O lab anterior (`2026-07-25-2337`) mostrou que
  contagem pode errar feio — lá a estimativa deu −38 B onde o real era +221 B, porque
  composições `1~2` precisam de um escape por corrida, não por token. Aqui o risco é menor
  (o delimitador é literalmente 1 B por posição contada), mas a ressalva vale: **antes de
  soldar, materializar**.
- **Eixo 3** não tem medição própria — os números vêm do lab anterior (terceira linha) ou são
  dedução direta do esquema (linhas 1 e 2).

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede. **Zero escrita em `src/tcf`.**
