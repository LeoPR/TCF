# Resultado — Sub-exp 03 (H-DA-04 cadence-break recovery)

**Data**: 2026-05-17
**Estado**: concluido (Fase 1+2; Fase 3 NAO executada — decidiu-se nao implementar)
**Plano**: [README.md](README.md)
**Audit completo**: [audit.md](audit.md)

## Conclusao executiva

**H-DA-04 refutada na forma pura (HCC sozinho).** O ganho residual
tratavel por extensao de detector e' **6 bytes total** (1 par em
D11b). Os 299 bytes residuais em Type B exigem cooperacao de OBAT
(H-DA-02) ou grammar nova — fora do escopo "HCC sozinho".

## Audit (Fase 1)

Classificacao de pares consecutivos NAO-compactados no body fork
da tentativa 02:

| Tipo | Criterio | Bytes residuais (D11a-h) |
|---|---|---:|
| A | Mesmo length, diffs todos digit | **6** |
| B | Lengths diferem, alguma sobreposicao | 299 |
| C | Lengths diferem, pouca sobreposicao | 50 |

## Analise do Type A (6 bytes — desistir)

Unico caso: D11b linhas 13-14 — `38,30` → `38,34` (Δ=+4).

Por que o detector atual NAO pegou? Meu `compare_for_seq` exige
ao menos uma escape-digit position. `38,30` nao tem escape — todos
os digits sao ref-ids.

Pra capturar: precisaria detector que aceita ref-digits varying +
sintaxe que indica QUAIS digits shiftar (ex: `*N+delta@pos|template`).

**Custo/beneficio**: complexidade significativa pra 6 bytes em 1
caso edge. **Nao implementar.**

## Analise do Type B (299 bytes — fora de alcance HCC sozinho)

Pares onde lengths diferem. Subdivido em:

### B.1 — Linha 1 vs linha 2 (todos datasets)

Exemplo D11d: `\2026-\05-\15 \09:*\0*\0*:\00` (29) vs `1~2\1*4` (7).
- Linha 1 = primeira declaracao (literais com escape)
- Linha 2 = primeira ref ja' usa frags da linha 1
- **Nunca compactaveis**. Estruturas fundamentalmente diferentes.

### B.2 — Pares post-transicao (D11d-h e D11e)

Exemplo D11d:
- Linha 4 (orig s11 = minuto 10): `1\1*3,4`
- Linha 5 (orig s12 = minuto 11): `1~15,6,4`
- Linha 6 (orig s13 = minuto 12): `16,7,4`

Estes correspondem a strings semanticamente sequenciais
("2026-05-15 09:10:00", "...11:00", "...12:00") mas com bodies
estruturalmente diversos. Causa raiz:

1. OBAT escolhe LCP/LCS greedy a cada string
2. s11 muda P de 15 pra 14 (carry na transicao 9→10) e S de 3 pra 4
3. s12 ja' nao referencia s1 mais — referencia s11 como nova base
4. s13 reusa o virtual ref criado em s12 → estrutura menor ainda

Cada linha "vira sua propria coisa". Body grammar atual nao permite
expressar "linha N e' modificacao incremental de linha N-1".

**Caminho para resolver Type B post-transicao**:
- OBAT precisa **manter shape** atraves da transicao (escolha
  nao-greedy, exigiria hint cadencia)
- Isto e' H-DA-02 (dica generica calibrando OBAT)

### B.3 — Outros (D11a, D11c, D11e)

Padroes proprios de cada dataset, todos requerem grammar/OBAT
cooperation. Excluidos do escopo H-DA-04.

## Analise do Type C (50 bytes — fora de alcance)

Pares totalmente diferentes ou com diffs em chars nao-digit. Nao
ha' caminho via extensao HCC.

## Decisao registrada (Fase 2)

**NAO implementar Fase 3** (extensao do detector). Razoes:

1. Type A residual (6 bytes) nao justifica complexidade adicional
   (marker mais rico, decoder mais complexo)
2. Type B residual (299 bytes) requer mudancas arquiteturais
   que violam principio "HCC sozinho"
3. O grande ganho residual em Type B aponta diretamente pra
   **H-DA-02** (hint-guided OBAT) — sub-exp futuro mais focado

## Status H-DA-04 no roadmap

