# Resumo — Sub-exp 06 (auto-hint regression D1-D9)

baseline total: 1615 B
fork total:     1890 B  (+275, +17.0%)

RT: 9/9

Ganhos (fork < baseline): 2
Empates: 2
**Regressoes**: 5

## Tabela

| Dataset | rows | uniq | baseline | fork | Δ | RT |
|---|---:|---:|---:|---:|---:|---|
| [D1-emails-simples](D1-emails-simples/5-rt-status.txt) | 12 | 12 | 118 | 104 | -14 | OK |
| [D2-emails-quote-id](D2-emails-quote-id/5-rt-status.txt) | 12 | 12 | 166 | 169 | +3 [REGRESSAO] | OK |
| [D3-stress-substring](D3-stress-substring/5-rt-status.txt) | 12 | 12 | 177 | 185 | +8 [REGRESSAO] | OK |
| [D4-caos-mix](D4-caos-mix/5-rt-status.txt) | 12 | 12 | 113 | 113 | +0 | OK |
| [D5-padroes-multiplos](D5-padroes-multiplos/5-rt-status.txt) | 12 | 12 | 281 | 484 | +203 [REGRESSAO] | OK |
| [D6-poucos-em-ruido](D6-poucos-em-ruido/5-rt-status.txt) | 12 | 12 | 287 | 354 | +67 [REGRESSAO] | OK |
| [D7-aninhamento](D7-aninhamento/5-rt-status.txt) | 12 | 12 | 215 | 315 | +100 [REGRESSAO] | OK |
| [D8-cabeca-cauda](D8-cabeca-cauda/5-rt-status.txt) | 12 | 12 | 100 | 100 | +0 | OK |
| [D9-frequencia-alta](D9-frequencia-alta/5-rt-status.txt) | 20 | 20 | 158 | 66 | -92 | OK |

## Regressoes detalhadas

- **D2-emails-quote-id**: 166 → 169 (+3 bytes)
- **D3-stress-substring**: 177 → 185 (+8 bytes)
- **D5-padroes-multiplos**: 281 → 484 (+203 bytes)
- **D6-poucos-em-ruido**: 287 → 354 (+67 bytes)
- **D7-aninhamento**: 215 → 315 (+100 bytes)

→ H-DA-09 (always-on) NAO e' safe — hint precisa ser opt-in.

