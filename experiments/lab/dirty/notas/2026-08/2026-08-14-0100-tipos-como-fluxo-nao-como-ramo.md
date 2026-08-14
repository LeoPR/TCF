# Tipos como FLUXO, não como ramo — ciclo de análise

**2026-08-14** · pedido do owner:

> *"o fluxo tem que ser generalizado […] ter um código exclusivo pros tipos deixa o código
> mais engessado, mas ao mesmo tempo podemos admitir que os tipos mais primitivos como
> string, bool e int (e até float) são especiais no python. porém, também precisamos que isso
> seja uma **otimização, não um padrão do tcf**. então como mesmo o bool respeita o fluxo,
> então é justo pensar no int também. no .9 podemos pensar em atalhos pra isso […] o
> entendimento do core para os tipos é sempre amplo, a parte de parâmetros da função encode,
> decode também é diferente, e o que vai para escrever efetivamente no corpo do arquivo (ou
> stream) tcf é outro ainda. […] só vamos padronizar pro int também, ver o que de algoritmos
> já temos que se encaixa nele, reaproveitar e usar."*

---

## 1. A boa notícia: o fluxo **já** é generalizado, e está escrito

A generalização que o owner pede não é trabalho a fazer — é decisão já tomada, em
2026-07-25, e a docstring de `_tipo_single_col` (`encoder.py:98-112`) a enuncia:

> *"FONTE ÚNICA da detecção de tipo do single-col. **Antes só o bool tinha ramo; generalizado
> p/ que cada tipo novo seja uma LINHA aqui, não um bloco novo no `encode`**."*

E é literalmente isso: a função devolve `(tag, render)`. O bool é
`return "b", lambda v: RENDER_B[v]`; o número é `return "n", str`. Duas linhas, mesma forma.

O decode é simétrico: `_cast_tipo(strs, tag)` com um ramo curto por família.

## 2. Os três planos, mapeados (o ADR-0041 aplicado a tipos)

O owner separa três coisas, e elas de fato existem separadas no código:

| plano | o que é | onde vive | vê o tipo? |
|---|---|---|---|
| **CORE** | OBAT · HCC · seq-RLE · polaridade · bN | `composicional/`, `core/` | **não** — só enxerga linhas de texto |
| **API** | `nature=` · `nature_per_col=` · a entrada tipada | `encoder.py:349, 531` | sim, e **é onde está o buraco** |
| **WIRE** | a tag do índice 7 (`n`/`b`/`s`) + `:id` do spec | header e meta | sim |

A separação é real e saudável: **o core não sabe o que é um inteiro**, e não precisa saber.
Tipo é assunto das pontas — a API que recebe e o wire que declara.

O buraco está no plano da **API**: `nature=` só aceita string. E no plano do **WIRE**, no
`.8H`, tag de tipo e id de spec são **mutuamente exclusivos** na gramática do meta
(`hierarchical.py:602-605` no encode, `:806-813` no decode) — os dois não cabem juntos hoje.

## 3. "O bool respeita o fluxo" — verificado, e é a chave

O encode tipado é **um `min()` de candidatos** (`encoder.py:549-600`):

```
candidatos = [ core ]
           + [ polaridade ]                 se aplicável
           + [ bN de domínio ]              todos os tipos, EXCETO bool
           + [ denso b1 / b2 ]              SÓ bool
min(candidatos, key=bytes)
```

O bool não tem rota própria — ele tem **um candidato a mais** no mesmo `min()`. E a razão
está escrita no código: *"`bool` NÃO entra [no bN]: o denso b1/b2 tem domínio **implícito** e
vence por construção"*. Ou seja, o bool troca um candidato genérico por um mais específico
que sempre ganha naquele caso — e o resto do fluxo é idêntico.

**É exatamente o modelo para o int.**

## 4. O que o int já herda (medido)

| algoritmo | o int usa hoje? | evidência |
|---|---|---|
| seq-RLE | **sim** | `[100000+i]` → `#TCF.8n`, 23 B |
| RLE | **sim** | `[42]*600` → `#TCF.8n`, 17 B |
| **bN de domínio** | **sim** | `[10,20,30,40,50]` → `#TCF.8nB3258` |
| polaridade | **sim** | `1..600` → `#TCF.8n!!` |
| OBAT (afixos) | **sim** | `[20240000+i]` → `#TCF.8n!` |
| denso (bitpack) | **não** | exclusivo do bool (`b1`/`b2`) |
| pré-transformação (spec) | **não** | `nature=` recusa entrada tipada |

