# 2026-08-17-1700 — o grupo como COMBINADOR do `.8H`

## A observação

> *"o group fica muito mais limpo e de certa forma dá pra emprestar a lógica da hierarquia,
> pensando que ele só vai tratar um pouco diferente na hora de combinar."* — owner, 2026-08-17

**A gramática confirma.** O `.8H` **já é** "N colunas físicas + uma regra de recombinar", e o
meta declara o combinador em cada campo:

| marcador | como combina | resultado |
|---|---|---|
| `{` | aninhando | `{"a": {"b": v}}` |
| `#:[` | por contagem | `{"a": [v, v]}` |
| `?:` | com máscara | presente / ausente / null |
| `:tag` | folha escalar tipada | `30` (int), `true` (bool) |
| **`\|…\|`** | **concatenando por template** | **`parte0 + c0 + parte1 + c1 + …`** |

O grupo não é um mecanismo novo — é **a quinta linha da mesma tabela**.

## O fio que isso amarra

O lab [`0400`](../2026-08-17-0400-o-candidato-unico-do-H/) mediu: o `.8H` perde **+23,0%**
para o `.8M`, e **100% do gap** é o **candidato único** — a folha chama `_encode_col` e não
tem `raw`/`dict`/`split`. Minha proposta na época foi *"abrir um slot de modo no meta da
folha"*.

A ideia do owner ataca por **outra rota**: se o grupo é um **combinador**, a folha estruturada
vira N colunas irmãs e cada uma passa pelo pipeline normal — **sem slot de modo, sem `%`, sem
sub-wire**.

Confirmado que a folha não alcança o split hoje:

```
.8H : '#TCF.8Hitem{sku:70,preco'   ← sem marcador de modo na folha
.8M : '#TCF.8M%preco'  modo='%'    ← a MESMA coluna, com split, 132 B
```

## Resultado — atribuição decomposta

**Os dois efeitos são ortogonais e foram medidos separados** (lição do D6: sem controle, o
ganho todo iria para a ideia mais recente):

| caso | n | **A: candidatos** (`raw`/`dict`) | **B: GRUPO** (isolado) | total vs `.8H` |
|---|--:|--:|--:|--:|
| h1-folha-decimal | 24 | −8,6% | **−17,0%** | −24,1% |
| h2-folha-data | 24 | −3,3% | **−21,8%** | −24,4% |
| h3-duas-folhas | 24 | −3,0% | **−25,4%** | −27,7% |
| h4-cep-real (Receita) | 3 998 | −14,0% | **−11,7%** | −24,1% |

- **A** = o que `raw`/`dict` dariam nas folhas — o achado do lab 0400, pela rota do slot de modo.
- **B** = o que o **combinador de grupo** acrescenta **por cima de A**. É o efeito da ideia do owner.

**B é maior que A em 3 dos 4 casos**, e no CEP real os dois são comparáveis. Não se substituem:
**A abre candidatos; B muda a estrutura da folha.**

Verificação da atribuição de **A** (o gap `.8H real` → `mock sem grupo` é mesmo o candidato?):

```
h1  corpos só-tcf    207  →  com raw/dict    180   (−13,0%)
h4  corpos só-tcf 46 751  →  com raw/dict 40 179   (−14,1%)
```

Fecha por coluna — é o candidato, como o lab 0400 dizia.

## O meta, lado a lado

```
.8H real   : #TCF.8Hv{preco:137,quando
com grupo  : #TCF.8Hv{preco||.||:@34,@27;v{quando||-|-||:a,1e,@
                     └─ template ["", ".", ""]      └─ template ["", "-", "-", ""]
                        2 colunas irmãs, modos @ @     3 colunas irmãs
```

## Ponto a ponto da crítica

**"Muito mais limpo"** — o decoder do mock reusa `_decode_raw_body`, `_decode_v2b` e o
`decode` público. **Nenhuma primitiva nova.** A única lógica própria é a linha do combinador:

```python
v = "".join(partes[k] + cols[k][r] for k in range(len(cols))) + partes[-1]
```

Uma linha, ao lado das que já existem para `{` (aninhar) e `#:[` (contar).

**"Só trata um pouco diferente na hora de combinar"** — literalmente. O shredding, o plano de
fatias, a escolha de candidato por coluna e o walk de reconstrução são **os mesmos**. O que
muda é qual operador fecha o valor.

## O que este mock NÃO é

- **Não é weld.** `src/tcf` intocado; a grafia `|…|` e o separador `;` são ilustrativos
  (marcadores abstratos, congelados por economia — a escolha de char é reversível).
- **Cobre uma classe reduzida**: objetos aninhados de folhas string. **Não** exercita máscara
  (`?:`), contagem (`#:[`), array-em-array, nem tipos. A composição grupo×máscara e
  grupo×array **não foi testada** — e é onde eu esperaria a primeira dificuldade real
  (um grupo dentro de um array precisa que os N campos compartilhem a contagem).
- **Não mede CPU**, e o `.8H` real tem invariantes (ordem DFS, omit-closes) que o mock
  simplifica.
- **O gate do grupo aqui é o do split** (template uniforme, ≥2 campos, variação). Não testei
  o gate por spec/dica, que é a H-13-04.

## Evidência

12 wires (por caso: `.8H-real`, `mock-sem-grupo`, `mock-com-grupo`) + 4 roundtrips.
**RT validado nos três formatos** de cada caso, com portão de completude.

## Conexões

- Origem: crítica do owner (verbatim no `run.py`)
- Lab do gap que isto amarra: [`0400`](../2026-08-17-0400-o-candidato-unico-do-H/)
- Mock anterior (grupo no `.8M`): [`1600`](../2026-08-17-1600-split-como-grupo-no-meta/)
- Didático do split: [`1500`](../2026-08-17-1500-split-didatico/)
- Registro: [roadmap-hipoteses Pacote 13](../../../notas/2026-05/roadmap-hipoteses.md)
