# EXP-007 — Prototipo TCF-CORE (OBAT + HCC em src/tcf)

**Data**: 2026-05-17
**Tipo**: experimento clean
**Ciclo**: v0.6 (primeiro clean apos saida do dirty lab)
**Estado**: foi (fechado)

## Pergunta cientifica

A API publica em `src/tcf/` (`from tcf import encode, decode`),
welded do dirty lab v0.6, reproduz os bytes do baseline canonico
M9-M14 byte-a-byte em todos os 9 datasets sinteticos de controle?

## Hipotese

**H1**: sim. Apos welding step 3 (commit `1fcb88b`) + contra-prova
M14 (commit `ab2eada`), `src/tcf` deve produzir exatamente os
mesmos bytes em D1-D9 que a cadeia dirty M9 → M10 → M11 → M12 →
M13 → M14.

**H0** (rejeitada): se algum byte difere, indica regressao no
welding e necessita rollback/fix.

## Metodo

1. Importar API publica: `from tcf import encode, decode`
2. Para cada dataset Di em `datasets/synthetic/`:
   - Carregar linhas (CSV single-column)
   - `tcf_text = encode(linhas)`
   - `decoded = decode(tcf_text)`
   - Verificar `decoded == linhas` (RT)
   - Salvar em `outputs/Di.tcf`
3. Comparar `outputs/` com baseline byte-canonico
   (`experiments/lab/dirty/old/2026-05-17-M14-clean-validation-srctcf/M14-tcf-clean/output/`)
   via `diff -r`
4. Gerar `manifest.jsonl` (1 linha por run) e `report.md`
   (analise consolidada)

## Datasets

9 datasets sinteticos de controle (de `datasets/synthetic/`):

| ID | Cenario |
|---|---|
| D1 | emails-simples (gmail/hotmail/yahoo) |
| D2 | emails-quote-id (apostrofes em nomes) |
| D3 | stress-substring (URLs api/users/*) |
| D4 | caos-mix (alto caos) |
| D5 | padroes-multiplos (email + uuid) |
| D6 | poucos-em-ruido (timestamps unicos) |
| D7 | aninhamento (padroes em multiplas positions) |
| D8 | cabeca-cauda (prefix/suffix estaveis) |
| D9 | frequencia-alta (wrapper com middle variavel) |

## Resultado

Ver [`report.md`](report.md) (gerado por `run.py`).

Resumo:
- **RT**: 9/9 OK ✓
- **Bytes total**: 1615 (esperado 1615) ✓
- **Diff vs M14 baseline**: vazio (byte-identico) ✓

## Como rodar

```bash
python experiments/lab/clean/EXP-007-prototipo-tcf-core/run.py
```

Pre-requisito: `src/tcf/` welded (commits `d5e4c24` Step A,
`af555b9` Step B, `1fcb88b` Step C).

## Como reproduzir validacao

```bash
diff -r \
  experiments/lab/clean/EXP-007-prototipo-tcf-core/outputs/ \
  experiments/lab/dirty/old/2026-05-17-M14-clean-validation-srctcf/M14-tcf-clean/output/
```

Deve retornar vazio (exit 0).

## Significado

EXP-007 e' o **primeiro experimento clean v0.6**. Apos passar,
confirma que:

1. Welding do dirty → src/tcf esta completo e correto
2. API publica `from tcf import encode, decode` e' utilizavel
   externamente (sem dependencia do dirty lab)
3. Cadeia byte-canonica M9 → M14 → **EXP-007** se mantem
4. Dirty lab pode ser considerado **backup canonico** apartir daqui

## Direcoes futuras (fora do escopo de EXP-007)

Ver `docs/theory/perspectiva-triplice-e-pre-tx.md` para roadmap
das 3 estrategias (pre-filtro multi-col + tipos; manager com
memoria shared; slot detection online).

Direcao mais imediata para proximo EXP clean:
- **EXP-008**: type encoders (CPF/UUID/data) — Estrategia 1.A
- OU
- **EXP-008**: multi-coluna ingenuo (instancias TCF por coluna) —
  Estrategia 1.B

## Conexoes

- [`../../../src/tcf/`](../../../src/tcf/) — codigo canonico testado
- [`../../../datasets/synthetic/`](../../../datasets/synthetic/) — datasets
- [`../../dirty/old/2026-05-17-M14-clean-validation-srctcf/`](../../dirty/old/2026-05-17-M14-clean-validation-srctcf/) — baseline byte-canonico
- [`../../../docs/algorithms/`](../../../docs/algorithms/) — documentacao OBAT + HCC + TCF
