# A polaridade come o fim do nome da coluna — RT quebrado calado no `.8M` e no `.8H`

> Achado do mapeamento de M/H (2026-08-16). **É defeito de correção, não medição de bytes.**

```python
>>> from tcf import encode, decode
>>> d = {"obs.": ["v0", "v1", "v2", "v3", "v4"]}
>>> decode(encode(d))
{'obs': [...]}          # a chave perdeu o ponto. Sem warning. Sem exceção.
```

Com pontuação **dobrada** (`"obs.."`) além da chave **os valores também corrompem**.

## O mecanismo, verificado

A polaridade é **camada de borda, a primeira coisa do decode** (`decoder.py:154-161`):

```python
_tag, _sufixo = _separa_sufixo_polaridade(line1[6:])
```

Ela roda sobre `line1[6:]` — que no `.8M` é `M<meta>`. E no fim do meta está o **nome da última
coluna**, porque a forma `min_header` omite o size da última (`multi/core.py:413-414`). A
polaridade não sabe disso: vê `Mobs.`, separa `('Mobs', '.')`, e o parser recebe um meta onde a
coluna se chama `obs`.

## Por que passou despercebido

O gatilho é o **modo** que vence no `min()` por coluna, e o modo põe (ou não) um prefixo:

| n | header | RT |
|---:|---|---|
| 3 | `#TCF.8M!obs.` (modo raw, prefixo `!`) | ok |
| ≥5 | `#TCF.8Mobs.` (modo tcf, prefixo vazio) | **quebra** |

Com poucos valores o `!` protege. **Um teste de RT com coluna pequena não vê nada** — e é assim
que a suíte não pegou.

## O que foi medido

| | resultado |
|---|---|
| `.8M`, 1 coluna, 64 nomes | **48/64 RT falso (75,0%)** — 24 perdem só a chave, 24 corrompem chave **e** valores |
| `.8H`, 1 campo, 64 nomes | **38/64 RT falso (59,4%)** — mesmo mecanismo, **não é controle** |
| warnings em todo o sweep | **0** — perda 100% silenciosa |
| **contra-prova: 2 colunas** | **64/64 RT ok (100%)** — isola a causa na coluna única |

Escapam 16 nomes: os que terminam em `* , : = \ ^ | ~` (simples ou dobrados) — exatamente o
alfabeto que o `_esc_name` já escapa (`multi/core.py:65`) ou que a polaridade não usa.

## Como rodar

```
python run.py     # sai 0 se REPRODUZIR o defeito (lab de defeito, não de ganho)
```

Sem `Z:`, determinístico. `src/tcf` intocado — este lab **reproduz e delimita, não conserta**.

## Vínculo

`T-UM-CAMINHO-SO` (a polaridade foi soldada como camada de borda e não sabe da gramática do
`.8M`) · ADR-0029 (discriminadores) · `T-GRAFIA-CHECKLIST` (a assimetria escapar/desescapar já
reincidiu 5×; esta é a 6ª, e a primeira **entre camadas** em vez de dentro de uma) ·
`T-NATURE-IGNORADA-CALADA` (mesma família: silencioso)
