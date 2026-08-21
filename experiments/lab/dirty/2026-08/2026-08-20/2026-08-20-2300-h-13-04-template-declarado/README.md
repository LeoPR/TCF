# 2026-08-20-2300 — H-13-04: template declarado dispensa o gate global?

## A hipótese

> *"Spec/dica pré-declarada de template dispensa o gate global batch: coluna com dica valida
> por VALOR e não bufferiza."*

É o **S3** do [desenho do H-13-03](../../../notas/2026-08/2026-08-17-2400-h-13-03-encode-streaming.md):
se o template vem do contrato, não há o que descobrir. Em vocabulário de prefetch, é o
*"prefetch orientado"* — não há aposta, há informação.

## Veredito: a hipótese se sustenta, **mas eu medi a coisa errada**

| gate | resultado |
|---|---|
| **G1** equivalência (decide o mesmo que o global) | **6/6** |
| **G2** streaming (a decisão em `k` não olha `k+1..n`) | **7/7** |
| **G3** fail-loud (dica errada recusa) | **1/1** — recusa **no 1º valor** |
| **G4** varreduras poupadas | **−0,2%** |

**G4 ≈ zero, e isso não refuta a hipótese — refuta a minha métrica.** Os dois gates olham
todo valor: o global para *confirmar* uniformidade, o declarado para *validar* cada um. A
contagem de varreduras nunca ia distinguir os dois.

**O que distingue é BUFFER, não varredura.** O global **não pode emitir nada** antes do
último valor (só então sabe se aplica); o declarado **emite conforme valida**. É diferença
de *quando o primeiro byte sai*, não de *quantos valores são olhados*.

E é a terceira vez nesta sessão que escolho a métrica errada:

| onde | métrica que escolhi | métrica certa |
|---|---|---|
| H-13-03 (plano) | pico de memória | latência/overlap |
| lab 0800 | B1+B2 somados | união por coluna |
| **aqui** | **contagem de varreduras** | **ponto de emissão / buffer retido** |

O padrão: escolho o que é **fácil de contar** em vez do que **decide**. Registrado.

## O caso que mostra o mecanismo

```
s5-dica-errada   global varreu 90 · declarado recusou no valor 1     poupou 89
s3-quebra-cedo   global varreu  2 · declarado parou em 2             (empatam)
s4-quebra-tarde  global varreu 201 · declarado parou em 201          (empatam)
```

O declarado só ganha varredura quando a **dica está errada** — aí ele descobre na primeira
comparação, enquanto o global varreria tudo. Nos casos em que a dica está certa, ambos
percorrem a coluna (mas só um precisa **segurá-la**).

## O achado de carona — que corrige um lab anterior

**O gate do split olha os SEPARADORES, não a LARGURA dos dígitos:**

```
'(47) 99813942'  template=('(', ') ', '')  campos=['47','99813942']
'(0) 0'          template=('(', ') ', '')  campos=['0','0']        ← MESMO template
```

Logo o dado **sujo do telefone passa no gate** — `_struct_split_encode` aplica normalmente
numa coluna que o contenha (`r2-fone-real`: 19 971 valores, gate aceita, `recusou_em=None`).

Isso **corrige o lab [2145](../2026-08-20-2145-telefone-br-real/)**, onde escrevi que *"o
gate 100%-uniforme recusaria a coluna INTEIRA por causa de 1% de sujo"*. Não recusa. Quem
sofre com largura variável é a **nature** (b85 de largura fixa) — e é ela que precisa do
`ndig`, como a verificação daquele lab já apontava. **Eu tinha misturado dois critérios
diferentes**: o do gate (separadores) e o da nature (largura).

## O que isso significa para o H-13-03

- **S3 é viável** e é o único dos três que **não especula**: sem lookahead, sem retrabalho,
  sem prefixo a descartar.
- **A economia não é CPU** — é *quando o encoder pode começar a emitir*. Quem quiser o
  argumento de streaming precisa medir **latência ao primeiro byte** e **buffer retido**,
  não varreduras.
- **A dica errada é barata de detectar** (1 valor), o que torna o modelo seguro: declarar
  errado custa uma comparação, não uma coluna inteira.

## Não medido (declarado)

- **Latência ao primeiro byte e buffer retido** — a métrica certa, e o lab **não a mediu**.
  É o próximo passo, e vale para os três (S1/S2/S3).
- **De onde vem a dica**: o mock recebe o template pronto. Não há desenho de *como* uma
  spec o declararia (isso conecta ADR-0041 e o `T-FMT-CONTRACT-SIGNATURE`).
- **O gate não valida largura** (o achado acima) — se a dica devesse incluir largura, é
  outro mecanismo, não este.
- Uma seed, um volume. CPU não medida.

## Evidência

7 wires + 7 roundtrips, portão de completude. `resultado.json` com os 4 gates por caso.

## Conexões

- [H-13-03](../../../notas/2026-08/2026-08-17-2400-h-13-03-encode-streaming.md) (S3) ·
  [Pacote 13](../../../notas/2026-05/roadmap-hipoteses.md)
- Lab corrigido por este: [`2145`](../2026-08-20-2145-telefone-br-real/)
- `src/tcf/multi/split.py` (o gate global real)
