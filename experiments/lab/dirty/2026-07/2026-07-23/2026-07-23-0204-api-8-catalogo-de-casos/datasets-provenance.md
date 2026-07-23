# Proveniência dos dados — catálogo de casos da API `.8`

**Origem**: 100% **sintético e determinístico**, gerado inline no `run.py` (sem seed externo — os
valores são literais fixos ou fórmulas fechadas). Nenhum dado real, nenhum download.

**Viés declarado**: os dados são *ilustrativos* — construídos pra exibir CADA comportamento de
saída (header, marcador, tipo, RLE, FLOOR), não pra medir compressão ou representar distribuição
real. Volumes minúsculos (2–6 linhas, 50 no caso de compressão) — é catálogo de comportamento, não
benchmark. Para números de performance/compressão ver o processo `scripts/bench_perf/`.

**Placeholders sensíveis (conformidade)**:
- **CPF**: `111.111.111-11`, `222.222.222-22`, `333.333.333-33` — placeholders de **dígitos
  repetidos** mod-11-válidos (aceitos pelo `SPEC_CPF`), **nunca** CPFs de pessoa real. Mesma
  convenção da suíte (`tests/test_hierarchical_rt.py`).
- **CNPJ**: `11.222.333/0001-81`, `11.444.777/0001-61` — synthetic DV-válidos, **não** vinculados a
  entidade real (o gate de CNPJ real da Receita é outro — ver `project_cpf_cnpj_natures_real_world_gate`).
- **IP**: `10.x.x.x` (faixa privada RFC 1918), synthetic.
- **Nomes/cidades/telefones**: fictícios (`Ana`, `Bruno`, `SP`, `11 9999-0001`).

**Reprodutibilidade**: `python run.py` regenera byte-a-byte (determinístico). O RT é provado em
arquivo (`outputs/*.roundtrip.json` diffável contra `inputs/`); bytes só reportados com RT válido.
