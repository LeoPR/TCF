# EXP-006 — Flag P (Affix-DICT) em identificadores estruturados

## Objetivo

Validar Affix-DICT (flag P, Proposta H) em datasets com **prefixo claro**.
Compara TCF v0.5 SRDM vs SRDMP em 5 cenarios, com auto-detect de prefix.

## Como funciona

Quando flag P ativa, o encoder:
1. Detecta longest common prefix por coluna
2. Threshold: `|prefix| ≥ 4 chars` E `cobertura ≥ 70%` E `ganho ≥ 50B`
3. Auto-bypass quando nao vale (caso C4 emails)

Sintaxe:
```
codigo: affix="PED-2026-00"
01
02
03
```

Decoder le `affix=` no col header, prepende ao decodificar.

## Cenarios

| ID | Tipo | Padrao esperado |
|----|------|------------------|
| **C1** | Codigo PED-NNNN | `PED-2026-` (100% prefix) |
| **C2** | TPC-H supplier | `Supplier#000000` (100% prefix) |
| **C3** | URLs API | `https://api.example.com/v1/users/0` |
| **C4** | Emails 2 dominios | sem prefix (auto-bypass esperado) |
| **C5** | Misturado | `INV-2026-` em codigo + outras cols |

## Resultados

| Cenario | SRDM | SRDMP | **P vs SRDM (texto)** | SRDM+gz | SRDMP+gz | P+gz vs no-P+gz |
|---------|----:|------:|----------------------:|--------:|---------:|----------------:|
| C1 codigo PED | 2151 | **1072** | **-50.2%** | 706 | 632 | -10.5% |
| C2 TPC-H supplier | 2837 | **1362** | **-52.0%** | 821 | 751 | -8.5% |
| C3 URLs | 3734 | **1058** | **-71.7%** | 384 | 352 | -8.3% |
| C4 emails (auto-bypass) | 2099 | 2100 | **+0.0%** | 371 | 373 | +0.5% |
| C5 misturado | 4157 | **2275** | **-45.3%** | 1286 | 1184 | -7.9% |
| **medias** | | | **-43.8%** | | | **-7.0%** |

## Achados

### A1 — Affix funciona muito bem em prefixos limpos

Em C1, C2, C3, C5, ganho de **-45% a -72% no texto puro**. Prefixos
de 10-35 chars sao removidos do body, body so traz sufixos.

### A2 — Auto-bypass funciona em C4

C4 (emails com 2 dominios distintos) **NAO ativou** affix. Algoritmo
detectou que LCP comum entre `user000@gmail.com` e `contact000@company.com`
eh muito curto. Resultado: SRDM = SRDMP em bytes (diff 0%).

### A3 — Apos gzip, ganho diminui mas nao zera

P vs no-P apos gzip: -7% a -10.5%. gzip absorve parte da repeticao
do prefix mas nao tudo — bytes que nao sao emitidos nao podem ser
comprimidos.

### A4 — Roundtrip OK em TODOS os 10 cenarios (5 × 2 variantes)

Bug encontrado e corrigido durante este experimento:

**Bug**: regex original do col header `^([^:#\s][^:]*):(.*)$` confundia
linhas como `https://api.example.com/...` com col header (capturava
`https` como nome de coluna).

**Fix**: regex restritivo agora exige nome de coluna como identificador
valido + `:` + fim-de-linha OU modifier (`affix="..."`):
```python
r"^([a-zA-Z_][a-zA-Z0-9_]*):(\s*$|\s+\w+=.*$)"
```

Strings literais com `:` no meio (URLs, MAC, etc.) nao casam mais
acidentalmente. Roundtrip 100% em SRDM e SRDMP.

## Headers reais (samples)

### C1 — codigo PED-NNNN
```
#TCF.5 SRDMP
# s:3
codigo: affix="PED-2026-00"
02
03
07
09
20
...
```
Prefix detectado: `PED-2026-00` (11 chars). Sufixos sao 2 digitos.

### C2 — TPC-H supplier
```
#TCF.5 SRDMP
# s:2
s_name: affix="Supplier#000000"
024
028
037
003
029
...
```
Prefix `Supplier#000000` (15 chars). Sufixos sao 3 digitos.

### C3 — URLs
```
#TCF.5 SRDMP
# s:3,2
endpoint: affix="https://api.example.com/v1/users/0"
07/profile
23/profile
35/profile
...
```
Prefix detectado eh longo (35 chars). Cada linha vira `NN/profile`.

### C4 — Emails (sem prefix detectado, auto-bypass)
```
#TCF.5 SRDMP
# s:2
email:
user026@gmail.com
user041@gmail.com
user040@gmail.com
contact039@company.com
contact014@company.com
```
Sem `affix=` — algoritmo desativou flag em runtime. Output identico
a SRDM.

### C5 — Misturado (codigo + nomes + categorias)
```
#TCF.5 SRDMP
# s:2,3
codigo: affix="INV-2026-00"
011
021
058
001
...
cliente_nome:
Cliente_018
Cliente_007
3*Cliente_017
...
categoria:
2*TIPO_A
TIPO_B
TIPO_C
```
Affix so na coluna `codigo` (onde tem prefix). `cliente_nome` e
`categoria` viram normais (RLE/dict aplicado).

## Decisao

**Flag P como opt-in (não default)**.

Razoes:
- Auto-bypass funciona, entao ativar P por default seria seguro
- Mas P traz overhead de detecao de prefix (1 passada extra)
- Ganho concentrado em datasets com identificadores estruturados
- Em datasets sem prefixo, P nao agrega nada (mas tampouco perde)

Default produção: SRDMA (flag A vira a proxima a implementar).
SRDMAP fica como "perfil estendido" para datasets com codigos estruturados.

## Pendencia detectada

Durante o experimento, apareceu:
- Bug do regex resolvido **(corrigido durante o experimento)**
- Strings com `:`, `*`, `+`, `-` em conteudo precisarao de
  **escape** ou **quoting** quando aparecerem como literais. Ainda
  nao implementado — registrar.

## Arquivos produzidos

```
outputs/
  C1-codigo-PED/
    source.csv      tcf-SRDM.tcf      tcf-SRDMP.tcf
  C2-tpch-supplier/  ...
  C3-urls/  ...
  C4-emails/  ...
  C5-misturado/  ...
  results.json
```

## Status

- [x] Encoder com flag P + auto-detect de prefix
- [x] Decoder parseia `col: affix="..."` com escape
- [x] Bug do regex de col header corrigido
- [x] 10/10 roundtrips OK
- [x] Ganho mensurado: -44% texto / -7% gzip (medias)
- [x] Auto-bypass validado em C4
- [ ] (futuro) flag para sufixo (`@dominio.com`)
- [ ] (futuro) mascara estrutural (CPF, UUID com `-`)
- [ ] (futuro) escape de chars reservados em strings literais
