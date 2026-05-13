# 17 — famílias variadas (comportamento do exp 16 fora de emails)

## Princípio / motivação

Os exps 13-16 testaram apenas dois tipos de string: emails (D2) e
URLs (D4). É necessário mapear o comportamento do algoritmo em
famílias mais variadas antes de testar variantes algorítmicas
(par A+B independente, revisão retroativa) ou escala.

## Propósito

Pergunta dirigida: em quais famílias de string o algoritmo do
[exp 16](../2026-05-11-16-online-cleanup/) mantém a estrutura
observada em emails? Em quais degrada?

Esta é uma resposta à **pergunta 2** do dirty (comportamento), não
às perguntas 1 (viabilidade), 3 (formato) ou 4 (comparação ponto a
ponto com exp anterior). O algoritmo é o mesmo — só os dados mudam.

## Comparação

- **Compara com**: [16 (online cleanup)](../2026-05-11-16-online-cleanup/).
  O algoritmo é o **mesmo arquivo `online.py`** copiado, sem
  alteração. O que muda é o conjunto de datasets.
- **É comparável?** Não diretamente em bytes — datasets têm
  tamanhos e estruturas diferentes. A comparação é **qualitativa**:
  o algoritmo se mantém, degrada parcialmente, ou falha
  completamente em cada família.

## Cenários e valores

6 famílias × 12 strings cada (alinhado com D2-completo do exp 15).

| Família | Exemplo | Construção viesada para... |
|---|---|---|
| `urls` | `https://api.example.com/v1/users/00042/profile` | Base comum + 3 recursos × 4 IDs |
| `uuids` | `f47ac10b-58cc-4372-a567-0e02b2c3d479` | Hex random (caso adversarial) |
| `iso-timestamps` | `2026-05-11T08:00:00Z` | 2 dias × 6 horários |
| `ips` | `192.168.1.10` | 3 sub-redes × 4 hosts |
| `cpfs` | `123.456.789-00` | Dígitos pseudo-random (caso adversarial) |
| `codigos` | `PED-2026-00001` | 2 prefixos × 6 seriais |

**Viés declarado**: cada família foi construída para revelar um
comportamento esperado a priori. Não são amostras de dados reais.
O propósito é mapear **dinâmica do algoritmo**, não medir
performance absoluta em produção.

## Resultado observado

Roundtrip **6/6 OK**.

### Tabela 1 — Compressão por família

| Família | bytes | unid | chars total | chars lit | cobertura ref |
|---|---:|---:|---:|---:|---:|
| iso-timestamps | 380 | 49 | 240 | 27 | **88.8%** |
| codigos | 307 | 38 | 168 | 22 | **86.9%** |
| urls | 433 | 128 | 572 | 111 | **80.6%** |
| ips | 304 | 52 | 132 | 37 | **72.0%** |
| uuids | 563 | 430 | 432 | 429 | **0.7%** |
| cpfs | 291 | 168 | 168 | 168 | **0.0%** |

"Cobertura ref" = `1 − chars_literal / chars_total`. Mede quanto
do payload foi resolvido via ref (cobertura alta = algoritmo
funciona).

### Tabela 2 — Distribuição por tipo de cobertura

| Família | lit puro | puro ref | r+lit≤4 | r+lit>4 | só lit |
|---|---:|---:|---:|---:|---:|
| iso-timestamps | 1 | 5 | 6 | 0 | 0 |
| codigos | 1 | 5 | 6 | 0 | 0 |
| urls | 1 | 0 | 8 | 3 | 0 |
| ips | 1 | 5 | 4 | 0 | 2 |
| uuids | 1 | 0 | 0 | 1 | 10 |
| cpfs | 1 | 0 | 0 | 0 | 11 |

- **lit puro**: 1ª string (sempre)
- **puro ref**: zero literal, só refs
- **r+lit≤4**: refs + literal de até 4 chars
- **r+lit>4**: refs + literal grande
- **só lit**: sem refs (algoritmo não achou padrão)

### Dois regimes claros

**Regime A — algoritmo se sustenta (cobertura 72-89%)**:
`iso-timestamps`, `codigos`, `urls`, `ips`.

Característica comum: há **regiões fixas de chars consecutivos
iguais** entre strings (prefixo, sufixo, ambos). O algoritmo
detecta e referencia.

**Regime B — caso adversarial (cobertura 0-1%)**:
`uuids`, `cpfs`.

Característica comum: separadores em posições fixas (`.`, `-`)
mas chars **entre separadores variam**. O `min_len=3`
exige 3 chars consecutivos iguais — nem `.X.` nem `-XX-` atendem
quando X varia.

## Limitações

- **N=12 por família**: idêntico em ordem de grandeza ao exp 15;
  fala de comportamento, não de escala.
- **Famílias construídas a mão**: viesadas por construção. Não
  representam distribuições reais. Família real do mesmo tipo
  pode ter mais ou menos repetição.
- **6 famílias**: não esgota o universo. Faltam ao menos: nomes
  próprios, texto livre, hashes/base64, números decimais, enums
  curtos.
- **Sem reordenação**: ordem dos dados afeta cobertura (exp 04
  mostrou isso em outro contexto). Aqui usei ordem que vi natural;
  outras ordens podem dar resultados diferentes.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-11-17-familias-variadas
python run.py
```

Saída: 2 tabelas + lista de literais residuais por família +
TCFs em `encoded/` + debug detalhado em `debug-output/`.

## Próximo experimento

Conclusões em [conclusoes.md](conclusoes.md). Sequência sugerida:

- **18 — escala**: medir tempo e cobertura em N=50, 200, 1000
  para as 4 famílias do regime A
- **19 — par A+B independente**: pode dar margem nas URLs onde
  hoje há 3 introduções literais
- **20 — revisão retroativa**: pode ajudar em URLs e ips a
  reaproveitar refs entre famílias internas
- **Adversarial fica fora**: UUIDs e CPFs não são alvo deste
  algoritmo — outra abordagem (separadores estruturais reconhecidos,
  alfabeto reduzido) seria necessária. Registrar como limite e
  passar adiante.
