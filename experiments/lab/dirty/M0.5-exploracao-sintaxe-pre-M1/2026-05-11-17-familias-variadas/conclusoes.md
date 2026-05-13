# Conclusões — comportamento do algoritmo em 6 famílias

Roundtrip 6/6 OK. Cobertura via ref variou de **0% (cpfs) a 89%
(timestamps)**. Dois regimes claros emergiram.

## Regime A — algoritmo se sustenta

`iso-timestamps`, `codigos`, `urls`, `ips`.

Característica estrutural comum: regiões de **3 ou mais chars
consecutivos iguais** entre strings da mesma família. O algoritmo
detecta via LCP/LCS e referencia.

### iso-timestamps (cobertura 88.8%)

```
no1: "2026-05-11T08:00:00Z"
no2: no1[0:14] + "3" + no1[-5:]      ← 08:30 = pref + "3" + suf
no3: no1[0:12] + "9" + no1[-7:]      ← 09:00 = pref + "9" + suf
no4: no3[0:14] + no2[-6:]            ← 09:30 = pref de no3 + suf de no2
...
```

Comportamento similar a emails do exp 15: refs reaproveitando
sub-partes de nós anteriores. 5 strings viraram puro ref.

### codigos (cobertura 86.9%)

```
no1: "PED-2026-00001"
no2: no1[0:13] + "2"
...
no7: "INV-2026-00001"   ← introdução da 2ª família
no8: no7[0:13] + "2"
...
```

2 introduções (PED-, INV-) viraram literais. As 10 strings
restantes são `ref + 1 char` (o último dígito do serial).

### urls (cobertura 80.6%)

```
no1: "https://api.example.com/v1/users/00042/profile"   ← introdução 1
no5: no1[0:27] + "orders/2026-001/items"                ← introdução 2 (longa)
no9: no1[0:27] + "products/cat-a/sku-001"               ← introdução 3 (longa)
no11: no9[0:40] + "b/sku-003"                           ← subfamília interna
```

A base URL (`https://api.example.com/v1/`, 27 chars) é referenciada
a partir de no1, mas cada recurso novo (orders, products) entra
como literal de 17-22 chars. Em URLs, o **suffix matching falha
porque os endings variam por recurso** (`/items`, `/profile`,
`/sku-NNN`). O algoritmo não consegue reaproveitar entre famílias
internas.

Esse é exatamente o cenário onde **revisão retroativa** (exp 20
proposto) poderia ajudar: ao processar no5, identificar que
`users/` em no1 poderia ter sido fatorado e reabri-lo. Não
verificado nesse experimento.

### ips (cobertura 72.0%)

```
no1: "192.168.1.10"
no2..no4: refs a no1 com sufixos pequenos     ← mesma sub-rede
no5: pref de no1 + suf curto                  ← sub-rede 192.168.2.x
no7: "10.0.5.1"                               ← introdução 2
no11: "172.16.0.1"                            ← introdução 3
```

Cada sub-rede nova entra como literal. As variações de host dentro
da sub-rede viraram puro ref ou ref + lit curto.

## Regime B — caso adversarial

`uuids`, `cpfs`.

### cpfs (cobertura 0.0%)

```
no1..no12: TODOS literais puros
```

Nem uma única ref foi gerada. Razão estrutural: o formato CPF tem
separadores `.`, `.`, `-` em posições **2-3, 6-7, 10-11**, mas os
dígitos entre separadores **variam**. Para o algoritmo achar pref
de 3 chars iguais, precisaria de algo como `XYZ.` igual em duas
strings — o que só aconteceria por coincidência.

O dataset gerado foi pseudo-random; mesmo dataset real teria
comportamento semelhante (a não ser que houvesse correlação
explícita entre CPFs adjacentes, o que geralmente não é o caso).

### uuids (cobertura 0.7%)

1 dos 12 UUIDs teve uma cobertura mínima — quase coincidência
acidental. Estruturalmente idêntico ao caso CPF: separadores em
posições fixas mas conteúdo entre eles aleatório.

## O insight central

O algoritmo do exp 16 **vê "regiões de 3+ chars idênticos
consecutivos"** — não vê separadores como entidades estruturais,
não vê posições absolutas, não vê classes de caractere
(dígito/letra/símbolo).

Famílias onde esse modelo funciona:

- Há um **prefixo textual fixo** compartilhado (URL base, código
  com prefixo, timestamp do mesmo dia)
- Há um **sufixo textual fixo** compartilhado (`@gmail.com`, `Z`)
- Há **regiões internas** de chars iguais entre strings (`/v1/`,
  `:00:00`)

Famílias onde esse modelo falha:

- Conteúdo entre separadores é pseudo-random
- Cada string tem alta entropia interna
- Formato impõe estrutura por **posição** mas não por **conteúdo
  textual** repetido

## Pontos a registrar

1. **O algoritmo cobre Regime A bem**: 72-89% de cobertura sem
   ajustes. Resultado consistente com emails do exp 15 (que tinham
   ~70-90% também).

2. **Regime B é fora do alvo natural**. Não é "defeito" do exp 16
   — é limite estrutural. UUIDs e CPFs nesse formato não comprimem
   por LCP/LCS literal. Outras abordagens (separadores estruturais
   reconhecidos, classes de caractere, alfabeto reduzido)
   precisariam ser experimentos diferentes.

3. **URLs revelaram cenário onde retroativa pode ajudar**: 3
   introduções de 17-22 chars cada poderiam ser fatoradas se
   permitida reabertura de nós anteriores. Justificativa para
   priorizar exp 20 sobre exp 19 quando chegar a hora.

4. **Métrica de cobertura por chars é mais informativa** que bytes
   nesse experimento. Bytes totais varia muito por tamanho de
   string média; cobertura % normaliza.

5. **iso-timestamps** mostrou cobertura ainda maior que emails do
   exp 15. Combinação de prefixo + sufixo fixos é o caso favorito
   do algoritmo.

## O que este experimento não mostra

- Comportamento em N >> 12 dentro de cada família
- Misturas (URLs + IPs no mesmo dataset)
- Famílias não testadas (nomes, texto livre, hashes, decimais,
  enums)
- Que outras ordens dos mesmos dados dariam resultados similares
- Comportamento se min_len mudar (atualmente fixo em 3)
- Qual subconjunto dos resultados sobreviveria à medida em escala
  (próximo exp)

## Próximo passo natural

- **Escala (exp 18)**: pegar as 4 famílias do Regime A e crescer
  para N=50, 200, 1000. Medir se a cobertura se mantém ou degrada,
  e como o tempo escala (O(N²·L) na teoria).
- **Variantes algorítmicas** entram depois (exps 19, 20). A leitura
  do exp 17 indica que **revisão retroativa (20)** atacaria as
  introduções residuais em URLs, que é o gargalo mais visível
  no Regime A.
- **Regime adversarial (UUIDs/CPFs)** fica fora do escopo até
  surgir abordagem nova — não é refinamento do algoritmo atual.
