# O custo da ambiguidade de data — e as quatro formas de lidar com ela

**2026-08-08 · dirty · 4 casos, `n=480`, 8 encodes, 0 falhas de RT**

---

## 1. A tese está certa, e agora medida

> *"a ambiguidade só gera problema de compressão, não de encode/decode, que vai gerar o
> mesmo código"*

**Confirmado: 8 de 8 encodes com round-trip byte-exato**, incluindo todos os que usaram o
spec **errado** de propósito. As colunas são 100% ambíguas por construção — dia **e** mês
≤ 12, onde `DD/MM` e `MM/DD` são leituras igualmente válidas.

A integridade nunca depende de acertar a leitura. Só a compressão depende.

## 2. Mas o custo **não é constante** — ele é proporcional à regularidade destruída

| caso | ignorar (hoje) | spec CERTO | spec ERRADO | custo bruto |
|---|---:|---:|---:|---:|
| `consecutivo-no-mes` | 852 | **529** | 3159 | **+497%** |
| `consecutivo-no-mes-espelhado` | 849 | 3159 | **529** | −83% |
| `ambiguo-sem-ordem` | 1816 | 1669 | 1667 | **−0,1%** |
| `ambiguo-k12` | 399 | 411 | 411 | **0,0%** |

Os dois últimos são o refinamento que faltava na tese: **onde não há regularidade a perder,
errar a leitura custa exatamente nada.** O prejuízo existe só quando a leitura certa teria
encontrado uma sequência.

### O mecanismo, na telemetria

| | corridas do seq-RLE | deltas uniformes |
|---|---:|---|
| leitura **certa** | 40 | `[1]` |
| leitura **errada** | 239 | `[-334, -333, 20, 28, 29, 30]` |
| `ambiguo-sem-ordem` (as duas) | 0 | — |

```
certo   →  #TCF.8!!↵*12+1|739617↵*12+1|739648↵…      corridas de 12, passo +1
errado  →  #TCF.8!!↵*2+31|739617↵*2+31|739676↵…      corridas de 2, passo irregular
```

A leitura errada não destrói o dado — **estilhaça a corrida**. `01/03, 02/03, 03/03` em BR é
`1, 2, 3 de março` (passo +1); em US é `3 de janeiro, 3 de fevereiro, 3 de março` (passo
~+30). Mesmo texto, mesma reversibilidade, regularidade oposta.

## 3. O número que dissolve o risco: **com FLOOR, o prejuízo é zero**

Se o spec entrar como **candidato** do `min()` — o padrão do projeto — e não como
substituto, o pior caso cai de volta no wire de hoje:

| caso | com FLOOR | vs hoje |
|---|---:|---:|
| `consecutivo-no-mes` | 852 | **0,0%** |
| `consecutivo-no-mes-espelhado` | 529 | **−37,7%** |
| `ambiguo-sem-ordem` | 1667 | **−8,2%** |
| `ambiguo-k12` | 399 | **0,0%** |

**Nunca pior que hoje, em nenhum caso.** E em dois dos quatro, o palpite errado ainda ganha
— porque a leitura "errada" às vezes encontra uma regularidade que a "certa" não tinha.

> Isso reduz a decisão sobre ambiguidade a uma exigência de arquitetura, não de acerto:
> **o spec tem de ser candidato, nunca substituição.** Com isso, adivinhar errado é grátis.

---

## 4. As quatro formas, com custo

### a) IGNORAR — tratar como string

O que o TCF faz hoje. **Custo zero, risco zero.** E medido: em `ambiguo-k12` ignorar (399 B)
**ganha** de qualquer spec (411 B); em `ambiguo-sem-ordem` fica a 8% do melhor.

É o **default correto**, e continua sendo o piso do FLOOR.

### b) ORIENTAR — o guia, sem código

*"entra uma data estranha → formata → deixa padrão pro TCF trabalhar"*

**É onde está o maior retorno por menor esforço**, e não mexe em `src/tcf`.

Custo de explicar: documentação. Risco: o produtor não seguir — e aí nada quebra, só
comprime menos.

> **Pendente**: qual grafia recomendar depende de qual já é default na indústria. Está sendo
> levantado (bancos, linguagens, formatos de arquivo). **Esta seção será revista com o
> resultado** — recomendar uma grafia sem saber o que o mundo já emite seria chute.

### c) MULTI-PADRÃO dentro do TCF

O owner separou bem: *"salvo questões de resolução (ano, ou anomes, ou as combinações até
datetime com nanossegundos) pode ser feito dentro, mas a internacionalização é complicado"*.

Concordo, e a razão é estrutural — **são problemas de natureza diferente**:

| | resolução | internacionalização |
|---|---|---|
| forma | **hierárquica**: `2026` ⊂ `2026-01` ⊂ `2026-01-31` | **combinatória**: ordem × separador × idioma |
| ambiguidade | **nenhuma** — o comprimento já distingue | existe, e é real (BR/US) |
| quantos specs | 1 por resolução, e elas se encaixam | 1 por combinação, e elas se multiplicam |
| escala | linear e previsível | explode |

**Linha de corte defensável: resolução dentro, internacionalização como specs nomeados
extras.** Não porque i18n seja impossível, mas porque ela não *converge* — cada spec novo é
um caso isolado, enquanto as resoluções formam uma família.

### d) ACEITAR a ambiguidade

O ponto de vista do owner, agora com número: **custa 0% com FLOOR**, e o palpite pode ser
tão preguiçoso quanto se queira.

O único cuidado é o registrado antes: **adivinhar não substitui declarar**. O palpite escolhe
qual spec tentar; qual foi escolhido tem de ir pro wire, senão o decode não inverte.

---

## 5. O que este lab NÃO fez

- **Não decide qual grafia recomendar** — depende do levantamento externo, em curso.
- Só **BR × US**, o único par verdadeiramente ambíguo entre as grafias comuns. Não testou
  ambiguidade com `YY` de 2 dígitos, nem com mês por extenso em outro idioma.
- Só **data**, sem hora.
- Não mede CPU do `min()` com mais candidatos (é `.9`).
- As colunas são **100% ambíguas por construção** — no dado real a proporção é menor, e aí o
  custo bruto cai proporcionalmente. O número de 497% é o **teto**, não a expectativa.
