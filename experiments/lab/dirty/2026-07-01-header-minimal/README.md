# Header-minimal — quanto o cabeçalho pode ser economizado? [probatório]

**Iniciado** 2026-07-01 (stub `medir.py`), **fechado** 2026-07-05. Foco **byte-level / payload pequeno**
([[project-byte-level-compression-focus]]). Read-only, **não toca `src/tcf`**. `python run.py` regenera `artifacts/`.

> Nome só-data (pré-convenção dia+HHMM). Lab **existente continuado**, não fragmentado.

## Pergunta

Num **registro mínimo** (1 linha, poucas colunas), o header (shebang + meta) é uma fração grande do
payload. Quanto dá pra economizar, e **quando isso importa**?

## Fluxo

```
registro mínimo (cpf+nome) → medir header vs body por LEVER (nomeado / drop_names / nature) →
   + deduções HIPOTÉTICAS (M implícito, header derivável O-FMT-14) → break-even (header vs N registros)
```

## Arquivos

- [`run.py`](run.py) — driver: piso do header (levers reais + hipotéticas) + break-even. Conserta o
  stub (contabilidade line-based do header) e a lever `nature` (SPEC_CPF, não a string "cpf").
- [`medir.py`](medir.py) — probe inicial (2026-07-01), **superado** pelo `run.py` (contava só o shebang).
- [`artifacts/`](artifacts/) — `01-piso-header.txt` · `02-breakeven.txt` · `00-resumo.txt`.
- [`result.md`](result.md) — conclusão + caminho de protótipo.

## Achados (medido — `artifacts/`)

**Piso (1 registro, 24 chars de dados)**: header `#TCF.7 M\n!14=cpf,!nome\n` = **23B** (default) →
`#TCF.8M!14,!\n` = **13B** (`drop_names`, magic+meta fundidos, sem nomes). Deduções hipotéticas:
implícito-M **12B** (deduz multi de ≥2 colunas) → só-magic **6B** (schema pré-acordado, O-FMT-14) →
**0B** (contrato total, header fora de banda). O **piso teórico é o body** (24B).

**Orthogonalidade das levers** (eco da teoria de cardinalidade): `drop_names` corta o **header** (nomes);
`nature` corta o **body** (cpf 14→5B via pre-tx). São **levers ortogonais** — a menor combinação real é
`drop_names + nature` = **31B** (de 47B).

**Break-even**: o header é ~fixo (13–14B); o body cresce → o header vira ruído. N=1 → **39%**; N=5 → 9.8%;
N=20 → 4.6%; N=100 → **1.3%**. O ganho de encolher o header concentra-se em **payload minúsculo (1-poucos
registros)** — exatamente o foco byte-level.

## Estado (era / foi / é / será)

- **É**: piso medido + break-even + as deduções mapeadas. Conclusão: o header **self-describing já está
  perto do ótimo** (13B/2-col anônimo); o frontier real é o **header DERIVÁVEL** (O-FMT-14), e só pesa em
  payload minúsculo.
- **Foi**: stub `medir.py` (contabilidade quebrada, nature quebrada).
- **Será** (protótipo, exige aprovação — toca formato/src): ver [result.md](result.md).

Convenções: [dirty-lab-convencoes](../notas/dirty-lab-convencoes.md).
