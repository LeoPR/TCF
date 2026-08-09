# 2026-08-09-0042 — data: o alvo DELTA (transform de coluna × seq-RLE periódico)

Lab próprio do vencedor da triagem (`../2026-08-09-0024-data-hipoteses-restantes/`, H6+H2).
Registro prévio: `T-DATA-ALVO-DELTA` + `T-SEQRLE-PERIODICO` (STATUS.md) e
H-DATA-DELTA-01 + H-SEQRLE-PERIOD-01 (registry). Conclusões: [`result.md`](result.md).

## Como rodar

```
python run.py            # os 12 casos da comparação D1 (delta-coluna) x D2 (periódico)
python design_probe.py   # o periódico posto DENTRO do compact_body (monkeypatch)
python custo_cpu.py      # custo de CPU, rodadas intercaladas
python detector_v4.py    # a versão do detector que vai no weld (v1->v4) + gates
```

`run.py` confere RT em todos os casos (asserts; D2 em DOIS níveis: coluna via decoder real
+ valor via `decode_value` real) e regrava `outputs/`.

**Ordem de leitura**: `result.md` (placar + custo) → `design_probe.py` (a sonda que
fundamenta o ADR) → `detector_v4.py` (a escada do custo, v1 O(n²) até v4) →
`weld_proposto.py` (o código do weld, **não soldado**) → [ADR-0040](../../../../../docs/adr/0040-seq-rle-periodico.md).

## Guia de nomes

| onde | o quê |
|---|---|
| `inputs/<caso>--json-lib-like.json` | input após higiene `json.loads(json.dumps(...))` — o que o encode recebeu |
| `intermediates/<caso>--trilha.json` | trilha do processo: prefixo dos deltas reais, runs/períodos que o detector escolheu, rota do candidato D2, se o periódico ganhou no corpo |
| `outputs/<caso>--com-spec.tcf` | wire REAL de hoje (`encode(vals, nature=SPEC_DATA_ISO)`) — decodável |
| `outputs/<caso>--delta-coluna.tcf` | wire REAL da coluna transformada pelo D1 (decodável; o un-delta é o wrapper naive do lab) |
| `outputs/<caso>--seqrle-periodico.wire.txt` | wire do PROTÓTIPO D2 — **não** é TCF válido (marcador `~` provisório), por isso `.wire.txt` e não `.tcf` |
| `outputs/<caso>.roundtrip.json` | os dois níveis de RT + amostra do input pra inspeção |
| `outputs/medicoes.md` / `.json` | tabela completa + detalhe por caso |

## Os candidatos (bytes já incluem o header hipotético: D1 +12 B, D2 +10 B)

- **C0** — `encode()` real sem spec (status quo core)
- **C1** — `encode(..., nature=SPEC_DATA_ISO)` real (status quo com spec)
- **D1** — transform de COLUNA: `[1º ordinal absoluto, depois deltas; inválido → _literal]`,
  coluna transformada vai pro `encode()` REAL (o core escolhe a rota — k baixo cai no bN)
- **D2** — seq-RLE PERIÓDICO estrito (≥2 ciclos completos) sobre o CANDIDATO real da
  nature; marcador dirty `*N~d1,...,dp|template`
- **D2L** — a forma degenerada descoberta no lab: 1 ciclo só = LISTA literal de deltas

## Decisões de método (lições da 1ª rodada, corrigidas)

1. **Medir o candidato, não o wire emitido** — quando o spec recusa, o candidato ordinal
   nem aparece no wire; o periódico muda o próprio candidato (mesma lição do H1).
2. **`_lcg % 30` não é irregular** — bits baixos do LCG têm período curto; o "espalhado"
   era quasi-periódico. Trocado por sha256 por índice.
3. A rota real do candidato digit-heavy é o **fallback raw `#TCF.8!!`** (linhas de dígito
   cruas, sem `\`) — o protótipo espelha o modo raw; `compare_for_seq` do core é só do
   modo escapado.

`src/tcf` NÃO foi tocado.
