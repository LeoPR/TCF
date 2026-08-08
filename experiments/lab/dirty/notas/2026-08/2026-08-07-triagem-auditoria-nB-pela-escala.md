# Triagem da auditoria do weld `nB` pela escala E0–E5

**2026-08-07 · registro, não fila de trabalho**

Auditoria adversarial do weld `T-BN-TIPADO`: 15 agentes, 5 lentes de caça + verificação
individual com repro executado. Resultado bruto: **9 achados, 9 "confirmados"**.

Aplicando a [escala de verificação](2026-08-07-escala-de-verificacao-e-fechamento-do-bn.md)
que o owner acabou de estabelecer, o quadro muda bastante.

---

## Primeiro: 9 não são 9

Deduplicando por causa raiz, são **6 achados distintos**:

- `[3]` ≡ `[9]` — sufixo de polaridade espúrio
- `[5]` ≡ `[8]` — `_le_grafia(None)` → `AttributeError`
- `[6]` ≡ `[7]` — `w` não checado como mínimo

A taxa "9/9 confirmado" é artefato do desenho: cada verificador recebeu **um** achado e
julgou só ele, sem ver os outros. Sem passo de dedup, achado repetido conta várias vezes.
É a segunda vez que o resumo do orquestrador precisa ser reconferido à mão — a primeira foi
o oposto (marcou 18 achados como "descartados" sem que nenhum tivesse sido refutado).
**Ler o journal, nunca o sumário.**

## Segundo, e é o que importa: **zero achados de E1/E2**

| achado | wire veio de onde? |
|---|---|
| todos os 9 | **escrito ou mutado à mão** |

Nenhum defeito alcançável pelo fluxo `encode→decode`. O caminho feliz do weld está limpo, e
isso é consistente com a checagem que eu já tinha feito: simetria conferida em 26 valores
exóticos, 0 falhas.

O alerta do owner previu exatamente isto: **15 agentes, 5 lentes, ~2,2 milhões de tokens, e
o que saiu foi inteiramente E4/E5.** Má alocação de orçamento de auditoria, e foi minha.

---

## Os 6 distintos, classificados

| # | achado | nível | de quem é |
|---|---|---|---|
| **1** | `.8H` (`_dec_scalar`, ramo `n`) aceita grafia numérica não-canônica (`1e3`, `1.50`, `0e0`, `-0`, `1E3`, `1e+3`, `10.0e2`) — e **meu comentário em `decoder.py` diz "as DUAS rotas numéricas" quando são TRÊS** | E4 · **o comentário é doc errado** | pré-existente · **comentário meu** |
| **2** | `#TCF.8nB…` + sufixo de polaridade: a pré-passe despolariza o corpo **antes** da delegação; 20 de 40 valores trocam em silêncio | E5 | interação nova do weld |
| **3** | sufixo de polaridade espúrio aceito calado — 50 wires distintos → mesmo valor. Afeta `#TCF.8B` também | E4/E5 | pré-existente |
| **4** | erros do `#TCF.8nB` saem assinados `#TCF.8B` — o rótulo aponta pro irmão de string | **E3** | **meu weld** |
| **5** | domínio com `0` cru vaza `AttributeError` em vez de `ValueError`; o irmão `#TCF.8bB` **já trata** e diz o que é | **E3** (o fix) · E5 (o gatilho) | pré-existente |
| **6** | `w` do cabeçalho não é checado como **mínimo** (`_largura(len(dom))`): 8 grafias por valor | E4 | pré-existente |

### O que é meu, e é barato

- **`[1]` o comentário.** `_cast_tipo` tem 2 chamadores — isso é verdade — mas o `.8H` tem
  rota numérica própria (`_dec_scalar`, via `json.loads`). Escrever "o ponto único por onde
  passam as DUAS rotas numéricas" instrui o próximo mantenedor a acreditar que a família
  está fechada. **Doc errado é defeito**, e o custo de corrigir é uma frase.
- **`[4]` o rótulo.** A delegação passa `"B"` ao `decode_bn`, então o erro de um wire `nB`
  sai assinado `#TCF.8B` — que é o irmão de **string**, com contrato de retorno diferente.
  Diagnóstico ruim, E3, custo baixo.

### O que é pré-existente e E4/E5

`[2]` `[3]` `[5]` `[6]` — nenhum alcançável por `encode→decode`. Ficam **registrados**.

Vale notar que `[3]` e `[6]` são da mesma família dos bugs de cabeçalho já corrigidos
(canonicidade por re-emissão): o invariante existe, aplicado em alguns campos e não em
outros. E `[5]` é assimetria entre irmãos — o `bB` trata, o `bN` não. Essa é a classe que
historicamente custou caro, mas **aqui só se manifesta com wire à mão**.

---

## O que fica decidido

1. **Nada vira código sem o owner mandar.** Achado E5 é registro.
2. Os dois itens do meu weld (`[1]` comentário, `[4]` rótulo) são E3/doc, custo baixo, e
   estão **propostos, não feitos**.
3. `[2]` merece nota à parte no `.9`: a promessa do meu comentário — *"herdar de graça
   TODAS as checagens do bN"* — **não é verdade** quando existe uma camada acima que
   reescreve o corpo. A polaridade é pré-passe; o `decode_bn` valida o corpo que **recebe**,
   e esse corpo já é outro. Isso não é bug alcançável, mas é uma **afirmação errada minha**
   sobre a arquitetura, e afirmação errada envelhece pior que código.
4. Auditoria futura: **gastar o orçamento em E1/E2** (round-trip, assimetria encode/decode),
   não em lentes de wire adulterado. Esta rodada é a evidência do custo de não fazer isso.

## Ligações

[escala E0–E5](2026-08-07-escala-de-verificacao-e-fechamento-do-bn.md) ·
[inventário de existência](2026-08-07-fechamento-bn-inventario-de-existencia.md) ·
[ADR-0036 §weld](../../../../docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md) ·
[EXP-016](../../clean/EXP-016-bn-familia-bits/)
