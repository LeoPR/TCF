# ADR-0036 — bN de domínio: densidade por CARDINALIDADE

- **Status**: aceito (weld 2026-07-27)
- **Escopo**: single-col flat (`_lista_flat`). **Fora**: rota tipada, `.8M`, `.8H`, spec, órfão.
- **Interage com**: ADR-0024 (baselines re-pináveis), ADR-0032 (discriminador),
  ADR-0035 (polaridade — o candidato irmão no mesmo `min()`).

## Contexto

Uma coluna de 200 valores `"0"`/`"1"` custava **609 B** — 2 literais e 198 referências de
linha (`^N`), ~3 B por linha. A mesma informação como `bool` nativo custava **47 B** (modo
denso `b1` + base64).

A diferença não é de conteúdo, é de **rota**: `list[str]` cai no `_lista_flat` e nunca chega
ao `_tipo_single_col`, onde o denso mora. E o denso é bool-**sem-null** por construção, então
`bool + null` também caía no core (546 B).

**A oportunidade é da cardinalidade da coluna, não do tipo Python da entrada.**

## Decisão

Com `k` valores distintos, bastam `w = ceil(log2(k))` bits por linha. O domínio viaja uma
vez; os índices viajam empacotados em base64.

```
#TCF.8                    #TCF.8B178
\0                        false
\1                        true
^1                        =CIhmASAEyQvAQQZokA
^2   …  (609 B)                 (57 B)
```

### Duas grafias, escolhidas pelo TRANSPORTE — não pelo tamanho

| | | |
|---|---|---|
| **`B`** | domínio **primeiro**, `=` abre os bits | **default** — streama nos dois lados |
| **`C`** | domínio por **último**, sem marcador | lote fechado — ~1 B menor |

O `C` é ~1 B mais barato e **venceria sempre num `min()` cego**. Mas ele **não streama**: o
leitor precisa do payload inteiro antes de emitir o primeiro valor — numa coluna de 2000
linhas, **1764 B de buffer contra 100 B**, 17× (lab `2211`). Trocar streaming por 1 byte, em
silêncio, seria a decisão certa tomada pelo critério errado.

Por isso **só o `B` é emitido por default**; o `C` fica **decodável** (wire de outra ponta lê
normalmente) e o opt-in de emissão é `T-BN-LOTE`.

### O marcador `=` e o escape

O `=` abre o bloco de bits; uma linha de **domínio** que comece com `=` ganha `\` na frente.
Isso é inequívoco porque **o core nunca emite `\` seguido de char fora de `* 0-9 \ ^ ~`** —
medido varrendo os 95 imprimíveis (lab `2231`).

Custo: **1 B** + 1 B por valor de domínio que comece com `=`. Em **145 colunas categóricas
reais** das fixtures, o segundo termo foi **zero**. O caso patológico é absorvido pelo FLOOR
externo: se o bN inchar, o core vence.

Alternativa considerada e descartada: marcador `\|` (imune por construção, 2 B fixos).
Break-even em 1 colisão; declarar qual dos dois foi usado custaria ≥1 B e comeria o ganho
(lab `2247`).

### `null` não é caso especial

É mais um valor do domínio, e ocupa o **slot 0** que o formato já reserva. A grafia do domínio
é a do core: `0` cru = null, `\0` = o literal `"0"`.

Essa assimetria — grafar mais do que se desfaz — já causou **4 bugs** no projeto (weld do slot
nulo, labs `2126`, `1608`, `2231`). `_le_grafia` desfaz exatamente `_grafa`, nem mais, e há
teste travando isso.

### Onde não se aplica

| | |
|---|---|
| `k ≤ 1` | o core já é ótimo com RLE (`*N\|valor` = 16 B); o bN nem se qualifica |
| `k > 256` | `w` passaria de 8 — fora do namespace |
| `n` pequeno | cabeçalho + domínio não se pagam; o FLOOR recusa sozinho |
| valor longo | o teto real é `k × len(valor)`, não `k` |

## Consequências

### Nenhum baseline moveu

D1-D9 **1545**, D17a **300**, real-world **89430** — inalterados. Nenhuma coluna dos gates tem
cardinalidade baixa o bastante para o bN vencer, o que confirma o FLOOR nunca-pior.

Suíte: **1042 passed, 3 skipped** (era 1010). Novo `tests/test_dominio_bn.py` (32).

### Reuso — quase nada é código novo

| peça | de onde |
|---|---|
| `pack_w` / `unpack_w` | `tcf/bitpack.py` — inclusive o fail-loud de payload curto e padding não-zero |
| domínio comprimido | `_encode_column` / `_decode_column` — o domínio é uma mini-coluna |
| garantia do marcador | a gramática de escape do core (`_escape_lit`) |
| ponto de inserção | o `min(candidatos)` que a polaridade já usa |

O `bitpack.py` já dizia no docstring: *"Larguras 1/2/4/8 (o namespace do `<modo>`); só w=1
(bool) é exercido agora"*. Este weld exerce de 1 a 8.

## Dois bugs corrigidos por auditoria adversarial (2026-07-28)

Rodei 4 lentes independentes sobre a proposta do `T-BN-TIPADO`. Elas acharam **dois defeitos
no código já soldado deste ADR**, os dois confirmados por mim rodando código.

### 1. `_grafa` não era injetiva — CORRUPÇÃO SILENCIOSA

```
_grafa("0")   ->  \0
_grafa("\0")  ->  \0      ← mesma saída, valores DIFERENTES
```

`encode(["\0", "x"] * 30)` devolvia `["0", "x", …]` — **sem exceção**, pela API pública, com
`list[str]` trivial. A rota core preservava, então era **regressão deste weld**, não limitação
do formato.

Causa: quem escapa tem de escapar também o próprio char de escape. A regra agora é *escapa o
`\` inicial **e** o `0` solitário; nada mais* — e há teste de injetividade.

É a **5ª aparição** da mesma família de assimetria no projeto.

### 2. O cabeçalho aceitava uma família infinita de grafias

`int(x, 16)` aceita zero à esquerda, maiúscula, underscore (PEP 515), prefixo `0x` e sinal;
`str.isdigit()` aceita dígito Unicode. Então `#TCF.8B20c8`, `#TCF.8B2C8`, `#TCF.8B2c_8`,
`#TCF.8B٢c8` — todos decodificavam igual ao canônico `#TCF.8B2c8`.

