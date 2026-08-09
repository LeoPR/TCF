# Os dois designs do alvo DELTA — custo real e qual é o barato

**2026-08-09 · nota de design. Nenhum byte de `src/tcf` mexido.**
Evidência: lab [`2026-08-09-0042-data-alvo-delta`](../../2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/)
(`result.md` = placar; `design_probe.py` = a sonda que fundamenta esta nota).

O owner pediu: *"mostre o próximo com os designs para analisarmos, pegue um que, talvez,
seja barato implementar"*. **O barato é o seq-RLE periódico — e é também o de maior
ganho.** Isso não costuma acontecer junto; a razão está no §1.

---

## 1. A correção que muda a conta: `!!` não é rota raw, é POLARIDADE

O `result.md` do lab `0042` afirmou que o periódico precisaria de um "espelho raw" porque
o candidato de data roteia pra `#TCF.8!!` com linhas de dígito **sem** escape. **Errado.**
O `!!` é o **sufixo de polaridade** (weld 2026-07-26), camada de *borda* aplicada depois de
tudo (`encoder.py:459`, `sufixo, body = polariza(body)`). Medido:

```
pré-polaridade  (o que o compact_body enxerga)   *3+1|7\3      \7396*\1*\7
pós-polaridade  (o que eu estava lendo)          *3+1|7!3      !7396*1*7
```

Consequência prática: o periódico mora **dentro do `compact_body`**, no mundo escapado,
onde `compare_for_seq` e `shift_escape_digits` já servem — **sem espelho novo, sem
primitiva nova**. Eu estava medindo de fora do encoder, e de fora o mundo parece raw.

> Classe de erro conhecida nesta casa: é a mesma da "âncora de pin" do EXP-016 e do
> baseline do FLOOR da nature — **medir o artefato emitido em vez do ponto de decisão**.
> Registrada de novo porque reincidiu.

---

## 2. Design A — seq-RLE PERIÓDICO (a ideia do owner)

**O que é.** O marcador aceita delta que *cicla* entre linhas:
`*N~d1,…,dp|template`. Hoje existe uniforme-entre-linhas (`*N+d|`) e per-run-dentro-da-
linha (`*N+d1,d2,…|`, ADR-0016); o ciclo entre linhas não existe.

**Onde mexe.** Um arquivo: `src/tcf/composicional/hcc_seqrle.py`.

| ponto | o que muda | tamanho |
|---|---|---|
| `detect_seq_runs` (irmã nova) | acha o período `p` de maior economia | ~35 linhas |
| `compact_body` | emite `*N~…\|` e delega o resto ao caminho de hoje | ~20 linhas |
| `expand_seq_marker` | reconhece `~` e cicla o padrão | ~15 linhas |
| `_contador_declarado` (teto/E3) | **nada** — já lê `*600~…` certo (verificado) | 0 |
| FLOOR por corpo | **nada** — já existe (`hcc_seqrle.py:329`) | 0 |

Nada de protocolo, header, registry, decoder-dispatch ou API. **Simetria encode/decode no
mesmo arquivo** — que é exatamente a forma E1/E2 que o `.8` privilegia.

**Medido pela sonda (camada trocada por monkeypatch, `encode`/`decode` REAIS):**

| caso | hoje | com periódico | fator |
|---|---:|---:|---:|
| dias úteis n=600 | 1590 | **40** | 39,8× |
| dias úteis n=6000 | 15630 | **41** | 381× |
| ids de turno (**não-data**, sem nature) | 1959 | **32** | 61× |
| úteis + feriado mensal | 1889 | 677 | 2,8× |
| diário / semanal / texto / ruído alta-card | — | **byte-idêntico** | 1,0× |

**Os dois gates, byte-idênticos com a camada ligada:**

| gate | congelado | com periódico |
|---|---:|---:|
| D1-D9 sintéticos | 1545 | **1545** ✔ |
| real-world (retail ×2 + lineitem) | 89430 | **89430** ✔ |

**E3 verificado:** o decoder de HOJE diante do wire novo **falha alto**
(`contador RLE invalido: '600~1,3,1,1,1'`) — nunca devolve dado errado calado.
**E1 adversarial verificado:** valores que *imitam* o marcador
(`"*600~1,3,1,1,1|739617"`, `"*3~1,2|z"`, `"a|b"`) fazem RT — a heurística de separador
do ADR-0007 já protege.

