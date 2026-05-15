# EXP-007 — Relatorio

**Data execucao**: 2026-05-17
**Estado**: foi (fechado, validou)

## Resumo executivo

`src/tcf` reproduz baseline byte-canonico do dirty lab M14 em todos
os 9 datasets sinteticos de controle. **Hipotese H1 confirmada**:
welding completou sem regressao.

| Metrica | Resultado |
|---|---|
| RT (roundtrip OK) | **9/9** ✓ |
| Bytes totais | **1615** (esperado 1615) ✓ |
| Raw totais | 2981 |
| Ratio medio | **54.2%** |
| Diff vs M14 | **vazio (byte-identico)** ✓ |

## Por dataset

| Dataset | Bytes | Raw | Ratio | RT |
|---|---:|---:|---:|---:|
| D1-emails-simples | 118 | 191 | 61.8% | ✓ |
| D2-emails-quote-id | 166 | 247 | 67.2% | ✓ |
| D3-stress-substring | 177 | 344 | 51.5% | ✓ |
| D4-caos-mix | 113 | 156 | 72.4% | ✓ |
| D5-padroes-multiplos | 281 | 418 | 67.2% | ✓ |
| D6-poucos-em-ruido | 287 | 533 | 53.8% | ✓ |
| D7-aninhamento | 215 | 337 | 63.8% | ✓ |
| **D8-cabeca-cauda** | **100** | **385** | **26.0%** | ✓ |
| D9-frequencia-alta | 158 | 371 | 42.6% | ✓ |
| **TOTAL** | **1615** | **2981** | **54.2%** | **9/9** |

## Analise

### Faixas de compressao

- **Melhor caso (D8 cabeca-cauda — 26.0%)**: padrao `common/prefix/X/common/suffix`
  onde so' X varia. OBAT detecta prefix + suffix estaveis, HCC nao
  precisa de composicoes adicionais — apenas 2 atom refs por linha.
- **Pior caso (D4 caos-mix — 72.4%)**: alta variabilidade nas
  strings (`[X]*'YYY'@4Z` com X, Y, Z todos variaveis).
  Poucas oportunidades de reuso.

A faixa 26%-72% reflete o **teto inerente** de cada cenario, nao
limitacao do algoritmo. Padroes estaveis (D8, D9) sao bem
explorados; caos genuino (D4) tem pouco a comprimir.

### Validacao byte-canonica

```
$ diff -r outputs/ ../../../lab/dirty/2026-05-17-M14-clean-validation-srctcf/M14-tcf-clean/output/
(exit 0, vazio)
```

Cadeia byte-identica preservada:
```
M9 → M10 → M11 → M12 → M13 → M14 → EXP-007
1615 bytes em todos os checkpoints.
```

### Significado

EXP-007 e' o primeiro experimento clean v0.6 — apos saida do dirty
lab. Confirma:

1. **API publica funciona**: `from tcf import encode, decode`
   utilizavel externamente sem dependencia do dirty lab
2. **Welding correto**: src/tcf reproduz dirty M14 exato
3. **Dirty lab pode ser backup**: cadeia byte-canonica fechada;
   nao depende mais do dirty para o algoritmo principal

## Limitacoes

- **Single-column**: TCF v0.6 atual processa 1 coluna por vez.
  Multi-coluna e' Estrategia 1.B no roadmap.
- **Datasets sinteticos pequenos**: D1-D9 sao 12-20 linhas cada.
  Escala (N grande, L grande) nao testada.
- **Sem benchmark de tempo/memoria**: foco aqui e' correcao byte
  apenas. Triple perspective (compressao + memoria + latencia)
  caracterizada apenas no eixo compressao.

## Direcoes futuras

Ver [`../../../../docs/theory/perspectiva-triplice-e-pre-tx.md`](../../../../docs/theory/perspectiva-triplice-e-pre-tx.md)
para 3 estrategias avaliadas:

- **Estrategia 1.A** (proximo passo natural): EXP-008 com type
  encoders (CPF, UUID, data ISO) — Estrategia 1.A do roadmap
- **Estrategia 1.B**: EXP-009 multi-coluna ingenuo (instancias por
  coluna)
- **Estrategia 3.B**: HCC online com slot detection (resolveria
  D9 melhor)

## Conexoes

- [`README.md`](README.md) — descricao do experimento
- [`config.json`](config.json) — parametros
- [`run.py`](run.py) — reproducao
- [`manifest.jsonl`](manifest.jsonl) — registro de execucoes
- [`outputs/`](outputs/) — TCFs gerados
- [`../../dirty/2026-05-17-M14-clean-validation-srctcf/`](../../dirty/2026-05-17-M14-clean-validation-srctcf/) — baseline byte-canonico
