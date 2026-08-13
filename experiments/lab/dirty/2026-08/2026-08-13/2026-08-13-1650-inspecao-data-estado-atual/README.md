# Inspeção do tipo DATA — estado em 2026-08-13

> **Pedido do owner**: *"preciso de uma demonstração com as modificações até o momento, mas
> vamos olhar só data, pode executar um dirty lab só pra inspecionar"*.

Lab de **inspeção**, não de decisão. Não escolhe design, não abre ticket de rota: mostra o
que as modificações acumuladas no tipo data produzem, com **o wire aberto e explicado**.
As conclusões daqui são **orientativas** (é dirty) — o que vale como verificação está nos
testes soldados e no `EXP-017` clean.

## Estado — era / foi / é / será

- **Era** (até 2026-08-07): data era string como qualquer outra. `2026-01-31 → 2026-02-01`
  não é "+1" em campo nenhum isolado, então o OBAT via texto e o ganho despencava com a
  irregularidade do passo.
- **Foi** (4 modificações, em ordem):
  1. **`SPEC_DATA_ISO`** (weld T-DATA-LAZY-ISO, 2026-08-08) — `YYYY-MM-DD` → ordinal
     decimal. A forma que rende é a que deixa a **aritmética visível** pro seq-RLE.
  2. **seq-RLE periódico** (ADR-0040, 2026-08-09) — `*N~d1,…,dp|âncora`: o delta **cicla**.
     Pega o que o passo constante não pega (dia útil, feriado mensal).
  3. **Fix do `view`** (2026-08-12) — coluna com nature em modo dict respondia `where`/
     `group_count` pelo **payload ordinal**; fonte única de reversão.
  4. **`wire_id` curto** (ADR-0041 weld A, 2026-08-13) — `:data-iso` → **`:dt`**. O
     comprimento do id **decide o FLOOR**: com 10 B de tag a nature perdia em N ≥ 11.
- **É**: o que este lab mostra — 29 casos, 0 falhas de round-trip.
- **Será**: `T-SPEC-SEM-CARIMBO` (tirar o id do fio quando o contrato vive nas pontas) e a
  triagem `.9`/`2.0` de `docs/theory/spec-orienta-nao-manda-triagem.md`.

## Como rodar

```
python run.py          # regenera inputs/, intermediates/, outputs/ e resultado.json
```

Sai 0 só se **todos** os round-trips fecharem. `src/tcf` não é tocado — o lab só chama a
API pública (`encode`/`decode`/`view`).

## O fluxo, e onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<c>.entrada.json` | o que entrou (sintético **materializado** também) |
| `inputs/<c>.fonte.json` | procedência: gerador, ideia, n/k, hash, se é corpus real |
| `intermediates/<c>.anatomia.txt` | **o wire decomposto e explicado** ← a peça de inspeção |
| `intermediates/<c>.trace.txt` | telemetria do encode (`SideOutputs`): apply-rate, cadence, runs |
| `outputs/<c>.tcf` | o wire, com extensão real |
| `outputs/<c>.roundtrip.json` | `decode(wire)` — **diff contra a entrada = a contra-prova** |
| `outputs/INDEX.md` | tabela: caso → ideia → input → wire → bytes → RT |

`inputs/<c>.entrada.json` e `outputs/<c>.roundtrip.json` são gravados com a **mesma
formatação**: a contra-prova é `diff` dar vazio, e o `run.py` faz esse assert.

## Progressão de dados

- **Ilustrativo** (`a*`): o mecanismo visível — passo constante, ciclo, passo irregular.
- **Flip do FLOOR** (`b*`): N=10 / 11 / 12, a mudança de hoje isolada.
- **Bordas** (`c*`): onde o FLOOR **recusa** — agrupada, aleatória, suja, nulos, N=1,
  descendente.
- **Estrutura** (`d*`): multi-coluna (+ `view` lazy) e dataset `.8H`.
- **Migração** (`e1`): wire gravado com `:data-iso` — falha alto e lê pela válvula.
- **Real** (`f*`): 12 colunas de data do corpus já extraído de `Z:/tcf-data/` pelo EXP-017
  (o lab **não** re-extrai nem baixa nada; roda sem `Z:` montado, pulando os `f*`).

## Vínculo

Tickets: `T-NOME-SPEC-CURTO` (soldado hoje) · `T-SEQRLE-PERIODICO` (ADR-0040) ·
`T-DATA-LAZY-ISO` · `T-LAZY-BYPASS-ARITMETICO` (o fix do view) · `T-SPEC-SEM-CARIMBO`.
ADRs: [0040](../../../../../../docs/adr/0040-seq-rle-periodico.md) ·
[0041](../../../../../../docs/adr/0041-spec-id-tres-planos.md).
Resultado e leitura: [`result.md`](result.md).
