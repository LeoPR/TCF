# DEMO — intuições CPF/CNPJ medidas (T-SPEC-DEEPDIVE-08 §5.1)

Gerado por scripts/spec_demo.py. Todos os bytes MEDIDOS (emitted_bytes por coluna,
via SideOutputs BUG-07). CPF efêmero (§2.3); CNPJ real não-PII com base mascarada.

## 1. A transformação de 1 valor (o que a nature faz)

  CPF  '111.111.111-11'  (14B)  →  '%g$.u'  (5B, compressible)
  CPF  '222.222.222-22'  (14B)  →  ')K%7l'  (5B, compressible)
  CNPJ '11.222.333/0001-81' (18B)  →  '!K9p5B$'  (7B, compressible)

  A nature JOGA FORA a máscara (pontuação) + o DV (derivável) e empacota o CORPO
  num inteiro base-94. Em 1 valor isolado é ótimo (−64%). O PROBLEMA aparece em
  COLUNA, porque o inteiro base-94 apaga a estrutura ENTRE as linhas.

## 2. CNPJ REAL (receita, não-PII): a estrutura que a nature destrói

  amostra: 5000 CNPJs reais (primeiros, PK-sorted)
  FILIAL   : 36 distintos; '0001' domina 97.6% (quase-constante → dict/RLE quase de graça)
  BASE-8   : 99.9% únicos, MAS 94.9% não-decrescente (ORDENADA)
  deltas base consecutivos concentrados: +11=37%, +10=24%, +12=18%, +9=7%
  DV       : derivável (mod-11) — 0 bits de informação (checado True)

  amostras (base mascarada, filial+ordenação visíveis):
    XX.XXX.X0/0001-54   (base termina …70, filial 0001)
    XX.XXX.X2/0001-89   (base termina …82, filial 0001)
    XX.XXX.X4/0001-03   (base termina …94, filial 0001)
    XX.XXX.X4/0001-00   (base termina …04, filial 0001)
    XX.XXX.X5/0001-90   (base termina …15, filial 0001)

  BYTES da coluna cnpj (emitted_bytes / modo vencedor):
    ORDENADA (como no hub)   sem nature  32665B (split)  |  com nature  39999B (raw  )  →  nature PIORA +7334B
    EMBARALHADA              sem nature  41332B (split)  |  com nature  39999B (raw  )  →  nature ajuda -1333B

  LEITURA: ordenada, o split explora a estrutura (matriz/filial/deltas) e a nature
  a DESTRÓI (cai pra raw) → +bytes. Embaralhada, não há estrutura → a nature ganha.
  A nature de hoje é FORÇADA (camada-0) — não deixa o split competir. É o que o fix corrige.

## 3. CPF sintético (efêmero, §2.3): nature ajuda RANDOM, piora CLUSTERED

  500 CPFs sintéticos por regime (gerados, NÃO salvos — §2.3)
  RANDOM   : corpos aleatórios (ex. 245.389X.XXX-XX — mascarado §2.3)
  CLUSTERED: base sequencial (lote emitido junto): 412.529X.XXX-XX, 412.529X.XXX-XX, 412.529X.XXX-XX — prefixo '412.529' compartilhado, base +3 por linha

  BYTES da coluna cpf (emitted_bytes / modo):
    RANDOM                   sem nature   7499B (raw  )  |  com nature   2999B (raw  )  →  nature AJUDA -4500B
    CLUSTERED (sequencial)   sem nature   1043B (split)  |  com nature   2999B (raw  )  →  nature PIORA +1956B

  LEITURA: a MESMA intuição do CNPJ vale pro CPF. Onde há estrutura inter-linha
  (lote sequencial = clustering administrativo real, NUNCA testado standalone), a
  nature pode PIORAR. Onde não há (random), ela ganha. O gate real-world do CPF
  segue aberto (só sintético) — mas o mecanismo é o mesmo, agora demonstrado.
