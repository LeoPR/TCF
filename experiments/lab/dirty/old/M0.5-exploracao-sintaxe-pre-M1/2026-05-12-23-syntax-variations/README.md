# 23 — variações de sintaxe (5 lado a lado em D2-mini e D2-completo)

## Princípio / motivação

Após o exp 22 ter mostrado que compact_v2 não é universalmente
melhor que v1, o user propôs variações mais radicais:

- Aspas em literais podem ser implícitas (transição lit/ref pela
  natureza dos chars: dígito ↔ não-dígito)
- O prefixo `@N:` na decl é redundante (linha já é decl pela
  ordem)

Este exp testa essas duas hipóteses em **2 datasets pequenos**
(D2-mini, D2-completo) para iterar rápido. Não escala para 21
datasets — foco é estudar formato, não validar generalização.

## Propósito

Resposta às **perguntas 1 e 3** do dirty (viabilidade + formato).
Mede o ganho de cada simplificação isoladamente.

## Comparação

5 sintaxes lado a lado:

| Sintaxe | Diferenças |
|---|---|
| verbose | exp 16 (referência) |
| compact_v1 | exp 21 — `@N:`, `@N<K`, `'X'`, `=N` |
| **compact_v1b** | NOVO — v1 sem prefixo `@N:` (linha é decl pela ordem) |
| compact_v2 | exp 22 — idx por fragmento, `'X'` |
| **compact_v3** | NOVO — v2 sem aspas, `*` separa literais consecutivos |

## Por que a quebra v1 vs v2 é diferente

(Esclarecimento pedido pelo user.)

As 5 sintaxes representam os **mesmos tokens** do algoritmo. A
diferença é **filosofia de marcação**:

- **v1**: a string da decl fica inteira; refs externas usam slice
  explícito (`@N<K`). Quebras são implícitas no length.
- **v2/v3**: a string da decl é **pré-fragmentada** nos pontos
  exatos das refs futuras; cada fragmento ganha idx. Refs apenas
  listam idx.

Em v1, paga-se `K` (length) por ref. Em v2/v3, paga-se quebra
no nó + idx pequeno por ref. Trade-off depende de N de refs.

## Resultado observado

Roundtrip **10/10 OK** (5 sintaxes × 2 datasets).

### Bytes

| Dataset | verbose | v1 | v1b | v2 | **v3** |
|---|---:|---:|---:|---:|---:|
| D2-mini (6) | 208 | 116 | 98 | 97 | **85** |
| D2-completo (12) | 456 | 232 | 193 | 191 | **177** |

### Razão vs verbose

| Dataset | v1 | v1b | v2 | **v3** |
|---|---:|---:|---:|---:|
| D2-mini | 0.558 | 0.471 | 0.466 | **0.409** |
| D2-completo | 0.509 | 0.423 | 0.419 | **0.388** |

### Razão vs compact_v1

| Dataset | v1b | v2 | **v3** |
|---|---:|---:|---:|
| D2-mini | 0.845 | 0.836 | **0.733** |
| D2-completo | 0.832 | 0.823 | **0.763** |

**v3 ganha em ambos os datasets.** Margem ~24-27% sobre v1.

### D2-mini lado a lado

**verbose** (208 bytes):
```
<body>
  no2: no1[0:12] + "hot" + no1[-8:]
</body>
```

**compact_v1** (116 bytes):
```
@2:@1<12'hot'@1>8
```

**compact_v1b** (98 bytes — −16% vs v1):
```
@1<12'hot'@1>8
```

**compact_v2** (97 bytes — −16% vs v1):
```
1,2'hot'4,5
```

**compact_v3** (85 bytes — −27% vs v1):
```
1,2hot4,5
```

### Onde cada simplificação ganha

| Simplificação | Economia em D2-mini | Onde |
|---|---:|---|
| Remover `@N:` (v1 → v1b) | 18 bytes (16%) | 4 linhas de decl × ~5 chars cada |
| Materializar quebras (v1 → v2) | 19 bytes (16%) | Refs viram idx curtos em vez de `@N<K` |
| Tirar aspas dos literais (v2 → v3) | 12 bytes (12%) | 9 literais sem aspas + 4 `*` separadores |
| Total v1 → v3 | 31 bytes (27%) | acumulado |

## Análise do impacto de cada decisão

**1. Prefixo `@N:` da decl (v1 → v1b)**

Custa 3-5 chars por linha de decl. Removido sem perda:
- O decoder conta as decls em ordem; cada uma vira eid+1
- Conflito potencial: como distinguir decl de uso (`=N`)?
- Solução: linhas começando com `=` ou dígito são usos; resto
  é decl

**2. Quebras explícitas em fragmentos (v1 → v2)**

Substitui `@N<K` (4-5 chars) por idx (1-3 chars + `,` quando
sequência). Ganha quando refs apontam para poucos slices
distintos (poucas quebras por nó). Perde quando há muitos
slices sobrepostos (exp 22 viu iso-N1000 +86%).

**3. Aspas implícitas (v2 → v3)**

Em D2-mini e D2-completo, **nenhum literal contém dígito**. A
transição entre refs (dígitos+vírgulas) e literais
(não-dígitos) é detectada automaticamente. Aspas eram
redundância pura — 2 bytes por literal × N literais.

## Limitação crítica de v3

**v3 só funciona quando literais não contêm dígitos.** Em datasets
do regime A:

| Dataset | Literais têm dígitos? | v3 funciona? |
|---|---|---|
| D2-mini, D2-completo | não | **sim** |
| urls (`00042`, `2026-0001`) | sim | **não** |
| iso (`08:00:00Z`) | sim | **não** |
| ips (`192.168.1.10`) | sim | **não** |
| codigos (`PED-2026-00001`) | sim | **não** |
| uuids (hex) | sim | **não** |
| cpfs (dígitos) | sim | **não** |

Em todos os outros datasets, v3 quebraria — o parser confundiria
dígitos do literal com refs.

Para cobrir o regime A, seria preciso uma **v4** com:
- **Escape `\` antes de dígitos no literal**, OU
- **Aspas só quando ambíguo** (literal com dígitos)

Ambas as opções têm custo: cada char escapado/aspado custa 1
byte. O ganho líquido de v3 → v4 dependeria da densidade de
dígitos nos literais.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-23-syntax-variations
python run.py
```

3 tabelas + roundtrip 10/10 + TCFs lado a lado em D2-mini.

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. **v3 é a melhor sintaxe nesses 2 datasets**: −27% vs v1, −59%
   vs verbose
2. **v1b é uma melhoria barata sobre v1** (−16%) sem mudar
   filosofia
3. **As simplificações são ortogonais**: v1b (sem `@N:`) é
   compatível com v2 (idx por fragmento) — poderia haver v2b/v3
   sem o `@N:` análogo
4. **v3 tem limitação séria**: não cobre datasets com dígitos
   em literais. Precisa v4 com escape ou aspas condicionais
5. **Próxima direção**: implementar v4 (cobre regime A) ou
   escalar v3 para os 21 datasets onde funciona
