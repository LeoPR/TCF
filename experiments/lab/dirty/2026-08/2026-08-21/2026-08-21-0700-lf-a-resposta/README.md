# 2026-08-21-0700 — o `
` final: a resposta, em duas perguntas

> *"foco, bastando não ter ambiguidade, e não necessidade, focamos nisso, se alguma utilidade
> ortogonal, como arquivo, transporte, ótimo, senão não vale discutir."*

## A resposta

| pergunta | resposta |
|---|---|
| **tem ambiguidade?** | Com o terminador, **não**. Sem ele, **sim** |
| **tem necessidade?** | **SIM** |

Pelo seu critério, o `
` final **não se qualifica para remoção**: ele tem necessidade.
Fim da discussão — sem precisar invocar arquivo nem transporte.

## O par que decide

```
[]     ->  '#TCF.8
'        decode -> []
['']   ->  '#TCF.8

'      decode -> ['']
                        ↑ diferem em exatamente um LF
```

**Coluna com zero valores** contra **coluna com um valor vazio**. O LF terminador é o que as
separa. Se o LF fosse **separador** (n valores → n−1 LFs), as duas produziriam corpo vazio:

```
[]     ->  ''      ['']   ->  ''      /  o MESMO corpo — ambíguo
```

## O tamanho exato da necessidade

Ele carrega **1 bit, e só no caso de borda**: corpo vazio × um valor vazio. Em toda outra
posição é redundante — mas a convenção precisa ser **uniforme**, senão o decoder teria de
carregar um caso especial só para o corpo vazio. É pouco, e é suficiente.

## Isto REVOGA a conclusão do lab 0500

O [`0500`](../2026-08-21-0500-lf-final-tem-funcao/) concluiu *"o LF final é redundante, 100%
recuperável (55/55)"*. **Errado, e o erro foi de corpus:**

- testei **`drop + readd`** — uma operação que **já sabe** que o LF existia. Isso mede
  *recuperabilidade*, não *necessidade*;
- e o corpus omitia justamente `[]`, o único caso em que a diferença aparece.

Medir a propriedade errada num corpus que não contém o caso de borda dá 55/55 e nenhuma
informação.

## Evidência

[`run.py`](run.py) com asserts (`encode([]) != encode([''])` e `LF.join([]) == LF.join([''])`).
5 arquivos em [`inputs/`](inputs/)+[`outputs/`](outputs/) com roundtrip.

## Conexões

- Revoga: [`0500`](../2026-08-21-0500-lf-final-tem-funcao/) · confirma (pelo motivo certo):
  [`0400`](../2026-08-21-0400-lf-final-do-wire/)
