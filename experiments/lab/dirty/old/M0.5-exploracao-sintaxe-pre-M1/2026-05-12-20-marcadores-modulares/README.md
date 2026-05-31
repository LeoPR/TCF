# 20 — modularização de marcadores (Syntax plugável)

## Princípio / motivação

Antes de explorar sintaxes compactas (que mudam radicalmente o
formato textual), é preciso desacoplar o **algoritmo de
compressão** (tokens) da **linguagem de marcação** (sintaxe). Hoje
os dois estão misturados em `encode_online.py` e
`decode_online.py` — qualquer experimento de sintaxe quebra o
algoritmo e vice-versa.

A intenção declarada pelo user: aceitar **mais código e menos
eficiência** em prol de **clareza** e **possibilidade de trocar
radicalmente** a sintaxe sem mexer no algoritmo. Só depois de
ter várias sintaxes testadas e uma escolhida, considerar a
"fusão" entre as duas camadas para performance.

## Propósito

Resposta à **pergunta 1** do dirty (viabilidade técnica de
modularização). Não muda comportamento — muda estrutura.

## Comparação

- **Compara com**: [16 (online cleanup)](../2026-05-11-16-online-cleanup/)
  e [19 (par A+B)](../2026-05-12-19-par-AB-independente/).
- **Critério de equivalência**: TCFs gerados pela `VerboseSyntax`
  byte-idênticos aos do exp 16. Bytes e unidades também iguais.
- **Datasets**: os 21 do exp 19 (3 do exp 15 + 6 do exp 17 +
  12 do exp 18).

## Arquitetura

```
online.py        algoritmo de compressao (intocado)
                 produz tokens: TokLit, TokRefPref, TokRefSuf

syntax_base.py   interface abstrata `Syntax(ABC)`
                 metodos: encode(...) -> str
                          decode(tcf_text) -> list[str]
                 contrato: roundtrip lossless

syntax_verbose.py  implementacao `VerboseSyntax(Syntax)`
                   reproduz exatamente o formato do exp 16
                   marcadores: noN[0:K], noN[-K:], "X", +, ref:noN, Nx

run.py           pluga a sintaxe escolhida via instancia
                 testa nos 21 datasets, mede bytes/unidades/tempo
                 compara com bytes do exp 16 (referencia)
```

Trocar sintaxe = instanciar outra subclasse de `Syntax` no
`run.py`. Algoritmo (`online.py`) **não muda**.

## Resultado observado

Roundtrip **21/21 OK**.

### Paridade com exp 16

| dataset | bytes exp 20 | bytes exp 16 | diff |
|---|---:|---:|---:|
| todos os 21 datasets | (igual) | (igual) | **0** |

`VerboseSyntax` reproduz exp 16 byte-a-byte em todos os
casos.

### Diff vs exp 19 (que diverge do exp 16 em 5 casos)

| dataset | exp 20 igual exp 19? | nota |
|---|---|---|
| 16 datasets | sim | mesma escolha do exp 16 |
| codigos-N0050 | não | exp 19 fez escolha diferente |
| codigos-N0200 | não | idem |
| codigos-N1000 | não | idem |
| ips | não | idem |
| ips-N1000 | não | idem |

Confirma a leitura: exp 20 (verbose, mesmo algoritmo do exp 16)
reproduz exp 16 exatamente; exp 19 (algoritmo par A+B) diverge
nesses 5 casos como já documentado.

### Tempo

Sem diferença significativa vs exp 16/18. A modularização
adiciona indireções de chamada de método (chamada virtual em
classe abstrata) que não impactam o tempo de processar.

| caso | t exp 20 | t exp 18 |
|---|---:|---:|
| urls-N1000 | 3607 ms | 3829 ms |
| iso-N1000 | 3133 ms | 3431 ms |
| ips-N1000 | 1586 ms | 1595 ms |
| codigos-N1000 | 1342 ms | 1469 ms |

## Como criar uma nova sintaxe

```python
# syntax_compact_v1.py (hipotetico)
from syntax_base import Syntax

class CompactV1Syntax(Syntax):
    name = "compact_v1"

    def encode(self, linhas, unicas, tokens, header):
        # ...gerar texto na nova sintaxe...
        return tcf

    def decode(self, tcf_text):
        # ...parsear de volta...
        return linhas
```

E em `run.py`:

```python
from syntax_compact_v1 import CompactV1Syntax
sintaxe = CompactV1Syntax()
```

Nada mais muda. O algoritmo continua produzindo os mesmos
tokens; a sintaxe é responsável apenas por serializar e
desserializar.

## Limitações

- **Modularização não muda comportamento**. Não traz ganho de
  bytes, unidades nem tempo. É infraestrutura.
- **A interface `Syntax` é simples por design** — apenas dois
  métodos. Não prevê sintaxes que precisem de cooperação
  bidirecional (encoder consulta algoritmo durante encoding, por
  exemplo). Se sintaxe futura exigir isso, a interface vai
  precisar evoluir.
- **Não testa nenhuma sintaxe alternativa** ainda. Próximo
  experimento será o primeiro candidato a sintaxe compacta.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-20-marcadores-modulares
python run.py
```

21 datasets × sintaxe `verbose`. TCFs salvos em
`encoded/verbose/`. Saída esperada: `21/21 OK` + `diff = 0` em
todas as linhas + mensagem "VerboseSyntax reproduz exp 16".

## Próximo experimento natural

Implementar uma sintaxe compacta como segunda classe `Syntax`.
Candidatos discutidos na nota
[`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md):

- **Direção 1 — explícita compacta**: substituir `noN`, `[0:K]`,
  `[-K:]`, `+` etc. por símbolos de 1 char
- **Direção 2 — inferida pela ordem**: id implícito por linha,
  prefix/sufix detectado por posição

Cada direção vira uma classe `Syntax` separada (`CompactExplicitSyntax`,
`CompactInferredSyntax`). Compara-se bytes reais entre verbose,
compact_v1, compact_v2, etc. em todos os 21 datasets, sem
qualquer mudança no algoritmo.

Quando uma sintaxe se mostrar a melhor, considerar (em
experimento separado) a **fusão**: embutir o encoder dentro do
construtor do body para evitar passagem intermediária de tokens.
Por enquanto, **manter separado** — clareza > performance.
