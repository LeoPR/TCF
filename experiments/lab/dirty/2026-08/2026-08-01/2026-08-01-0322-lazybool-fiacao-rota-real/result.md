# Fiação do lazy bool na rota real (2026-08-01-0322)

Estudo pré-weld. Lazy será DEFAULT (sem flag); decode emite lista mista.

## Medição base — lazy × flat-string (referência de bytes)

| coluna | n | extras | lazy bB | flat-str | RT tipo |
|---|---:|---:|---:|---:|:--|
| `extras-raro` | 200 | 1 | 86 | 97 | OK |
| `extras-frequentes` | 200 | 1 | 86 | 97 | OK |
| `k-extras-05` | 200 | 5 | 133 | 144 | OK |
| `k-extras-20` | 200 | 20 | 201 | 212 | OK |
| `armadilha-tipos` | 200 | 3 | 126 | 132 | OK |
| `real-adult-sex-lazy` | 100 | 1 | 50 | 61 | OK |

## Q1 — detecção

Detector: `vals ⊆ {bool, str, None}` com ≥1 bool E ≥1 str — nada mais.

- casos-borda: **8/8 corretos** (str+null sem bool → flat; 1 extra → entra; bool+str+int → fora; bool puro/ternário → tipado puro; str pura/só-null → flat).
- varredura FP/FN nos consumidos do lab 0229: **7 datasets, zero divergências** (esperado-lazy: ['armadilha-tipos', 'extras-frequentes', 'extras-raro', 'k-extras-01', 'k-extras-05', 'k-extras-20', 'real-adult-sex-lazy']).
- confirmação do contexto: `_tipo_single_col` devolve `None` pra união (hoje: `None`) → `.8H` → fail-loud. O detector lazy é um ramo ANTES do `.8H`, não uma mutação do `_tipo_single_col`.

## Q2 — convivência no FLOOR

Para coluna lazy, os candidatos b1/b2/core-slots **não existem** (não é bool puro) e o core-flat-de-strings **muda o contrato** (perde tipo — é referência de bytes, não candidato). Logo o lazy é o **único candidato que preserva tipo**: FLOOR trivial, sem interação. Verificado por construção: `encode_com_lazy` devolve o wire lazy sempre que o detector dispara, e o RT tipo-estrito passou em todas as colunas acima.

Se o usuário converter pra str ANTES (flat-string), é decisão dele — fora da rota.

## Q3 — dispatch do decode

**Sem colisão**: o dispatch é O(1) pelo índice 6 — `B` (maiúsculo) = flat bN (ADR-0036), `b` (minúsculo) = tipado. São chars DISTINTOS:

- `#TCF.8B…` flat segue roteando certo: RT `['0','1']*100` = **True** (wire head: `#TCF.8B1c8`).
- `#TCF.8bB…` hoje cai no `_decode_typed` e morre no fail-loud de modo denso: `fail-loud: #TCF.8b: header de modo denso invalido: 'B2c8' (esperado <modo><n-hex>)` — ou seja, o índice 7 = `B` sob tag `b` é **namespace livre**.
- ramo prototipado `modo == 'B'` → decode lazy (cabeça `TABELA_B2` + extras): RT tipo-estrito **OK**.

## Q4 — domínio de extras (comprimido pelo core, custo e bordas)

| caso | wire lazy | tamanho domínio (linhas antes do `=`) | veredito |
|---|---|---:|---|
| `extras-raro` | 86 | 5 | RT OK |
| `k-extras-05` | 133 | 19 | RT OK |
| `k-extras-20` | 201 | 20 | RT OK |
| `extra-com-=` | 21 | 5 | RT OK |
| `extra-true` | 19 | 4 | RT OK |
| `extra-vazio` | 16 | 0 | RT OK |

- `extra-com-=`: o marcador `=` no domínio é escapado (`\=`, regra do `dominio_bn`) — RT OK.
- `extra-vazio`: string vazia como extra — o domínio é uma **linha vazia invisível** (o corte `[:-1]` do bugfix do `dominio_bn`); o decode a lê como `[""]` — **válido e RT OK**. NUANCE de fiação: um wire com domínio vazio é indistinguível do extra `""` — a leitura consistente é aceitar (como o `dominio_bn` já faz), não rejeitar.
- LF embutido num extra: **achado de fiação** — o fail-loud de LF mora no `encode` público flat, NÃO no `_encode_column` (medido: devolve calado). Sem check próprio, o extra com LF corromperia o parse do domínio. O weld DEVE adicionar o check: recusa pelo check explícito: extra lazy com LF embutido nao e' representavel (LF delimita linhas do.

## Q5 — canonicidade

- extras por **1ª aparição** + header hex mínimo + wire determinístico: **OK**.
- domínio declarando a cabeça (`0` cru = slot 0 congelado): **fail-loud: dominio lazy redeclara a cabeça congelada (slot 0 = null) — grafia nao-canonica; a cabeça ** — declarar o implícito é grafia inválida (evidência em `outputs/fail-loud.txt`).
- extras `"1"`/`"2"`/`"true"` são VÁLIDOS (slots ≥3, caso armadilha) — o proibido é redeclarar o slot, não o texto.

## Q6 — gates com a rota inserida (simulada)

`encode_com_lazy` (detector + lazy, senão `encode` real) aplicado a **12 colunas** dos dois gates: **ZERO wires alterados** — gates são flat/dict, o detector nunca dispara (esperado).

## Forma do weld proposta (se aprovada)

1. **`encoder.py`**: detector lazy como ramo ANTES do `.8H` — após `_tipo_single_col` devolver `None` e antes de `_tabela_flat`/hierárquico: se `detecta_lazy(data)`, candidato `bB` (único que preserva tipo; FLOOR trivial). Recusas: w>8, e **check EXPLÍCITO de LF nos extras** (achado Q4: o fail-loud de LF mora no `encode` público flat, não no `_encode_column` — não vem de graça).
2. **`decoder.py:_decode_typed`**: ramo `modo_c == 'B'` → decode lazy (tabela = `TABELA_B2` do `tipos_internos.py` + domínio declarado de extras; reusa `decode_bn` internamente ou a mesma mecânica).
3. **`tipos_internos.py`**: sem mudança de dados — a cabeça já é `TABELA_B2`.
4. **Recusa declaração da cabeça** no decode (Q5).
5. Testes: RT tipo-estrito, armadilha `"true"`, extra vazio/`=`, fail-loud índice/header/cabeça, gates zerados, FLOOR trivial.

## Veredito

**SEM BLOQUEADOR** — as 6 perguntas fecham a favor do weld na forma acima.

