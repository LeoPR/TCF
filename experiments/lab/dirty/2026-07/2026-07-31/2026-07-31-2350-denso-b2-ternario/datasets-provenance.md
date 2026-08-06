# Proveniência — T-DENSO-B2, denso ternário `#TCF.8b2<n>` (2026-07-31-2350)

## Por que este lab existe

O denso b1 (bool puro SEM null, domínio implícito) está soldado. O lab vizinho
[`2026-07-28-0829-bn-tipado-ganho-medido`](../../2026-07-28/2026-07-28-0829-bn-tipado-ganho-medido/)
mediu o ternário (bool COM null) com o bN tipado de domínio DECLARADO: 94 B vs 546 do core.
A hipótese medida aqui: o domínio `null/false/true` é conhecido a priori (tipos puros do
JSON), então declará-lo é redundante — denso a 2 bits com domínio IMPLÍCITO congelado
`0=null, 1=false, 2=true`, símbolo 3 reservado/fail-loud. Estimativa prévia para n=200:
~79 B. **Medido: 79 B exatos.**

## Sintéticas — determinísticas, sem RNG

Valores ciclados por `i % k` sobre o índice. **Sem `random`, sem relógio, sem rede.** Os
fontes bool replicam a geração do lab vizinho `2026-07-28-0829` (mesmas sementes/geradores,
copiados e re-gerados por este `run.py` — os `inputs/*-fonte.json` são equivalentes):

| coluna | geração | vem de |
|---|---|---|
| `bool-null` | `None if i%3==0 else bool(i%2)`, n=200 | lab 0829, `casos["bool-null"]` |
| `bool-null-esparso` | `None if i%17==0 else bool(i%2)`, n=200 | lab 0829, idem |
| `bool-puro` | `bool(i%2)`, n=200 | lab 0829, idem |
| `bool-constante` | `[True]*200` | lab 0829, contra-caso `bool-constante` |
| `bool-varre-nNNNN` | `None if i%3==0 else bool(i%2)`, n ∈ {3,10,50,200,1000} | varredura deste lab, densidade de null ~1/3 |

`bool-puro` e `bool-constante` entram de propósito como NÃO-aplicáveis: sem null, o
protótipo RECUSA (o b1 de 1 bit domina; `k≤1` cai no RLE do core).

## Reais — fixtures já commitadas

**Nenhum download.** De `datasets/samples/adult-census/adult-sample.csv` (o mesmo fixture
do lab 0829). O CSV dá STRING; o lab converte para `bool` — exatamente a conversão do lab
vizinho — e injeta nulls **deterministicamente a cada 7º elemento** para formar o ternário
real-ish. É escolha DO LAB, não do dado.

| coluna | campo | conversão | null |
|---|---|---|---|
| `real-adult-sex-bool-ternario` | `sex` | `v.strip() == "Male"` | a cada 7º (`i%7==0`) |
| `real-adult-class-bool-ternario` | `class` | `">" in v` | a cada 7º |

## Validação — e por que não é circular

```
dados -> _tipo_single_col   (src/tcf)  -> tag 'b' (+ tem null?)
      -> pack_w(idx, 2)     (src/tcf)  -> payload  (o MESMO bitpack soldado do b1)
      -> wire #TCF.8b2<n>\n<b64>
      -> proto_decode: parse posicional estrito, b64 validate=True,
         tamanho EXATO ceil(2n/8), unpack_w (src/tcf) — fail-loud em
         símbolo 3, payload errado, padding não-zero
      -> compara com os DADOS ORIGINAIS
```

O mecanismo de empacotamento NÃO é reimplementado — é o `bitpack.py` do `src/tcf`, só com
`w=2` (o b1 soldado usa `w=1`). O `hoje` vem do `encode`/`decode` públicos. O bN tipado da
comparação é o `tipado_bn.py` do lab vizinho, importado, não copiado.

O RT compara **valor, tipo e comprimento** (comprimento porque `zip` trunca — lição do lab
`2026-07-26-2126`). Roundtrip é ARQUIVO: `outputs/<nome>-dataset.roundtrip.json`
byte-idêntico a `intermediates/<nome>-dataset-consumido.json`, com assert no `run.py`.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. Os `-b2.tcf` são proposta — o `decode` público
  ainda não conhece o modo `2`.
- Domínio congelado `0=null, 1=false, 2=true` — compartilha o conceito de domínio
  implícito com o b1; se o b1 mudar a ordem, o b2 tem de seguir.
- As colunas reais tipadas são **convertidas pelo lab** e os nulls são **injetados pelo
  lab** (a cada 7º), não do dado.
- **gzip e CPU não medidos.**
- Fail-loud medido em 3 casos (símbolo 3, truncado, b64 não-canônico); evidência em
  `outputs/fail-loud.txt` + assert no `run.py`.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relógio, sem rede. Sai `0` só se o RT
estrito passar em todas as colunas e os 3 casos fail-loud rejeitarem com `ValueError`.
