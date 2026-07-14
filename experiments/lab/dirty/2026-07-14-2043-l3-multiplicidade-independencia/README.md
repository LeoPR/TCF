# Lab 2026-07-14-2043 — L3: multiplicidade EXPLÍCITA vs DEDUZIDA (independência × bytes)

**Status**: pesquisa/medido, sintético. **Ticket**:
[T-CODE-TCF8H-WELD](../../../../tickets/T-CODE-TCF8H-WELD.md) ·
[tcf-camadas-arquitetura](../notas/tcf-camadas-arquitetura.md) (L3).

Testa a hipótese do owner (2026-07-14) sobre o trade do **L3** (otimização pela
hierarquia): mesmo a hierarquia dizendo que o pai **não precisa expandir**, o
**NÚMERO** (multiplicidade) pode ser necessário. Duas formas:

- **EXPLÍCITA** (o `#count` do weld, ou a marcação `*N|`): cada bloco se basta →
  **assíncrono/paralelismo total**; a estrutura é separável do dado (lazy).
- **DEDUZIDA** (pai repete + RLE; a multiplicidade sai do run do pai): **menos bytes**,
  MAS a montagem tem que **ler o dado do pai** e agrupar → as colunas **se conversam**
  → menos independência.

## Medido (RT-exato da forma explícita = o weld)

Bytes por LARGURA do registro (nº de campos-pai `K`), 6 registros:

| K | explícita (#count) | deduzida (tabelão) | Δ | só o count | vence |
|---:|---:|---:|---:|---:|---|
| 1 | 192 | **163** | +29 | 20 | deduzida (−bytes) |
| 2 | 239 | **223** | +16 | 20 | deduzida (−bytes) |
| 4 | **333** | 343 | −10 | 20 | **EXPLÍCITA** (Pareto) |
| 8 | **521** | 583 | −62 | 20 | **EXPLÍCITA** |
| 16 | **909** | 1069 | −160 | 20 | **EXPLÍCITA** |

## Veredito (a hipótese é verdade... só num nicho)

1. **"Independência custa bytes" vale SÓ para registro ESTREITO** (K=1–2): aí a deduzida
   economiza a coluna de count. Crossover ~K=3.
2. **Para registro LARGO (K≥4, o comum em transmissão** — cadastro é largo), a EXPLÍCITA é
   **PARETO-melhor: MENOS bytes E MAIS independência**. Porque a deduzida paga o `*N|`
   repetido em CADA coluna-pai; a explícita paga **1 count só** (20 B, constante, seq-RLE'd).
3. **A dependência caracterizada**: EXPLÍCITA → a montagem lê 1 coluna de controle DEDICADA
   e minúscula (count); as colunas de DADO decodificam INDEPENDENTES (paralelismo) e dá pra
   ler a ESTRUTURA sem materializar o dado (**lazy-friendly, como o `view()`**). DEDUZIDA →
   a montagem decodifica a coluna de DADO do pai e analisa runs → estrutura ENTRELAÇADA com
   dado → bloco-filho DEPENDE do bloco-pai → menos assíncrono.

## Mitigação

O "imposto de independência" (a coluna de count) é **minúsculo e constante** (20 B, seq-RLE) —
não é gargalo. Logo o default do weld (`#count` EXPLÍCITO) é o certo: independência
**quase-grátis** no caso comum, e ainda dá o bônus lazy (estrutura sem dado). O "cobertor
curto" vira um **PARÂMETRO** só para o nicho estreito+min-bytes.

## Otimização — DEIXAR PRO FIM (owner)

Como o owner pediu (soldar em etapas, otimizações no fim): registrar, não implementar agora.
- **H-L3-MULTIPLICITY-01**: knob `multiplicity='explicit'|'deduced'` (independência × −bytes no
  nicho estreito); OU `min()` por documento (como o FLOOR das natures). Confiança: Média
  (sintético, forma).

## Rodar

```powershell
python experiments/lab/dirty/2026-07-14-2043-l3-multiplicidade-independencia/study.py
```

Usa o `encode_hierarchical` weldado (read-only) p/ a forma explícita; a deduzida é medida com
`encode` por-coluna. Zero mudança em `src/tcf`. Ver [result.md](result.md).