O **irmão no mesmo índice 7** (o modo denso) já rejeitava tudo isso, e
`test_typed_singlecol.py::test_grafia_nao_canonica_fail_loud` já travava o invariante
(*"duas grafias, mesmo valor, violaria S1.2"*). **O bN o violava.** Agora re-formata e
compara, como o irmão.

### 3. String vazia como ÚLTIMO valor do domínio

`bloco.rstrip("
")` comia **todos** os `
` finais, mas o corpo canônico termina em
exatamente um. `["a","b",""]` perdia o terceiro valor e o `decode` estourava. Falhava alto
(não corrompia), mas era **RT quebrado pela API pública**. Corrigido para `[:-1]`.

### 4. Conteúdo depois do bloco de bits, ignorado calado

Linha extra após o b64 era descartada em silêncio — o irmão no mesmo índice 7 **falha alto**
na mesma sonda. Agora também falha.

### Onde isto está analisado

A auditoria produziu **14 achados**; 4 eram bugs reais (os acima), 2 foram refutados por mim
rodando código, 1 era sobre a proposta e 1 virou ticket. A análise crítica — por que a mesma
assimetria de escape apareceu **5 vezes**, e por que o invariante de canonicidade existia,
era testado, e não foi aplicado ao módulo novo — está em
[`experiments/lab/dirty/notas/2026-07/2026-07-31-incidente-bn-4-bugs-e-a-analise-critica.md`](../../experiments/lab/dirty/notas/2026-07/2026-07-31-incidente-bn-4-bugs-e-a-analise-critica.md).

Suíte após as correções: **1061 passed, 3 skipped**; `test_dominio_bn.py` foi de 32 a 58
testes. Gates inalterados.

## Validação canônica de payload b64 — fonte única (2026-08-06/07)

`T-BN-B64-VALIDATE`. O `decode_bn` decodava o payload **sem nenhuma checagem**, vazando
`binascii.Error` cru. O lab `2026-08-06-2104` (9 sondas × 5 rotas, 45 células) mostrou que o
buraco era maior do que o ticket dizia:

- o **lazy `bB`** também tinha buraco — validava, mas não conferia tamanho, e aceitava
  `payload + "AAAA"` (bytes zero) em silêncio;
- havia **corrupção de valor** (o ticket dizia que não): trocar a caixa do último char muda
  valores em silêncio quando o payload tem bits mortos.

### As três checagens, e por que nenhuma é dispensável

```
1. validate=True        char fora do alfabeto, espaço, padding em lugar errado
2. re-codifica+compara  padding a mais, caixa trocada — grafia dupla dos MESMOS bytes
3. tamanho exato        extensão com bytes ZERO, truncamento
```

Medido: **nenhuma subsome as outras.** A (2) é a mesma técnica que o cabeçalho já usa para o
hex (`f"{n:x}" != nhex`) — canonicidade por re-emissão, em outro campo.