### Os dois defeitos que a sonda pegou (e que o weld tem de nascer com eles resolvidos)

1. **Padrão uniforme disfarçado.** O greedy emitia `*600~1,1|` (período 2 de deltas
   iguais) para dados uniformes — o `*N+1|` de hoje faz por menos. Sem a guarda, o
   diário piorava 32 → 34 B. **Guarda: rejeitar `len(set(pad)) == 1`.**
2. **FLOOR contra o baseline errado.** Comparar o candidato periódico com o corpo **cru**
   fazia ele "vencer" e piorar 4 de 8 casos (ruído alta-card 203 → 253), porque ganhava do
   cru e perdia do uniforme. **Guarda: `min(cru, compactado_de_hoje, periódico)`.** É
   literalmente a mesma classe do fix de baseline do FLOOR da nature (2026-08-08) — a
   terceira vez que este projeto tropeça em *comparar com o baseline que o encoder não
   emitiria*.

Com as duas guardas: zero regressão em todos os controles e nos dois gates.

### O que fica em aberto (não bloqueia, mas é decisão de weld)

- **Sintaxe.** O `~` é PROVISÓRIO: a vírgula já é do multi-delta per-run (ADR-0016) e `~`
  é operador composicional em outro contexto. Não houve colisão nos testes, mas a escolha
  final é sua — alternativas: outro char, ou `*N*p+d1,…|` com período explícito.
- **Escopo.** A sonda restringe a pares de **um** run de escape-digit (ordinal/id — o caso
  que importa). Multi-run periódico é produto cruzado com o ADR-0016 e fica de fora do 1º
  weld, registrado.
- É **format change** (`#TCF.8`), com ADR.

---

## 3. Design B — transform de COLUNA (delta-coluna)

**O que é.** A nature deixa de ser só per-valor e passa a transformar a coluna:
`[1º ordinal absoluto, depois deltas]`.

**Onde mexe** — e é aqui que ele fica caro:

| ponto | o que muda |
|---|---|
| protocolo das natures | `encode_value`/`decode_value` (per-valor) ganha irmão `encode_column`/`decode_column`. **Contrato que as 4 specs existentes implementam** |
| `encoder.py:385` | `pairs = [encode_value(nature, v) …]` vira dois caminhos |
| decoder | dispatch novo para desfazer o transform de coluna |
| header/registry | tag distinta (`:data-delta`) — o spec vira dois, ou um com dois alvos |
| semântica nova | delta **em relação ao último válido**, com literal no meio; null; o 1º elemento é absoluto e os outros não |
| pré-requisito | `T-NATURE-CANDIDATO-BN` (weld separado, aguarda aprovação) — sem ele os 345–644 B do delta-coluna não existem |

**Vale o que ele promete** (mensal 1085 → 349, quinzenal 3951 → 349, espalhado-ordenado
4059 → 644, e robusto a ruído: 345–353 B sob todas as variações). Mas é **transversal**:
mexe no contrato que todas as natures implementam, no decoder e no registry — e depende de
outro weld antes.

---

## 4. Recomendação

**Fazer o Design A (periódico) primeiro.** Não é só o mais barato — é o único que:

- cabe em **um arquivo**, com encode e decode espelhados lado a lado;
- **não** depende de nenhum outro weld;
- vale pra **qualquer coluna numérica** (ids, contadores, timestamps), não só data — o
  ganho de 61× apareceu numa coluna que nem passa por nature;
- já provou **zero movimento nos dois gates byte-canonical**, que é o risco real de mexer
  no core.

O Design B continua de pé e continua complementar (ganha onde o ciclo não é exato) — mas
ele é uma mudança de **protocolo**, e o `T-NATURE-CANDIDATO-BN` vem antes dele de
qualquer forma. Ordem sugerida: **A** → (aprovação do) `T-NATURE-CANDIDATO-BN` → **B**,
cada um medido no seu lab.

### Se o A for aprovado, o que eu faria (nesta ordem)

1. ADR do marcador (sintaxe decidida por você) + escopo single-run explícito.
2. Weld em `hcc_seqrle.py` com as **duas guardas** do §2 desde a primeira linha.
3. Testes: os 8 controles da sonda + os adversariais de colisão + os dois gates.
4. Lab de confirmação no clean, no molde do EXP-016.

**Nada disso começa sem seu OK** — `src/tcf` exige aprovação explícita.
