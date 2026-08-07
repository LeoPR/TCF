# Tolerância × erro em wire não-canônico — a política, e o que os outros formatos fazem

> *"avalie se dá pra criar uma condição de recuperação do dado em caso de lixo extra (…) então
> pode ter a verificação ativa com erro ou warning. Veja se faz sentido ou se isso poderia
> gerar problemas. E também liste como o comportamento de outros compressores ou tratamentos
> de dados (…) se o desempenho também é indiferente, daria pra deixar sempre ligado e tratar
> só o comportamento de erro/warning."*

**Faz sentido, e o projeto já decidiu esse padrão** — em 2026-07-24, por você. O que faltava
era o **critério** e a **taxonomia** de o que é recuperável.

Esta nota é **análise + levantamento**, não experimento novo: as medições vêm dos labs
[`2026-08-06-2104`](../../2026-08/2026-08-06/2026-08-06-2104-b64-canonicidade-3-rotas/) e
[`2026-08-06-2250`](../../2026-08/2026-08-06/2026-08-06-2250-b64-custo-x-protecao/), mais duas
sondas pequenas reproduzidas inline abaixo.

---

## 1. O precedente que já existe no projeto

`syntax.py:109-120`, no `split_lf_body`:

> *"NÃO-CANÔNICO: body sem o LF terminador estrutural. **Tolerante-COM-WARNING** (owner
> 2026-07-24, modelo camada-explícita-vs-implícita): aceita e decoda, mas AVISA (…)
> **Não muda o retorno (aditivo)**: a camada explícita permanece a mesma, só passa a sinalizar
> desvio."*

Aquele comentário carrega o critério inteiro, e ele é preciso: **tolera-se quando o valor
recuperado é provadamente o mesmo.** Não é "tolera-se o que dá pra ler" — é "tolera-se o que
dá pra ler **sem adivinhar**".

---

## 2. A taxonomia — o que é recuperável COM PROVA

| adulteração | valor recuperado é provadamente o mesmo? | veredito |
|---|---|---|
| **extensão** (bytes extras no fim) | **sim** — `unpack_w` só lê `n` símbolos; o excedente nunca entra | tolerável |
| **padding `==` a mais** | **sim** — mesmos bytes, outra grafia | tolerável |
| **bits mortos sujos** no último char | **sim** — medido: **4/4** variantes dão os mesmos bytes | tolerável |
| bits **úteis** trocados | **não** — não se sabe o original | fail-loud |
| char fora do alfabeto | **não** — inserção ou substituição? o stream desloca | fail-loud |
| truncado | **não** — faltam dados | fail-loud |

As duas sondas que fecham a taxonomia:

```
payload 67 chars = 402 bits;  dados 50 bytes = 400 bits  ->  2 BITS MORTOS
  último char 'E' (000100); variantes E/F/G/H mexem só nos 2 bits de baixo
  => 4/4 dão os MESMOS 50 bytes           -> recuperável por normalização
  variante 'I' mexe nos bits ÚTEIS
  => bytes diferentes                     -> NÃO recuperável

extensão +AAAA / +AAAAAAAA / +AAAAAAAAAAAA
  => cortar em ceil(n*w/8) devolve bytes IDÊNTICOS ao original em 3/3
```

**Metade das adulterações que hoje geram erro são recuperáveis com prova.** A sua intuição
está certa.

---

## 3. O problema que a recuperação cria — e é real

Truncar assume o **cabeçalho confiável** e o **payload suspeito**. Se o adulterado tiver sido
o `n`:

```
n de 200 -> 100 no cabeçalho:  corta para 25 bytes
                               e perde METADE dos dados — com WARNING, não com erro
```

Isso não invalida a ideia (qualquer decoder precisa confiar no cabeçalho para decodificar), mas
**muda o que o warning significa**: ele não diz "havia lixo extra", diz "**o cabeçalho e o
payload discordam, e eu acreditei no cabeçalho**". A mensagem tem de dizer isso.

E há o problema clássico: **warning em pipeline vai para `/dev/null`**. Um wire adulterado que
"funciona com aviso" vira, na prática, um wire aceito.

---

## 4. Como os outros fazem

Levantamento por classe de formato. O padrão que emerge: **quanto mais o formato se leva a
sério como formato, mais estrito** — e a tolerância, quando existe, é **explícita e opt-in**.

### Compressores binários — estritos, com checksum

| | comportamento |
|---|---|
| **gzip** | CRC32 + tamanho no trailer. Lixo depois do stream: descomprime e avisa (*"trailing garbage ignored"*), saindo com código de warning. Corrupção real: **erro**. |
| **xz** | checagem de integridade por bloco; **erro duro**. Tolerância só com `--single-stream` e afins. |
| **zstd** | checksum por frame (ligado por padrão no CLI); **erro**. Existe `--no-check`, mas é ato explícito de quem chama. |
| **zip** | CRC por entrada. Muitas ferramentas **extraem mesmo assim, reportando o CRC ruim** — e isso é considerado defeito de tolerância, não virtude. |

