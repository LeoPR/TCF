# Onde um spec encaixa na rota tipada — investigação de código

**2026-08-13/14** · 4 lentes sobre `src/tcf` com verificação adversarial (8 agentes, 0 erros),
para responder a pergunta que o lab da matriz deixou aberta: *se "entra int, spec int, devolve
int" não existe hoje, **onde** ele entraria?* Os achados abaixo foram **re-verificados à mão**.

---

## Correção ao que eu havia afirmado

Eu disse que a rota tipada *"custa 1 byte e não entrega nada"*. **Está errado.** A tag
seleciona a **família de cast**, e o mesmo corpo `\1` devolve:

| wire | volta | tipo |
|---|---|---|
| `#TCF.8n` | `[1]` | `int` |
| `#TCF.8b` | `[False]` | `bool` |
| `#TCF.8s` / `#TCF.8` | `['1']` | `str` |

O byte **é** o produto — sem ele, `[1,2,3]` voltaria `["1","2","3"]`. O enunciado correto é
mais estreito: a rota entrega o **cast**, não entrega **otimização de compressão**.

E há uma assimetria que importa para o desenho: dentro da família `n` (união `int|float`, o
`number` do JSON) o tipo concreto é re-derivado da **grafia**, por elemento —
`encode([1, 2.0])` volta `['int','float']`. Já na família `b`, a grafia é índice de slot
congelado e a **tag é o único portador**. Um spec de int vive na primeira situação: ele
mexeria justamente na grafia de onde o tipo é re-derivado.

## O encaixe, concreto

| ponto | arquivo | o que entra |
|---|---|---|
| encode | `encoder.py:539` | o spec depois do `render` (que para `n` é a builtin `str`) |
| FLOOR | `encoder.py:549-600` | um `candidatos.append` — o spec compete, como toda nature |
| decode | `decoder.py:410-411` | o spec antes do `_cast_tipo` |
| header | slot do índice 7 | `#TCF.8n [nome]:id` — **verificado livre** |

O namespace do índice 7 hoje: `''`, `!`/`!!` (polaridade), `B` (bN tipado), `1`, `2`, `4`, `8`
(densos/lazy). O par `n`+`espaço`+`:id` não colide.

## O `.8H` NÃO é "apagar um check"

Isto é o achado que evita um erro caro. A gramática do meta é **mutuamente exclusiva** entre
tag de tipo e id de nature:

- encode (`hierarchical.py:602-605`): emite `f"{csz}:{nat_id}"` quando há nature — **sem
  stype** — contra `f"{csz}{stype}"` quando não há.
- decode (`hierarchical.py:806-813`): lê o id primeiro e, havendo id, empilha o nó com
  **`stype` hardcoded `"s"`**; a função que lê `n`/`b` só roda no `else`.

Consequência: **apagar o check de `:476-479` faria uma coluna `int` voltar `str` sem erro** —
exatamente a falha que o owner está reclamando. No `.8H`, spec + tipo exige **mudança de
gramática do meta**, não remoção de guarda. É a mesma classe do `T-META-NAO-DECLARA-MODO`.

## Dois buracos de "ignora calado" (verificados à mão)

O portão principal é fail-loud: `encode([1,2,3], nature=SPEC)` → `ValueError`. Mas ao lado
dele:

1. **`nature_per_col=` na rota tipada é aceito e descartado calado.** Medido: `encode([1,2,3])`
   e `encode([1,2,3], nature_per_col={'x':SPEC})` produzem wire **byte-idêntico**. Causa: o
   rejeitador em `encoder.py:349` está condicionado a `_lista_flat`, que é falso para lista
   tipada. Mesma classe no multi-col: `nature_per_col={'ZZZ':SPEC}` com coluna inexistente é
   descartado calado (`encoder.py:625-633`, `if name in data`).
2. **`decode(wire_tipado, nature=SPEC)` é ignorado calado.** Medido:
   `decode(encode([738886,738887]), nature=SPEC_DATA_ISO)` devolve os inteiros. Causa:
   `decoder.py:175-176` roteia para `_decode_typed` antes de qualquer tratamento de nature, e
   `_decode_typed` nem recebe o parâmetro. (No disc `''` o ignorar é **documentado** e
   justificado pelo FLOOR; aqui não há justificativa registrada.)

Nenhum dos dois corrompe dado — o wire está certo. O que quebra é a expectativa: o usuário
pede uma coisa e recebe outra sem aviso, e o projeto invoca "nunca ignorar calado" como regra.

## Limitação documentável (não é defeito)

Subclasses de tipos nativos atravessam e voltam como o **tipo-base**, caladas:
`[Cor.VERM, Cor.AZUL]` (`IntEnum`) volta `[1, 2]` (`int`). E `==` **não detecta** — só uma
comparação por tipo pega. É esperado para um formato tabular textual (JSON também não
preserva `IntEnum`), mas vale estar escrito: quem usa `Enum` recebe `int` de volta.

## O que isso muda na fila

Nada de ordem — número segue sendo o próximo tipo, e M/H depois. O que muda é o **desenho**:

- o encaixe do spec na rota tipada single-col é pequeno e tem lugar definido;
- o `.8H` exige gramática nova de meta, e isso se soma ao `T-META-NAO-DECLARA-MODO`;
- os dois "ignora calado" são baratos de fechar e independem do spec de int.