`refutada (com grammar atual) — PARCIAL`

Justificativa: HCC sozinho com extensao razoavel captura **6 bytes**.
O residual maior (299 bytes Type B) requer cooperacao de OBAT
(H-DA-02) ou primitives gramaticais novas.

### Refinamento (2026-05-17, pos sub-exp 05)

Sub-exp 05 (H-DA-06 em D16a) revelou que esta refutacao e' **parcial**:
- H-DA-04 e' refutada SOMENTE no caso com refs estruturais ao
  redor do varying lit (estrutura `P+L+S` do D11d)
- Quando o varying part e' o STRING INTEIRO (sem refs), o
  seq-RLE atravessa transicoes naturalmente porque trata
  escape-digit runs como inteiros: `int("109")+1 = 110`
- D16a (100..112) compactado em **1 unica linha** `*13+1|\100`
  pelo HCC fork SEM precisar de OBAT cooperar

Roadmap atualizado: H-DA-04 status = `refutada parcial`.

Ver `05-numeric-ids-h-da-06/result.md` pra detalhes.

## Hipotese decorrente

**Observacao nova durante este audit** (registrar no roadmap):

Type B pares post-transicao tem padrao consistente em D11d/e/f/g/h:
sempre 3 linhas pos-transicao com bodies `R\L*R,R` → `R~R,R,R` →
`R,R,R`. Esta consistencia sugere que se OBAT mantivesse a shape
P+L+S atraves da transicao (escolhendo nao-greedy), as 3 linhas
seriam compactaveis pelo seq-RLE existente.

**Quantificacao se H-DA-02 funcionar**: estimar ~150 bytes
recuperaveis (~50% do residual Type B), porque so' os pares
post-transicao em datasets com cadencia regular ficam dentro do
alcance. Bordas (D11b) nao se beneficiam.

## Implicacoes pra proximas tentativas

- **H-DA-02 (sub-exp 04?)** ganha relevancia concreta. Antes era
  exercicio conceitual; agora tem alvo mensuravel (~150 bytes
  residuais quantificados).
- **H-DA-03 (OBAT relativo)** continua especulativa — sem evidencia
  empirica que adicione ganho sobre H-DA-02
- **H-DA-06 (outros deltas)** continua aberta — testa generalidade
  do que ja' temos em dataset diferente (numerico)

## Arquivos gerados

```
03-cadence-break-recovery/
├── README.md          (plano)
├── audit.py           (auditor que classifica pares + emite outputs)
├── audit.md           (sintese top-level — tabelas e detalhes resumidos)
├── result.md          (este — conclusao + decisao)
└── outputs/<dataset>/
    ├── body-fork-analyzed.tcf   (copia do input da tentativa 02, auto-contida)
    ├── pairs-detailed.md         (cada par nao-compactado em detalhe:
    │                              a, b, diff marker `^`, justificativa,
    │                              caminho-pra-tratar; Type A inclui
    │                              digit_runs + delta + nota)
    └── residual-stats.txt        (numerico — count + bytes por tipo)
```

**Sem implementacao de novo encoder/decoder** — sub-exp 03 e' analitico
(audit). Outputs sao do tipo "inspecao da analise", nao bodies novos.
A conclusao "nao implementar Fase 3" e' justificada nos arquivos acima.

## Como inspecionar (auto-verificacao)

Pra reproduzir/validar este sub-exp:

1. **Rodar**: `cd 03-cadence-break-recovery && python audit.py`
2. **Validar audit**: comparar `audit.md` com summary impresso no stdout
3. **Inspecionar caso a caso**: cada `outputs/<ds>/pairs-detailed.md`
   mostra o body inteiro (com `*` marcando linhas ja' compactadas) e
   cada par nao-compactado com diff marker
4. **Conferir Type A**: D11b linhas 13-14 (`38,30` → `38,34`, Δ=+4)
   e' o unico caso. Inspecionar
   [`outputs/D11b-datas-borda/pairs-detailed.md`](outputs/D11b-datas-borda/pairs-detailed.md)
   secao "Par linhas 13-14"
5. **Conferir Type B post-transicao**: D11d linhas 4-5 e 5-6 (e
   similar em D11e/f/g/h). Estes sao os alvos de H-DA-07 estimados
   em ~150 bytes recuperaveis.