E a (2) é a **única que protege valor** (lab `2026-08-06-2250`): as outras duas só detectam
adulteração que devolveria valores corretos. Como as três juntas custam **< 1%** do `decode`,
não há trade-off a fazer — ficam ligadas, sem toggle.

### Fonte única

`dominio_bn.valida_payload_b64` é a única implementação. As três rotas com payload denso a
chamam: `decode_bn` (`B`/`C`), `_decode_lazy_bool` (`bB`) e `_decode_denso` (`b1`/`b2`) — este
último **fazia as checagens inline e serviu de modelo**; foi consolidado em 2026-08-07.

Deixar duplicado era a causa-raiz: o denso evoluiu, o bN e o lazy não, e a divergência só
apareceu por auditoria. `padded` distingue a forma canônica de cada rota (o denso emite com
`=`; bN e lazy sem).

Suíte **1135 passed**; `test_dominio_bn.py` 58 → 88. Gates inalterados — a mudança só toca
caminho de erro.

### Invariante de canonicidade: todo slot do domínio é referenciado

Varredura de fechamento (2026-08-07): os **dois modos** aceitavam calados uma entrada extra
no domínio — no `B` antes do marcador, no `C` no fim. O guard `len(dom) > 2^w` só pegava por
acaso, quando a largura não tinha folga.

`dominio()` monta a lista pela **primeira aparição** de cada valor distinto, então todo índice
`0..k-1` aparece no corpo. **Slot sobrando = wire adulterado.** Medido: vale em **35/35**
colunas canônicas, inclusive com `null`. Agora é checado, e é a mesma classe do "conteúdo após
o bloco de bits": recusar o que o encoder canônico nunca produz.

### O que a varredura confirmou íntegro

- **auto-consistência**: **608 wires** (modos `B` e `C`, `k` de 2 a 39 × `n` de 2 a 401) —
  tudo que o encoder produz passa pelo próprio validador, **0 falhas**;
- **fronteira do namespace**: `k=256` usa `w=8`; `k=257` recusa e o core assume;
- **`unpack_w`**: a checagem de bits-de-padding continua alcançável — não virou código morto
  com a checagem de tamanho.

### Tolerância × erro — analisado, não soldado

A política de aceitar-com-warning as adulterações **provadamente recuperáveis** (extensão,
padding a mais, bits mortos sujos) está analisada em
[`notas/2026-08/2026-08-06-2329-tolerancia-vs-erro-politica-de-wire-nao-canonico.md`](../../experiments/lab/dirty/notas/2026-08/2026-08-06-2329-tolerancia-vs-erro-politica-de-wire-nao-canonico.md),
com levantamento de gzip/xz/zstd/PNG/protobuf/JSON/CSV/HTML5 e da RFC 4648. **Hoje é erro
duro**, que é o default conservador. Ticket `T-B64-TOLERANTE`.

## Aberto — registrado, não esquecido

| ticket | o quê | por quê importa |
|---|---|---|
| ~~`T-BN-TIPADO`~~ | **SOLDADO 2026-08-07** | Fechou em duas etapas: o `bool + null` saiu do escopo com o denso `b2` (ADR-0037, 546→79 B), e o NUMÉRICO ganhou `#TCF.8nB<w><n>`. A objeção ("exige tag dentro do cabeçalho, que é grafia nova") **estava errada**: o `#TCF.8bB` (ADR-0039) já usava esta forma exata desde 2026-08-01 — tag no índice 6, modo no 7. O decode reescreve o cabeçalho e delega ao `decode_bn`. Medido n=200: `int` 0/1 608→55 B, `int` 0..3 604→93 B, `float` 612→59 B. |
| **`T-BN-LOTE`** | opt-in para emitir o modo `C` | ~1 B/coluna, para quem não lê incrementalmente |
| **`T-BN-MULTICOL`** | o bN no `.8M` | é a decisão pendente que já está no `STATUS.md`; escopo diferente deste |
| **`T-BN-LARGURA-VARIAVEL`** | não desperdiçar slots em `k` = 3, 5, 6, 7 | largura fixa arredonda para cima; `k` potência de 2 é o caso justo |
| **`T-B64-TOLERANTE`** | `on_noncanonical='error'\|'warn'` no `decode` | só para as 3 classes provadamente recuperáveis; default `error`. Soldar só se houver caso de uso real de recuperação de arquivo |
| **`T-B64-BITS-MORTOS`** | trocar a re-codificação O(n) por checagem O(1) | mesma garantia; só vale se o custo (~0,17%) um dia importar |
| **`T-BN-GZIP`** | medir sob gzip | o estudo multi-col registrou que o gzip encolhe muito o ganho do bN |

