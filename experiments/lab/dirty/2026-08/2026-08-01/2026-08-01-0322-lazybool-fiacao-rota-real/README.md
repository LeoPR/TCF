# 2026-08-01-0322 — fiação do lazy bool na rota real (estudo, SEM weld)

Decisões do owner desde o lab `2026-08-01-0229` (que mediu o lazy `bB`: cabeça congelada
0/1/2 + extras do slot 3): **lazy será DEFAULT** (sem flag) e o **decode emite lista
mista** — contrato união decidido. Este lab responde às 6 perguntas de fiação antes do
weld. **Veredito: SEM BLOQUEADOR.**

## As 6 respostas (resumo; detalhe no result.md)

1. **Detecção**: `vals ⊆ {bool, str, None}` com ≥1 bool E ≥1 str. 8/8 casos-borda corretos
   (str+null sem bool → flat; bool+str+int → fora, é outro ticket; 1 único extra → entra)
   e zero divergências na varredura dos consumidos do lab 0229. É um ramo ANTES do `.8H`,
   não mutação do `_tipo_single_col`.
2. **FLOOR trivial**: para união, b1/b2/core-slots não existem e o flat-string muda o
   contrato — o lazy é o único candidato que preserva tipo.
3. **Dispatch sem colisão**: índice 6 `B` (flat bN) × `b` (tipado) são chars distintos;
   `#TCF.8B` flat segue roteando (RT OK); `#TCF.8bB` hoje morre no fail-loud de modo denso
   — índice 7 `B` sob tag `b` é namespace livre; ramo prototipado decodifica com RT OK.
4. **Domínio de extras**: comprimido pelo core (1 extra = 5 B, 5 = 19 B, 20 = 20 B).
   **Dois achados de fiação**: (i) `extra-vazio` — o domínio é uma linha vazia invisível,
   válido, espelho do bugfix `[:-1]` do `dominio_bn`; (ii) **LF embutido num extra NÃO é
   recusado de graça** — o fail-loud de LF mora no `encode` público flat, não no
   `_encode_column` (medido); o weld deve adicionar check explícito (prototipado).
5. **Canonicidade**: extras por 1ª aparição, determinístico; domínio **redeclarando a
   cabeça** (`0` cru) → fail-loud no decode; extras `"1"/"2"/"true"` são válidos (slots ≥3).
6. **Gates**: `encode_com_lazy` (rota simulada) aplicado às 12 colunas dos dois gates —
   **zero wires alterados**.

## Forma do weld proposta

1. `encoder.py`: detector lazy como ramo antes do `.8H` (após `_tipo_single_col` → None);
   candidato `bB`; recusas w>8 e LF-em-extra (check explícito).
2. `decoder.py:_decode_typed`: ramo `modo_c == 'B'` → decode lazy (tabela = `TABELA_B2` +
   domínio declarado).
3. `tipos_internos.py`: sem mudança de dados.
4. Decode recusa declaração da cabeça (Q5).

## Rodar

```
python run.py
```

Sai `0` só se as 6 perguntas fecharem sem bloqueador. `src/tcf` intocado.