O gzip é o precedente mais próximo do que você propôs: **lixo à direita = warning; corrupção
interna = erro.** Exatamente a linha da taxonomia acima.

### Formatos de dados estruturados

| | comportamento |
|---|---|
| **PNG** | CRC por chunk. A spec distingue **crítico × auxiliar**: erro em chunk crítico é fatal; em auxiliar o decoder pode ignorar. É a mesma ideia de "recuperável com prova", aplicada por estrutura. |
| **Protobuf** | campos desconhecidos são ignorados **por design** (extensibilidade), mas wire malformado é **erro**. Tolerância planejada, não acidental. |
| **JSON** | RFC 8259 é estrito. Os parsers divergem tanto que precisaram nascer JSON5/JSONC para nomear a versão tolerante — sinal de que tolerância informal **fragmenta o formato**. |
| **CSV** | **não tem noção de corrupção.** Só percebe "número de colunas diferente" — nunca o dado em si. O `pandas` expõe `on_bad_lines='error'/'warn'/'skip'`, que é a admissão de que o formato não decide e joga para o chamador. |
| **HTML5** | o único caso em que a **recuperação de erro é normativa**: a spec define exatamente como recuperar de cada malformação. Funciona porque foi **especificado**, não porque cada parser inventou o seu. |

### E o que a própria RFC do base64 diz

A RFC 4648 trata disso explicitamente na seção de **codificação canônica**: os bits de padding
devem ser zero, e decoders **podem** rejeitar quando não são. As considerações de segurança
alertam que aceitar formas não-canônicas abre **canal encoberto** (informação escondida nos
bits mortos) e quebra suposições de deduplicação e de assinatura — dois wires diferentes com o
mesmo conteúdo.

**Isso é diretamente aplicável**: os 2 bits mortos medidos acima são exatamente esse canal.

---

## 5. O que isso sugere para o TCF

O TCF está mais perto do **compressor binário** que do CSV: tem invariante de canonicidade
declarado (S1.2), byte-canonicidade como gate de teste, e um `decode` que já é fail-loud em
dezenas de pontos. Herdar a política do gzip/PNG é coerente; herdar a do CSV não.

### Proposta — três níveis, um critério

```
ERRO       o valor recuperado seria ADIVINHADO
           char invalido, truncado, bits UTEIS trocados

WARNING    o valor recuperado e' PROVADAMENTE o mesmo
           extensao, padding a mais, bits MORTOS sujos

SILENCIO   nunca
```

O critério é o mesmo do precedente do LF: **aditivo — não muda o retorno, só sinaliza desvio.**

### Três cuidados, se for por esse caminho

1. **A mensagem tem de nomear o pressuposto.** Não *"lixo extra ignorado"*, e sim *"cabeçalho
   e payload discordam; usei o cabeçalho (n=200 → 50 bytes); sobraram 3 bytes"*. Quem lê o log
   precisa saber o que foi acreditado.

2. **O warning não pode ser o único canal.** Como o `pandas` faz: um parâmetro
   `on_noncanonical='error' | 'warn'` no `decode`, com **`'error'` como default**. Aí o
   tolerante é ato explícito de quem chama, não política escondida do formato — que é o ponto
   onde JSON se fragmentou e HTML precisou de spec normativa.

3. **O encode nunca produz não-canônico.** A tolerância é do leitor, e só. Se o encoder puder
   emitir as duas grafias, a canonicidade morre de verdade — e aí os gates byte-canônicos do
   projeto deixam de significar algo.

### Sobre "só em arquivo, não em transmissão"

O desempenho já não é critério (lab `2250`: **< 1%**). E o eixo transmissão × arquivo não
separa bem, porque a não-canonicidade de base64 **não vem do canal** — vem de quem produziu o
wire. O que separa bem é **quem consome**:

| consumidor | política |
|---|---|
| pipeline automático, ingestão | **erro** — ninguém lê o warning |
| ferramenta interativa, inspeção, recuperação de arquivo velho | **warning** — quem está olhando decide |

Ou seja: não é uma propriedade do transporte, é do **modo de uso** — e por isso vira parâmetro
do `decode`, não flag global.

---

## 6. Estado e encaminhamento

**Nada disso está soldado.** Hoje as três checagens são erro duro, o que é o default correto
e conservador. A proposta acima é aditiva e não muda byte nenhum.

| ticket | o quê |
|---|---|
| **`T-B64-TOLERANTE`** | `on_noncanonical='error'\|'warn'` no `decode`, default `'error'`; só para as 3 classes provadamente recuperáveis; mensagem nomeando o pressuposto |
| `T-B64-BITS-MORTOS` | (já registrado) trocar a re-codificação O(n) por checagem O(1) dos bits mortos |

**Recomendação**: soldar `T-B64-TOLERANTE` **só se** houver caso de uso real de recuperação
de arquivo. Sem esse caso, é superfície de API por antecipação — e o `T-BN-TIPADO` (−6015 B
medidos) paga muito mais.
