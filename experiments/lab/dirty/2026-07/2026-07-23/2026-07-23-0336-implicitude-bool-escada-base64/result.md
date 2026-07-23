# Escada de implicitude do BOOL single-col — base64 vs cru vs 0/1 vs RLE

N=500 por dataset. Domínio bool IMPLÍCITO (tag `b` já fixa {false,true}; bit1=true). Cada forma é self-contained (n inline). `bytes` = wire total; `gzip` = pós-gzip-9 (sinal de transporte, não critério); `txt?` = é UTF-8 válido (o TCF exige texto).

| dataset | forma | bytes | gzip | txt? | RT=JSON |
|---|---|---:|---:|:---:|:---:|
| alt | json | 3250 | 58 | ✅ | ✅ |
| alt | tcf-atual | 1533 | 75 | ✅ | ✅ |
| alt | p-01 | 512 | 38 | ✅ | ✅ |
| alt | p-bin | 76 | 37 | ⚠️bin | ✅ |
| alt | p-b64 | 97 | 37 | ✅ | ✅ |
| alt | p-hex | 139 | 37 | ✅ | ✅ |
| alt | p-rle | 2012 | 54 | ✅ | ✅ |
| all-true | json | 3000 | 49 | ✅ | ✅ |
| all-true | tcf-atual | 36 | 54 | ✅ | ✅ |
| all-true | p-01 | 512 | 37 | ✅ | ✅ |
| all-true | p-bin | 76 | 37 | ⚠️bin | ✅ |
| all-true | p-b64 | 97 | 37 | ✅ | ✅ |
| all-true | p-hex | 139 | 37 | ✅ | ✅ |
| all-true | p-rle | 18 | 36 | ✅ | ✅ |
| most-true | json | 3025 | 61 | ✅ | ✅ |
| most-true | tcf-atual | 282 | 70 | ✅ | ✅ |
| most-true | p-01 | 512 | 40 | ✅ | ✅ |
| most-true | p-bin | 76 | 41 | ⚠️bin | ✅ |
| most-true | p-b64 | 97 | 46 | ✅ | ✅ |
| most-true | p-hex | 139 | 39 | ✅ | ✅ |
| most-true | p-rle | 237 | 44 | ✅ | ✅ |
| rand-50 | json | 3261 | 195 | ✅ | ✅ |
| rand-50 | tcf-atual | 1155 | 256 | ✅ | ✅ |
| rand-50 | p-01 | 512 | 147 | ✅ | ✅ |
| rand-50 | p-bin | 76 | 99 | ⚠️bin | ✅ |
| rand-50 | p-b64 | 97 | 117 | ✅ | ✅ |
| rand-50 | p-hex | 139 | 120 | ✅ | ✅ |
| rand-50 | p-rle | 1011 | 197 | ✅ | ✅ |
| rand-10 | json | 3452 | 125 | ✅ | ✅ |
| rand-10 | tcf-atual | 448 | 157 | ✅ | ✅ |
| rand-10 | p-01 | 512 | 100 | ✅ | ✅ |
| rand-10 | p-bin | 76 | 86 | ⚠️bin | ✅ |
| rand-10 | p-b64 | 97 | 91 | ✅ | ✅ |
| rand-10 | p-hex | 139 | 95 | ✅ | ✅ |
| rand-10 | p-rle | 389 | 128 | ✅ | ✅ |

## Leitura da pergunta (base64 vs cru vs textual)

> Framing: `bytes` inclui ~13 B do header do protótipo (`#P8b.xxx\n500\n`). Os PAYLOADS puros são: cru=**63 B** (500 bits), base64=**84 B**, hex=**126 B**, 0/1=**500 B**.

- **Piso informacional** = 500 bits = **63 B** (bit-packed cru). Irredutível de um bool[500].
- **`p-bin` (cru)** atinge o piso MAS não é UTF-8 válido — quebra o invariante textual/inspecionável do TCF e o gate byte-canônico. Só serviria num side-channel binário.
- **A pergunta, respondida**: base64 paga **+33% sobre o cru** (84 vs 63 B payload) e mantém o arquivo TEXTUAL e válido. **Mas depois do gzip a diferença some**: no `alt`, cru=37 e b64=37 B — IDÊNTICOS; nos `rand` a folga do cru sobre base64 fica em ~10-20 B. Ou seja, sob transporte comprimido, base64 é **quase de graça** e você fica com um `.tcf` legível. É melhor que o cru COMO ARQUIVO TEXTO. `p-hex` custa +100% — pior escolha.
- **Mas não é ganho universal vs o `.8H` atual**: para bool de ALTA entropia o bit-pack arrasa (`rand-50`: 1155→97 B; `alt`: 1533→97). Para BAIXA entropia o formato ATUAL já ganha (`all-true`: 36 B < 97 do base64; a maquinaria HCC/`^N` já esmaga constante/runs). Logo bit-pack+base64 é **candidato de `min()` por-coluna** (nunca-pior), não default.
- **`p-01`** (1 char/bool) é o mais legível e ainda ~3× menor que o `.8H`; gzipa muito bem (`010101` é padrão) — às vezes bate o cru pós-gzip. Legibilidade máxima, densidade média.
- **`p-rle`** depende dos DADOS: esmaga `all-true`(18)/`most-true`(237), perde feio no `alt`(2012)/`rand`. Não-geral — outro candidato de `min()`, não default.
- **Conclusão**: o eixo do bit-pack é latência/terminal (piso de bytes), não byte de transporte — o gzip confirma o alerta da memória (F3 pós-brotli ~net-zero). base64 é a forma textual correta SE o modo denso for adotado, como candidato `min()` para bool de alta entropia; a implicitude do tipo (`b`, sem literais) é o ganho garantido e ortogonal.

**35 medições · 0 falhas de equivalência JSON.** Regenera: `python run.py`.
