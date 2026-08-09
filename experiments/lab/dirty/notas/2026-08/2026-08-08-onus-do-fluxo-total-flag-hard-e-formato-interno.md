# O ônus do fluxo total, o flag hard, e o formato interno ótimo

**2026-08-08 · avaliação dos três pontos levantados pelo owner. Nenhum código mexido.**

---

## 1. "O ônus não some, muda de lugar" — certo, **e eu apontava pro lugar errado**

O owner: *"a gente joga o ônus do desempenho de conversão para fora do TCF, mas ele vai
existir (…) a gente só tira o tempo do TCF e coloca em algum outro lugar"*.

Procede. Medi o **fluxo total** — dado em BR entra, dado em BR volta, os dois caminhos
entregando exatamente a mesma coisa:

| | tempo | bytes |
|---|---:|---:|
| **A)** sem normalizar (BR → encode → decode → BR) | 51 361 µs | 705 B |
| **B)** normalizando (BR → ISO → encode+nature → decode → BR) | 92 848 µs | **33 B** |
| | **1,81×** | **4,7%** |

O tempo quase dobra. **Mas a decomposição contradiz a minha própria narrativa:**

| etapa do fluxo B | µs | % do fluxo |
|---|---:|---:|
| normalizar (BR → ISO) | 14 123 | **15,2%** |
| **encode** | 66 115 | **71,2%** |
| decode | 8 828 | 9,5% |
| desnormalizar | 4 765 | 5,1% |

**Normalizar não é o caro.** O caro é o encode — e dentro dele, o **baseline do FLOOR custa
58% do encode** (38 603 µs de 66 635 µs).

> Eu vinha dizendo *"o maior retorno está fora do TCF"*. O retorno está, mas **o ônus não
> foi pra fora — ele está dentro, no FLOOR**, que materializa vários candidatos pra
> comparar. Apontar pra normalização era desviar da conta.

E isso tem endereço: é o `T-GATES-ANTES` (avaliar gates antes de materializar candidatos),
que está aberto desde antes desta rodada.

### Sobre libs nativas — confirmado

O owner: *"tradução com libs nativas pode ser mais rápido por causa da alta otimização"*.
Medido: `date.fromisoformat` (implementado em C) é **16× mais barato** que
`datetime.strptime` (Python) para o mesmo resultado — 3,2% contra 52,8% do encode. A
conversão pela lib nativa é barata; a lenta é a genérica.

### A ressalva que o próprio owner fez, e que a medição não decide

*"não é nem bom nem ruim dependendo da perspectiva"* — exato, e a medição acima **não
inclui transmissão**. Se o fio vai pela rede, os 672 bytes economizados viram tempo
poupado do outro lado da conta. O ponto de equilíbrio depende do canal, e não é assunto
deste lab.

---

## 2. O flag hard — vale, e por um motivo **melhor** do que diagnóstico

O owner: *"um flag pra afirmar que a data é ISO forte e garantido (…) se não for, falhará
por pedido dos parâmetros do encode que o user pediu"*.

O ganho óbvio é diagnóstico: falhar alto quando a premissa do usuário está errada, em vez de
degradar em silêncio. Isso é real e é barato.

**O ganho não-óbvio é maior:** se o usuário *garante* a grafia e *manda* usar o spec, o
encoder **não precisa montar o baseline pra comparar**. Medido:

| | tempo | bytes |
|---|---:|---:|
| com FLOOR (hoje) | 66 635 µs | 33 B |
| strict (sem comparar) | **25 821 µs** | 33 B |
| | **−61%** | idênticos |

**O flag hard poupa 61% do encode, com os mesmos bytes.** É a maior economia de CPU que
apareceu nesta rodada inteira — e ela vem exatamente do que o §1 identificou como o caro.

### O risco, medido

Sem o FLOOR, o spec é aplicado mesmo onde perderia:

| coluna | sem nature | com FLOOR | **strict** | |
|---|---:|---:|---:|---|
| `diario` | 682 | 33 | 33 | ok |
| `agrupado-20` | 266 | 229 | 229 | ok |
| `constante` | 26 | 26 | **31** | 1,2× pior |
| `k12-ciclado` | 796 | 796 | **3314** | **4,2× pior** |