## Evidência

`experiments/lab/dirty/2026-07/2026-07-27/`: `1608` (a escada `k → largura`), `1647` (domínio
comprimido pelo core + alinhamento exaustivo 936/936), `2211` (o eixo de streaming), `2231`
(marcador por escape), `2247` (o espaço completo de delimitação, 7 opções).

---

## Weld T-BN-TIPADO (2026-08-07) — a rota numérica e a canonicidade da grafia

Fechado o único buraco de **existência** da família de bits: coluna numérica de baixa
cardinalidade não tinha faceta densa nenhuma.

### O wire

```
#TCF.8nB<w><n>↵<domínio>↵=<b64>
       │└─ discriminador bN, índice 7
       └── tag de tipo, índice 6
```

Não é grafia nova. O `#TCF.8bB` (lazy bool, ADR-0039) já usava esta forma desde 2026-08-01.
A objeção registrada na §aberto (*"exige tag dentro do cabeçalho, que é grafia nova"*)
**estava errada** — o precedente existia e não foi consultado. Vale como lição de processo:
o inventário das formas já emitidas tem de ser conferido antes de declarar bloqueio.

### Como foi soldado: reescrever e delegar, não duplicar

O decode do `nB` **reescreve o cabeçalho** para a forma explícita e chama `decode_bn`:

```python
return _cast_tipo(decode_bn(_V8_MAGIC + tcf_text[7:], "B", ...), tag)
```

É o mesmo idioma que a rota tipada já usava para o corpo core (*expande o apelido, delega,
casta*). Delegar em vez de duplicar o parser faz o `nB` herdar **de graça**: canonicidade do
header, marcador obrigatório, nada depois dos bits, todo slot referenciado, e as três
validações do payload b64. Um parser paralelo seria a divergência-entre-irmãos que já custou
4 bugs nesta mesma ADR.

No encode, o candidato entra no **mesmo `min()`** que já tinha core e polaridade — nunca
substitui. Só o modo `B`, pela mesma razão da rota flat.

### Medido (n=200)

| coluna | antes | depois |
|---|---:|---:|
| `int` 0/1 | 608 B | **55 B** |
| `int` 0..3 | 604 B | **93 B** |
| `float` | 612 B | **59 B** |

`bool` **não** entra: o denso `b1`/`b2` tem domínio implícito e vence por construção (47 B
contra 57 B sem null; 79 B contra 92 B com null).

### O buraco colateral: a grafia numérica não era canônica

Auditando o weld apareceu um defeito **pré-existente**, da mesma família dos 4 acima. A rota
`#TCF.8n` aceitava **cinco famílias de grafia** para o mesmo valor:

| wire | decodificava para |
|---|---|
| `01` | `1` |
| `1.50` | `1.5` |
| `+1` | `1` |
| `1e3` | `1000.0` |
| `1_0` | `10` (PEP-515) |

É exatamente a classe do bug de cabeçalho corrigido em 2026-07-28 — e o
`test_grafia_nao_canonica_fail_loud` já travava o invariante **para o header** enquanto o
**valor** ficava aberto. Mais uma vez: *o invariante existia e não foi aplicado*.

Corrigido por **canonicidade por re-emissão**, a mesma técnica do header: o encoder grafa com
`str`, logo a grafia canônica de `v` é `str(v)`.

```python
if str(v) != s:
    raise ValueError(f"#TCF.8n: grafia numerica nao-canonica {s!r} (canonica: {str(v)!r})")
```

O gate mora no **`_cast_tipo`**, que é o ponto único por onde passam as duas rotas numéricas
(corpo core e denso bN). Gate numa só criaria a divergência que esta ADR já documenta como
causa raiz.

Simetria conferida em 26 valores exóticos (subnormais, `2**53±1`, `1e-300`, `0.1+0.2`,
`-0.0`, `1e100`): **0 falhas** — o encoder nunca emite grafia que o decoder recusa.

### Efeito no EXP-016

Os 6 casos tipados estavam pinados em `espera="recusa"` — a previsão registrada era que o
weld os moveria para `ativa`. Moveu.

E o lab **passou mesmo assim na primeira rodada**, porque o classificador de rota devolvia
`tipado-n` para um wire que já era bN. Pin só protege contra o que o classificador enxerga;
classificador defasado transforma pin em anestesia. Corrigido: `rota()` reconhece
`<tag><disc>`, e o lab agora reporta `bN-B-tipado-n`. bN ativa em **58** dos 72.
