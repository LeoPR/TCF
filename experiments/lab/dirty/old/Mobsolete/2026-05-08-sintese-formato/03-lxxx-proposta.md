# Proposta — novos formatos Lxxx

Como a regra unificada elimina os "níveis discretos" L0/L1/L2/L3, a
nomenclatura de níveis precisa ser repensada. Proposta abaixo.

---

## Princípio

"Nível" deixa de ser **modo de codificação** e vira **conjunto de features
ativadas**. O encoder sempre roda a mesma regra; o nível só diz quais
extensões/parâmetros estão habilitados.

Cada feature é uma **letra-flag**:

| Flag | Significado | Default |
|---|---|---|
| `S` | Sort aplicado (com chaves declaradas) | desligado (ordem fonte) |
| `R` | RLE habilitado | **ligado em produção** |
| `D` | Dict implícito habilitado | **ligado em produção** |
| `M` | Discriminação automática (bare/marcado) | **ligado** |
| `δ` | Delta encoding por coluna | desligado |
| `P` | Prefix elision por coluna | desligado |
| `L'` | Line-RLE (layout alternativo) | desligado |
| `K` | Count-recycling (streaming) | desligado |

Combinação de flags = "nível" do arquivo.

---

## Hierarquia proposta (Lxxx)

### L0 — Mínimo absoluto (ablação literal)
```
flags: nenhum
encoding: literal puro
uso: baseline científico, debug
```

### L1 — RLE puro (ablação histórica)
```
flags: R
encoding: literal + RLE
uso: ablação para comparar com regra unificada
```

### L2 — Dict puro (ablação histórica)
```
flags: D
encoding: literal + dict implícito (sem RLE)
uso: ablação
```

### L3 — Regra unificada
```
flags: R + D + M
encoding: literal + RLE + dict + auto-discriminação
uso: PRODUÇÃO (default)
```

### L3+S — Regra unificada com sort
```
flags: S + R + D + M
encoding: L3 + ordem aplicada
uso: produção quando há colunas correlacionadas
```

### L4 — L3+S com 1 extensão
```
flags: S + R + D + M + (δ ou P)
uso: dataset com 1 padrão estrutural extra
exemplo: timestamps + outras colunas normais
```

### L5 — L3+S com múltiplas extensões
```
flags: S + R + D + M + δ + P
uso: dataset com múltiplos padrões estruturais
```

### L6 — Layout alternativo
```
flags: L' (substitui column-major)
encoding: line-RLE para datasets com linhas duplicadas inteiras
uso: logs, eventos com repetições exatas
```

### L7 — Streaming
```
flags: S + R + D + M + K
uso: stream de longa duração com cardinalidade rotativa
```

---

## Nomenclatura compacta no header

Em vez de declarar `# TCF v0.5 lv=L3+S`, usar a string de flags:

```
# TCF v0.5 flags=SRDM sort=valor,produto,qty
```

ou ainda mais compacto:

```
# TCF v0.5 SRDM sort=valor,produto,qty
```

Onde a sequência alfabética de letras-flag torna o "nível" auto-explicável.

### Vantagens da notação flags

1. **Composicional**: posso adicionar `δ` ou `P` sem renumerar Lxxx.
2. **Auto-documentável**: ler o header já revela features. Não precisa
   tabela de níveis.
3. **Suporte a ablação**: experimentos científicos declaram explicitamente
   `flags=R` (só RLE) ou `flags=D` (só dict) sem ambiguidade.
4. **Default sensato**: ausência de header = `flags=RDM` (produção),
   sort=∅, ext=∅.

---

## Tabela cruzada Lxxx ↔ flags

| Lxxx | Flags | Significado curto |
|---|---|---|
| L0 | ∅ | literal apenas (ablação) |
| L1 | R | literal + RLE (ablação) |
| L2 | D | literal + dict (ablação) |
| **L3** | **RDM** | **regra unificada (produção default)** |
| L3+S | SRDM | + sort |
| L4δ | SRDMδ | + delta |
| L4P | SRDMP | + prefix |
| L5 | SRDMδP | + ambos extensões |
| L6 | L'RDM | line-RLE |
| L7 | SRDMK | streaming com reciclagem |

A nomenclatura Lxxx é **opcional** — só serve para nomear pacotes comuns
em conversas e papers. O header usa flags diretas.

---

## Compatibilidade com TCF v0.4

### Mapeamento das versões antigas

| TCF v0.4 lv | Equivale em v0.5 | Observação |
|---|---|---|
| `lv=0` | `flags=∅` (L0) | literal puro |
| `lv=1` | `flags=R` (L1) | RLE puro |
| `lv=2` | `flags=SR` (L1+S) | sort + RLE |
| `lv=3` | `flags=SRD` (L3+S sem M) | dict explícito → implícito |

A migração v0.4 → v0.5 troca:
- `# TCF v0.4 lv=2` → `# TCF v0.5 SR sort=<col>` (ou só `R` se sort não
  declarado)
- `# TCF v0.4 lv=3` + bloco `# dict <col>: ...` → `# TCF v0.5 SRDM`
  (dict explícito desaparece; vira inline no corpo)

Decoder v0.5 lê v0.4 também (parsing tolerante). Encoder v0.5 prefere
escrever no formato novo.

---

## Como o encoder escolhe o "nível"

Em produção, **sempre L3 + S** (`flags=SRDM`). O encoder:
1. Analisa as correlações entre colunas
2. Decide chaves de sort (multi-key se necessário)
3. Aplica regra unificada com auto-discriminação

O usuário pode forçar:
- Mais features (`flags=SRDMδP`) se sabe do dataset
- Menos features (`flags=R` para ablação)
- Layout alternativo (`flags=L'RDM`)

Mas o **caminho-feliz** é deixar o encoder decidir.

---

## Próximas mesas (depois desta síntese)

A síntese fecha a pergunta "qual o formato base de compressão?".
Pode-se voltar para:

1. **Mesa de extensões** — testar δ, P, L' em datasets onde brilham.
   Validar empiricamente que cada extensão paga seu overhead.

2. **Mesa de header** — refinar a notação compacta:
   - `flags=SRDM` é claro?
   - Como declarar `discrim` por coluna?
   - Como declarar `sort` com tipo (numeric, lex, freq)?
   - Onde encaixar `# ext:` para δ/P por coluna?

3. **Mesa de quebra (chunks)** — agora que o formato base está fechado,
   voltar à pasta `2026-05-07-hipoteses-transporte` para definir como
   chunks adaptam o L3+S.

4. **Implementação experimental** — protótipo do encoder L3 unificado
   em Python, integrar no `src/tcf/`, validar bytes contra contagem
   manual desta mesa.

---

## Resumo executivo

> **Antes:** 12 variantes de codificação (C1-C12), 4 níveis discretos
> (L0-L3), múltiplas notações de header. Confusão.
>
> **Agora:** 1 regra (unificada) + 8 flags compositoriais + extensões
> ortogonais opt-in. O "nível" emerge das flags.
>
> **Domínio:** matematicamente, a regra unificada é ≥ qualquer combinação
> de RLE/dict/literal em qualquer escala. Comprovado por indução sobre
> formas arquetípicas de dados.
>
> **O que volta:** os antigos L0/L1/L2 ainda existem como flags-ablação
> para ciência. Em produção, sempre **L3+S** (`flags=SRDM`).