O `k12` é o aviso: onde o RLE do core já resolvia, o strict paga 4,2×.

### O que isto é, de verdade

O flag hard **é a origem HARD declarada, sem precisar do tipo nativo.** O owner já tinha
separado as duas origens; o `date` nativo não existe (é `fail-loud` hoje), então o strict é
a ponte: o usuário assume o papel que o sistema de tipos assumiria.

> **Avaliação**: vale, e o trade é honesto — CPU −61% contra risco de bytes assumido por
> quem pediu. Mas note que **são dois eixos diferentes num flag só**: "falhe se não for
> data" (diagnóstico) e "não compare, use" (performance). Vale decidir se são um parâmetro
> ou dois, porque alguém pode querer o primeiro sem o segundo.

---

## 3. O formato interno ótimo — **já é o que o spec faz, mas não é ISO**

O owner: *"o TCF pode fazer uma reconversão para um formato ótimo pra ele comprimir (…)
num formato bom ISO, talvez"*.

A primeira metade já está soldada: o `SPEC_DATA_ISO` converte para **ordinal decimal**
internamente. É exatamente a "string de data ótima" descrita.

A segunda metade — *"num formato bom ISO"* — a medição contradiz:

| | diário n=600 | mensal n=600 |
|---|---:|---:|
| ISO como forma interna | 414 B | 6338 B |
| **ordinal decimal** | **22 B** | **23 B** |

O ISO é bom para **humano e interoperabilidade**; para compressão ele é o pior dos alvos
testados, porque os separadores quebram a aritmética que o `*N+M|` procura. O ótimo interno
é o ordinal.

### Mas há uma generalização aqui que vale mais que a pergunta

Se o TCF vai reconverter para uma forma interna ótima, então **o parse e o alvo podem ser
separados**:

```
N grafias de entrada  →  [parse]  →  data canônica  →  [alvo]  →  o que vai pro core
   ISO, BR, US,           4 linhas      (interno)        ordinal / denso / delta
   compacto, ponto…       por grafia                     (compartilhado)
```

Hoje o `DataIsoSpec` tem parse e alvo **acoplados** no `encode_value`. Separá-los muda o
custo de crescer:

| | acoplado (hoje) | separado |
|---|---|---|
| adicionar uma grafia | uma classe nova | **uma linha de `fmt`** |
| adicionar um alvo | tocar todas as grafias | uma função, vale pra todas |
| escolher alvo por regime | não dá | o `min()` escolhe |

Isso **dissolve o atrito que eu tinha levantado** na análise crítica de ontem (*"CPF tem uma
grafia, data tem muitas; 6 a 8 specs"*). Com parse e alvo separados, não são 8 specs — é 1
spec com 8 parsers.

E resolve de quebra a questão dos alvos: o lab mediu que **nenhum alvo ganha sempre**
(`delta-dias` 5 de 8, `ordinal-denso` 2, `iso` 1). Com o alvo desacoplado, o `min()` escolhe
por regime, que é o padrão do projeto.

---

## Resumo da avaliação

| ponto | veredito |
|---|---|
| **o ônus muda de lugar** | certo — e a decomposição mostra que ele está **no FLOOR (58% do encode)**, não na normalização (15% do fluxo). Minha narrativa apontava errado |
| **libs nativas são mais rápidas** | confirmado: `fromisoformat` (C) é 16× mais barato que `strptime` |
| **flag hard** | vale, e o motivo forte é **CPU −61%**, não diagnóstico. Risco medido: até 4,2× em bytes. São dois eixos num flag só — decidir se é um parâmetro ou dois |
| **reconversão interna** | já é o que o spec faz; mas **ISO não é o formato ótimo** — o ordinal é (18–275× melhor) |
| **generalização** | separar **parse** de **alvo** transforma "8 specs" em "1 spec, 8 parsers" e deixa o `min()` escolher o alvo por regime |

## O que fica em aberto

- Se o flag hard é **um** parâmetro ou **dois** (falhar × não-comparar).
- Se vale separar parse/alvo **agora** ou quando a segunda grafia aparecer. Hoje só há uma,
  e separar sem necessidade é abstração especulativa.
- O ponto de equilíbrio tempo × bytes depende do canal (transmissão não medida).
