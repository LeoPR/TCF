# Lab 2026-07-17-0014 — SINTÉTICOS DE CONTROLE do fluxo hierárquico (navegação)

**Status**: executado; suíte de pins WELDADA em `tests/test_hierarchical_control_synthetics.py`.
**Pedido do owner**: "lembre dos sintéticos de controle pra gente ter uma noção de como a
navegação do fluxo do tcf está se saindo" + "veja se os testes antigos podem ser melhorados".

**A lacuna que este lab fecha**: os testes antigos do `.8H` provam CORREÇÃO (RT + fail-loud,
754 testes) mas não medem/pinam COMPORTAMENTO DE FLUXO — pra onde os bytes vão, quais mecanismos
disparam. Uma regressão de eficiência seria invisível (o flat tem D1-D9/real-world pinados; o
hierárquico não tinha NENHUM pino de bytes).

## Desenho

- **Fonte única**: `tests/fixtures/control_synthetics_h.py` — gerador seedado (12 casos,
  design-realista, viés declarado: construídos pra OBSERVAR, não pra ganhar bytes) +
  `decompose()` (buckets meta/controle/folhas pela MESMA regra de classificação do decode).
- Cada caso isola UM mecanismo; o lab emite `.tcf` inspecionável + roundtrip byte-idêntico
  (assert) + tabela de navegação (`outputs/00-resultado.txt`, `outputs/01-navegacao.csv`).
- O teste formal pina os buckets byte-exatos (re-pináveis, ADR-0024) + asserts de mecanismo.

## Casos e o que cada um observa

| caso | mecanismo | leitura |
|---|---|---|
| c01-uniforme | mask omitida quando uniforme | **0 colunas de controle** ✓ |
| c02-telemetria-array | fan-out fixo como array | counts colapsam (8 B/200 inst.) ✓; folhas 98,9% do wire |
| c03-telemetria-split | par de controle do c02 | **split −9,5%** com série realista (random-walk) |
| c04-ragged / c05-null-campo | mask 2/3-estados | controle 78/90 B p/ 120 regs (RLE segura) |
| c06-null-elemento | **emask densa** | controle = 29% do wire (409 B vs 973 B de folhas) |
| c07-arrays-vazios | counts com vazios espalhados | **counts variáveis NÃO colapsam**: controle 201 B ≈ dados 218 B |
| c08-matriz | counts 2 níveis constantes | 7+7 B ✓ |
| c09-espinha | fan-out variável 0..4 | count 238 B p/ 80 regs (não colapsa, esperado) |
| c10/c11 | tipos cadenciados / categórico | 0 controle; seq-RLE e refs fazem o trabalho |
| c12-compose-total | integração P1+P2+P3a+P3b+P4a | 5 colunas de controle, 65% folhas |

## Achado novo (da primeira execução): ordem de chaves em ragged

Chave opcional que aparece pela 1ª vez DEPOIS do 1º registro volta na ordem do **schema**
(união por 1ª aparição — ao fim do dict), não na posição por-registro. Igualdade semântica
(dict) preservada; byte-igualdade do `json.dumps` NÃO. Mínimo: `[{a,c},{a,obs,c}]` → registro 2
volta `[a,c,obs]`. **754 testes + auditorias não pegaram** (didáticos tinham ordem compatível).
Relevância: o contrato **S0** do DatasetH (lab `2026-07-16-1708`) preserva ordem por-registro —
**gap S0×`.8H`** a decidir no S6/P4b. Pinado como comportamento em
`test_ordem_de_chaves_ragged_e_do_schema`; registrado em T-API-BOUNDARY-CONTRACTS +
T-CODE-TCF8H-JSON-PARITY. **Não consertado** (decisão de contrato do owner).

## Avaliação dos testes antigos (o pedido "podem ser melhorados?")

**Ficam como estão** — papel correto (correção/RT/fail-loud) e são eles mesmos pinos. O que
faltava não era refazê-los, era a dimensão ausente (fluxo/bytes), agora coberta por esta suíte.
Refazer os RT antigos não pagaria nada; a melhoria certa era ADITIVA.

Ver [result.md](result.md). Zero mudança em `src/tcf`.
