# Checkpoint 2026-07-15 — revisão de null pós-P1; decisão do owner pendente

**[pausa explícita]** P1 está fechado e sincronizado. Esta pausa ocorre ANTES de qualquer estudo ou
mudança de código para null, para o owner decidir conscientemente o escopo campo × array.

> **Pausa histórica, retomada concluída em 2026-07-16.** P3a, P3b e P2 foram welded depois deste
> registro. Estado e próxima retomada: [`2026-07-16-revisao-p2-p4.md`](2026-07-16-revisao-p2-p4.md).

## Estado verificado nesta pausa

- HEAD `69db6bc`, `main` limpa e sincronizada com `origin/main`.
- P1 presença/ragged welded: `nome?:msize`, `.`=presente, `-`=ausente, `0` reservado para null.
- Testes focados (`test_hierarchical_rt.py` + `test_core_rt.py`): **129 passed, 1 xfailed**.
- Suíte completa: **685 passed, 2 skipped, 1 xfailed**.
- `xfail`: `BUG-SEQRLE-RANGE-EMPTY-B`, bug pré-existente do L1, separado do P1.
- Nenhum código foi alterado durante a revisão; somente rastreamento documental nesta etapa.

## Achado controlador

Null não é um único incremento no modelo colunar atual:

1. **P3a — null em campo de objeto**: `{x:null}`. A definition mask do campo já tem o estado `0`.
   Ao ler `0`, o decoder materializa `x=None` e não consome corpo nem descendentes. Isso pode cobrir
   campos normalmente escalares, objetos ou arrays, além de coluna all-null, sem nova gramática.
2. **P3b — null em elemento de array**: `{"xs":["a",null,"b"]}` ou array de objetos com elemento
   null. A máscara P1 está alinhada às instâncias do CAMPO, não aos ELEMENTOS. É preciso um stream de
   definição na cardinalidade dos elementos; aceitar `0` no campo não resolve suas posições.
3. **Null na raiz**: fora do contrato atual (`encode_hierarchical` espera `list[dict]`). Decidir junto
   de P4/N-raízes, não embutir silenciosamente em P3a.

## Opinião técnica registrada

Null é o próximo trabalho com melhor relação entre frequência semântica, impacto e custo. Não foi
encontrada outra feature de grande ROI pronta que deva passar à frente. Ordem recomendada:

1. Owner decide se autoriza apenas P3a ou P3a+P3b como sequência.
2. Estudar P3a em lab novo, com código zerado a partir do contrato, sem copiar o proto dirty.
3. Gate P3a: ausente/null/`"null"`/`""`; campo escalar/objeto/array; all-null; null em campo opcional;
   máscara/frame corrompidos; wire sem null byte-idêntico; suíte flat e real-world verdes.
4. Weld P3a somente após revisão e aprovação explícita de `src/tcf`.
5. Estudar P3b separadamente, incluindo arrays escalares e de objetos, posições inicial/meio/final,
   todos-null, vazio, arrays aninhados e alinhamento count×mask×dense.
6. Depois: P2 tipos → P4 rep-level/N-raízes → contratos de borda → P5/decisão de fronteira.

## Delimitações para não misturar assuntos

- NaN, `+Infinity` e `-Infinity` ficam FORA de P3: não são JSON RFC 8259; dependem de P2/tipos.
- O bug seq-RLE `..` permanece R0 registrado e deve ser corrigido antes do release, mas não bloqueia
  pensar ou estudar P3 sob a regra atual de não priorizar borda estreita.
- Não declarar “família null fechada” depois de P3a.
- Não declarar “qualquer JSON” enquanto null-em-array, raiz/rep-level ou array polimórfico estiverem fora.

## Ritual de reentrada

1. Ler o bloco vigente no topo de `STATUS.md`.
2. Ler este checkpoint.
3. Ler `tickets/T-CODE-TCF8H-JSON-PARITY.md` (fonte da ordem e dos gates).
4. Owner registra a decisão: **P3a apenas**, **P3a→P3b**, ou **adiar null**.
5. Só então abrir lab `YYYY-MM-DD-HHMM-p3a-null-campo-estudo/`; não tocar `src/tcf` antes da aprovação.

## Fontes

- `src/tcf/hierarchical.py`: `_field_node`, `_emit_row`, `_read_object`.
- `tickets/T-CODE-TCF8H-JSON-PARITY.md`.
- `tickets/BUG-SEQRLE-RANGE-EMPTY-B.md`.
- `experiments/lab/dirty/2026-07-06-2246-tcf8h-fronteira-link-posicional/mask_codec.py`.
- Diário `experiments/lab/dirty/notas/diario/2026-07-15.md`.