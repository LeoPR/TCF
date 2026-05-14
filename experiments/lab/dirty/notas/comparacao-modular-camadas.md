# Comparacao modular — camadas e expansoes

**Data**: 2026-05-13
**Tipo**: nota teorica transversal (estrutural, vale para todos os macros)
**Contexto de origem**: discussao no M4 sobre limites de deteccao greedy
e busca de padroes. User levantou que comparacao "menos binaria"
poderia ser modular em multiplas camadas. Tambem pediu nome formal
para o alg16 ("ele parece ter ficado muito resistente e bem
consolidado").
**Conecta com**: [`2026-05-11-comparacoes-nao-literais.md`](2026-05-11-comparacoes-nao-literais.md)
(delta/aproximacao), [`2026-05-11-tipos-com-estrutura.md`](2026-05-11-tipos-com-estrutura.md)
(estruturais), [`quebra-de-linha-como-marcador.md`](quebra-de-linha-como-marcador.md)
(marcadores como dimensao opcional).
**Status**: registrada como direcao arquitetural. **Nao acionavel
imediatamente** — fica como guia pra protótipo e macros futuros.

## Nome formal para o alg16

O algoritmo cristalizado em
[`M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py`](../M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py)
(e copiado em M1/M2/M3/M4) ficou estavel e resistente a varios
ataques empiricos (M1 a M4). Vale dar nome formal para citar como
componente do TCF.

**Sugestoes** (a confirmar com user):

| Nome | Significado | Pro / contra |
|---|---|---|
| **TCF-CORE** | algoritmo nuclear do TCF | claro, generico |
| **Online Affix Search (OAS)** | online + busca de afixo (pref/suf) | descritivo, tecnico |
| **TCF-OAS** | combinacao | mais especifico |
| `online` (atual) | manter informal | familiar mas nao formal |

Recomendacao: **TCF-CORE** para citacao em artigos/notas; **OAS**
para descricao tecnica do algoritmo dentro do prototipo.

## Tese central — comparacao como parametro modular

Atualmente toda comparacao no TCF-CORE e' **literal byte-a-byte**:

```python
# online.py
def lcp_len(a: str, b: str) -> int:
    while i < n and a[i] == b[i]:  # ← igualdade literal hard-coded
        i += 1
```

E em descritores (M1.E range, M2.A sufixo, M4.C1' subseq):

```python
contagem[tuple(refs[a:b])] += 1  # ← igualdade literal hard-coded
```

**Hipotese**: tornar a comparacao um **parametro** abre extensoes
sem mexer no nucleo.

## Camadas onde a comparacao aparece

Comparacao aparece em PELO MENOS 2 camadas distintas no TCF:

### Camada A — Algoritmo (TCF-CORE / OAS)

Decide pref/suf comum entre strings:
```
a vs b  →  LCP(a, b), LCS(a, b)
```

### Camada B — Descritores / sintaxes (M1.E, M2.A, M4.C1', etc)

Detectores de padroes nas refs serializadas:
```
run_atual vs runs_anteriores  →  contagem global
sub_atual vs sub_anteriores   →  contagem global
```

## Comparacao modular — taxonomia possivel

| Modo | Lossless? | Onde encaixa | Exemplo |
|---|---|---|---|
| **literal** (atual) | sim | A e B | `a == b` byte-a-byte |
| **relativo / delta** | sim (se delta exato) | A pre-transformacao, B detector | datas, IDs sequenciais |
| **aproximado / tolerancia** | nao | apenas Shaper opt-in | numericos com ε |
| **estrutural** | sim | A pre-transformacao | CPF, UUID, IP (separadores deduziveis) |

Notas:
- **Literal** e' default e cobre 90% dos casos.
- **Delta** ja' explorado em Mobsolete (`2026-05-09-delta-datas/`).
  Lossless se delta e' exato. Cabe como pre-transformacao por coluna.
- **Aproximado** e' lossy — fora do contrato atual do TCF (lossless).
  Encaixa em Shaper ou modo opt-in declarado.
- **Estrutural** mapeia tipos conhecidos (CPF, UUID) com mascara
  fixa. Reduz info armazenada. Pre-transformacao por coluna.

## Por que registrar agora

Surge na conversa do M4 enquanto avaliamos M4.C1' (subsequencias com
idx implicito). Limite teorico (114B) so' parcialmente atingido
(35%). Suspeita: greedy nao resolve combinacoes; comparacao mais
flexivel (estrutural, delta) poderia capturar padroes que comparacao
literal nao ve.

**Mas e' direcao futura, nao acionavel agora**:
- Modos relativo/aproximado/estrutural sao **pre-transformacoes**
  ortogonais ao TCF-CORE
- Para implementar, precisariamos definir contrato: como o decoder
  sabe que coluna sofreu qual transformacao? Header? Por coluna?
- Cabe no prototipo, nao no dirty

## Implicacao para protótipo

Quando partir do dirty para prototipo, considerar:

1. **TCF-CORE puro** = algoritmo lossless byte-a-byte (alg16
   intocado)
2. **Camada de pre-transformacao por coluna** opcional:
   - `δ` para colunas numericas/datas → output e' coluna delta
   - `mask` para tipos estruturais → output e' coluna sem
     separadores
3. **Camada de pos-transformacao no decoder** desfaz a pre-tx

O TCF-CORE NAO MUDA. Camadas sao plugins.

## Implicacao para macros futuros do dirty

Se houver tempo/interesse antes do prototipo, vale 1 experimento
de pre-transformacao para validar a arquitetura:

- **Macro M5 (sugestao)**: pre-transformacao + TCF-CORE
  - M5.A: delta encoding em coluna de IDs sequenciais
  - M5.B: mask de separadores em UUID/CPF
  - Mede ganho vs TCF-CORE direto
  - Confirma viabilidade do contrato

Mas isso requer **dataset com esses tipos** (D1-D4 nao tem). Pode
ser feito em `data_extra/` se valer.

## Conexoes

- [[2026-05-11-comparacoes-nao-literais.md]] — registra delta como
  pre-tx (origem da ideia)
- [[2026-05-11-tipos-com-estrutura.md]] — registra estrutural como
  pre-tx (origem da ideia)
- [[quebra-de-linha-como-marcador.md]] — marcadores tambem
  modulares
- [[../2026-05-13-M4-desfragmentacao-arvore/notas/buffer-e-refragmentacao.md]] —
  conversa que motivou a sintese
- [[../2026-05-13-M4-desfragmentacao-arvore/notas/arvore-da-arvore-vs-regex.md]] —
  busca de padroes vs regex

## Resumido em 1 linha

"TCF-CORE (alg16) e' lossless byte-a-byte. Comparacao modular
(literal/delta/estrutural/aprox) cabe como pre-tx ortogonal — nao
muda o nucleo, abre extensoes no protótipo."
