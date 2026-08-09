# Matriz de conformidade — tipos do ciclo (bool → date)

| caso | família | rota | B | RT | rota ok | nota |
|---|---|---|---:|---|---|---|
| bool-puro | bool | `#TCF.8b1c8` | 47 | ✓ | ✓ | denso b1: 1 bit/valor, dominio implicito |
| bool-null | bool | `#TCF.8b2c8` | 79 | ✓ | ✓ | denso b2 TERNARIO: null=0/false=1/true=2 congelado |
| bool-all-true | bool | `#TCF.8b` | 16 | ✓ | ✓ | core-com-slots (ADR-0038): RLE de linha vence o denso |
| bool-lazy-extras | bool | `#TCF.8bB2c8` | 84 | ✓ | ✓ | lazytype (ADR-0039): cabeca congelada + extra str declarad |
| bool-so-null | bool | `#TCF.8` | 14 | ✓ | ✓ | null puro: core, slot 0 |
| int-01 | num | `#TCF.8nB1c8` | 55 | ✓ | ✓ | nB tipado: dominio {0,1}, 1 bit |
| int-0a3 | num | `#TCF.8nB2c8` | 93 | ✓ | ✓ | nB tipado: 2 bits |
| float-2vals | num | `#TCF.8nB1c8` | 59 | ✓ | ✓ | float low-card via nB; grafia canonica no _cast_tipo |
| int-null | num | `#TCF.8nB2c8` | 91 | ✓ | ✓ | null ocupa slot; dominio {0,1}+null |
| int-sequencial | num | `#TCF.8n` | 23 | ✓ | ✓ | rota tipada usa o CORPO do core: `*200+1|` uniforme |
| int-PERIODICO | num | `#TCF.8n` | 33 | ✓ | ✓ | ADR-0040 na rota TIPADA: `*200~10,10,10,50|` |
| int-grafia-canonica | num | `#TCF.8nB264` | 65 | ✓ | ✓ | grafias 01/1.50/+1/1e3 nao existem na emissao |
| str-low-card | str | `#TCF.8B1c8` | 60 | ✓ | ✓ | bN de dominio: k=2, 1 bit/linha |
| str-true-false | str | `#TCF.8B1c8` | 57 | ✓ | ✓ | bool-em-string fica STRING (caixa preservada) — bN resolve |
| str-high-card | str | `#TCF.8!!` | 58 | ✓ | ✓ | alta cardinalidade: OBAT/HCC + polaridade |
| str-vazia-e-espaco | str | `#TCF.8B264` | 51 | ✓ | ✓ | vazio e whitespace sobrevivem (NAO strip) |
| cpf-2-distintos | nature | `#TCF.8B13c` | 61 | ✓ | ✓ | FLOOR-ve-bN (fix 2026-08-08): bN vence a nature aqui |
| cnpj | nature | `#TCF.8 :cnpj` | 25 | ✓ | ✓ | constante: RLE de linha vence; nature recusa |
| ip-sequencial | nature | `#TCF.8!` | 39 | ✓ | ✓ | multi-delta per-run (ADR-0016) come o IP; nature recusa |
| cpf-com-null | nature | `#TCF.8B13c` | 45 | ✓ | ✓ | fix None nas 4 natures: nao estoura TypeError |
| data-diaria | data | `#TCF.8 :data-iso` | 32 | ✓ | ✓ | ordinal + `*600+1|` uniforme |
| data-uteis | data | `#TCF.8 :data-iso` | 40 | ✓ | ✓ | ADR-0040: `*600~1,3,1,1,1|` — era 1590 B |
| data-uteis-feriado | data | `#TCF.8 :data-iso` | 677 | ✓ | ✓ | periodo quebrado a cada ~21: runs menores |
| data-mensal | data | `#TCF.8 :data-iso` | 679 | ✓ | ✓ | antes o spec RECUSAVA (1085); periodico p=12 pode inverter |
| data-com-ruido | data | `#TCF.8 :data-iso` | 148 | ✓ | ✓ | valvula lazy: lixo vira _literal, resto comprime |
| data-com-null | data | `#TCF.8 :data-iso` | 147 | ✓ | ✓ | None passa pelo slot 0, fora da nature |
| data-grafia-suja | data | `#TCF.8B23c` | 62 | ✓ | ✓ | nenhuma parseia canonica -> spec recusa a coluna |
| ids-turno | num-str | `#TCF.8` | 32 | ✓ | ✓ | `*600~10,10,10,50|` no nivel do CORE — era 1959 B |
| date-nativo | fail-loud | `HierarchicalError: valor` | — | — | ✓ |  |
| decimal | fail-loud | `HierarchicalError: valor` | — | — | ✓ |  |
| datetime | fail-loud | `HierarchicalError: valor` | — | — | ✓ |  |
| int-e-str-misto | fail-loud | `HierarchicalError: tipos` | — | — | ✓ |  |

## Interação do periódico (antes = lab 0042)

- `data-diaria`: 32 → **32 B** (1.0×)
- `data-uteis`: 1590 → **40 B** (39.8×)
- `data-uteis-feriado`: 1889 → **677 B** (2.8×)
- `data-mensal`: 1085 → **679 B** (1.6×)
- `ids-turno`: 1959 → **32 B** (61.2×)