**Cinco de sete já funcionam.** O int não está desassistido — ele está sem as duas peças que
o bool tem: o denso e (para ambos) o spec.

## 5. A triagem que o owner pediu: `.8` = estrutura, `.9` = atalho

Aplicando o critério dele (*"isso tem que ser uma otimização, não um padrão do tcf"*):

**`.8` — estrutura, porque muda o que é expressável:**
1. **Spec na rota tipada** — mais um `candidatos.append`, exatamente como o bool fez. Sem
   rota nova, sem código exclusivo. Pontos já localizados: `encoder.py:539` (depois do
   `render`), `decoder.py:410-411` (antes do `_cast_tipo`), header `#TCF.8n [nome]:id` com
   slot livre.
2. **Tag + spec convivendo no `.8H`** — hoje a gramática do meta os torna exclusivos, e
   apagar o check faria coluna int voltar string **sem erro**. Exige gramática nova; soma ao
   `T-META-NAO-DECLARA-MODO`.
3. **Fechar os "ignora calado"** (`T-NATURE-IGNORADA-CALADA`) — independe do resto e é barato.

**`.9` — atalho, porque só troca bytes/tempo sem mudar o que se pode expressar:**
4. **Denso para int** — o análogo do `b1`/`b2` com largura variável (o `pack_w` já existe em
   `bitpack.py` e é parametrizado por largura). É o "atalho" que o owner previu.
5. **Auto-detecção dos gatilhos** do spec (progressão, largura fixa, base alta) sem o usuário
   declarar.

A linha entre os dois é justamente a que o owner traçou: (1)–(3) mudam o **contrato**;
(4)–(5) só mudam o **desempenho** de algo que já é expressável.

## 6. O ponto delicado: o spec parametrizado

O `OFFPAD` (offset para o mínimo) é o alvo de maior ganho do int — mas ele é
**parametrizado**, e isso o coloca em conflito com o plano do WIRE: a base não é dedutível do
corpo, então o id no header não basta e o self-describing do ADR-0027 quebra.

Isso não é detalhe de implementação — é a diferença entre *"o tipo é uma linha no dispatch"*
e *"o tipo precisa de um campo novo no wire"*. Vale decidir antes de qualquer weld:

- **caminho A**: só specs **auto-contidos** no `.8` (PAD e B94 são; OFFPAD fica de fora), e o
  parametrizado espera o desenho do meta estendido;
- **caminho B**: o parâmetro viaja no header agora, e aí é extensão de formato no `.8`;
- **caminho C**: o parametrizado vive só no modo contrato-nas-pontas
  (`T-SPEC-SEM-CARIMBO`), onde o wire já não se auto-descreve por decisão.

O caminho A é o que mantém o `.8` como estrutura mínima e adia a decisão sem perder os dois
alvos que já funcionam.

## 7. Proposta de lab

Um lab que **não** mede compressão — mede **conformidade de fluxo**. A pergunta não é "quanto
ganha", é *"o int percorre o mesmo caminho que o bool?"*.

Casos, para cada tipo (`bool`, `int`, `float`, `str`) e cada rota (single, multi, `.8H`):

1. **Simetria de dispatch**: o tipo é detectado por uma linha em `_tipo_single_col`?
2. **Simetria de candidatos**: quais candidatos o `min()` consulta? (tabela tipo × candidato)
3. **Simetria de API**: `nature=` é aceito? recusado? **ignorado calado**?
4. **Simetria de wire**: a tag aparece? convive com `:id`?
5. **Simetria de RT**: volta com o tipo certo, comparado por `type()`?

O produto é uma **matriz de conformidade** — onde o int diverge do bool, e se a divergência é
justificada (como o denso, que tem razão escrita) ou é lacuna. Isso dá a lista exata do que
soldar para "padronizar pro int", que é o pedido.

E fica registrado o que **não** medir de novo: os ganhos já estão medidos nos dois labs
anteriores; repetir seria diluir.
