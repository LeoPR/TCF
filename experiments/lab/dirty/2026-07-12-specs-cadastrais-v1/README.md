---
title: Specs cadastrais v1 — triagem para .8/.9
type: experiment
status: open
created: 2026-07-12
---

# Specs cadastrais v1

Laboratório de triagem para campos comuns em formulários: data, datetime,
CEP, RG estadual, telefone e códigos decimais fixos. O objetivo é decidir
escopo, não criar specs canônicos.

## Regras

- Não altera `src/tcf/` nem o `SPEC_REGISTRY`.
- Todo candidato é comparado com a codificação comum pelo blob serializado completo.
- Todo resultado exige round-trip com o filtro declarado separadamente.
- Hubs locais são usados apenas como amostras; RG/CEP/CNH não têm fonte real
  neste repositório.
- `BASE94` é o nome histórico do alfabeto, que hoje possui 80 caracteres
  seguros após remover símbolos reservados pela gramática TCF.

## Execução

```powershell
.\.venv\Scripts\python.exe experiments/lab/dirty/2026-07-12-specs-cadastrais-v1/run.py
```

## Resultado

Consulte [`result.md`](result.md). A recomendação atual é manter CPF/CNPJ/IP
no `.8`, deixar CEP/RG/CNH/RENAVAM/PIS/título/telefone e specs de alfabeto fixo
para `.9`, e não introduzir base96 no wire-format. `DateSpec` ISO continua uma
hipótese condicional: só pode preemptar F6 com aprovação própria, validação de
calendário e dois gates reais.
