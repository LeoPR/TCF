# Resultado — estudo P4a (array-em-array via count recursivo)

**[probatório]** `proto.py` (extrai a ideia; não copia o core) + `study.py`. Números:
[outputs/00-resultado.txt](outputs/00-resultado.txt); roundtrips diffáveis em `outputs/01-*-rt.json`.

## Confirmado

1. **Count recursivo cobre o gate inteiro do owner** (checkpoint 2026-07-16): básico, matriz,
   profundidade 3, inners vazios, `[]`≠`[[]]`≠`[[1]]`, arrays de arrays de OBJETOS, null entre
   arrays, null no inner, compose total (P2+P3b+P4a), strings/bool aninhados, campo no meio —
   **RT 12/12**; fuzz de profundidade (1–4, com nulls e tipos) **4000/4000**.
2. **Null estrutural entre arrays = P3b∘P4a** (decisão que o parecer pediu explícita): a element-mask
   do nível externo cobre `[[1],null,[2]]` (`m#?[...]`); a do interno cobre `[[1,null,2]]`
   (`m#[#?[]...]`). **Sem gramática nova, não é P5** — P5 continua sendo tipo-MISTO.
3. **Invariantes de frame por nível**: count truncado/excedente e folha faltando/sobrando →
   fail-loud (exaustão por coluna, o mesmo mecanismo do weld) — nunca silencioso.
4. **Separabilidade (Ciclo 4)**: counts por nível são colunas próprias — a ESTRUTURA (quantos, onde
   reinicia) é legível sem materializar folhas; cada nível é um stream independente (O(1)/view).

## Gramática (a inspecionar antes do weld)

`campo#?[...]` por nível: cada `#` = um nível de array; `?` após o `#` = element-mask daquele nível;
o conteúdo de `[...]` é a spec do ELEMENTO (recursiva: outro `#`, um `{campos}`, ou `[]<tag>` escalar).
No weld os sizes entram como hoje: `m#:c0?:e0[#:c1?:e1[]:asize n`.

## Fronteira (declarada)

- **P5 union** (tipos mistos no mesmo array) segue fail-loud — fora do P4a.
- **P4b raiz generalizada** — ato separado (contrato público), depois do P4a (ordem do owner).
- Custo por profundidade: cada nível = 1 coluna de counts (+1 emask se houver null). No proto o
  overhead é linear na profundidade; o byte-custo REAL (com L1) se mede no weld.

## Próximo (ordem do checkpoint do owner)

1. **Inspeção do owner desta gramática** (o item 6 do seu ritual de retomada).
2. Aprovação → weld no core: spec de ELEMENTO recursiva no nó de array (a mudança estrutural maior
   até agora — `arr_scalars`/`arr_objects` viram casos de `elemento ∈ {scalar,object,array}`),
   parser por nível, gate padrão (didático→realista→massa + suíte + flat + auditoria adversarial).

`confianca: Média-Alta` p/ o design (RT 12/12 + fuzz 4000 + adversarial; falta o gate do core).
Sintético declarado (didático construído pro gate; fuzz seedado).
