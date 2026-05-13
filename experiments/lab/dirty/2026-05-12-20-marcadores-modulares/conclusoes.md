# Conclusões — modularização sem regressão

Refatoração estrutural. Resultado: TCFs **byte-idênticos** ao
exp 16 em 21/21 datasets, com o algoritmo (`online.py`) e a
sintaxe (`VerboseSyntax`) agora em arquivos separados, ligados
apenas pela interface abstrata `Syntax`.

## Decisões de design registradas

### 1. Interface mínima

`Syntax(ABC)` tem apenas dois métodos: `encode(...)` e
`decode(tcf_text)`. Não há "encoder" e "decoder" como classes
separadas — manter os dois na mesma classe garante que **a
linguagem (sintaxe) seja sempre consistente entre escrita e
leitura**.

Se uma sintaxe permite emitir algo que o decoder da mesma
sintaxe não sabe ler, o problema fica visível na mesma classe.
Sintaxes diferentes podem coexistir como subclasses distintas.

### 2. Algoritmo não vê a sintaxe

`online.py` produz tokens. Não importa qual sintaxe vai
serializá-los. Isso permite trocar a sintaxe sem mexer no
algoritmo, e também trocar o algoritmo (no futuro) sem mexer na
sintaxe.

### 3. Tokens permanecem como dataclasses

`TokLit`, `TokRefPref`, `TokRefSuf` continuam dataclasses
simples. Quando uma sintaxe nova precisar de tokens diferentes
(p.ex. token interno `noN[a:b]`), a interface vai precisar
evoluir — mas por enquanto os 3 tokens cobrem todos os casos
do regime atual.

### 4. Aceitar indireção em prol de clareza

A chamada `sintaxe.encode(...)` é levemente mais cara que uma
função direta (overhead de método virtual em Python). Não
medimos diferença em tempo — algoritmo é o gargalo. Em escala
maior, em linguagem nativa (Rust/C), essa indireção tem custo
zero ou negativo (inline + monomorfização).

Vale a clareza.

### 5. Output organizado por sintaxe

TCFs salvos em `encoded/<syntax_name>/<dataset>.tcf`. Quando
houver múltiplas sintaxes, podemos comparar arquivo a arquivo
lado a lado (`encoded/verbose/D2-completo.tcf` vs
`encoded/compact_v1/D2-completo.tcf`).

## O que isto habilita

Trocar sintaxe agora é uma operação **localizada**:

```python
# antes (exp 16)
from encode_online import encode_online
tcf = encode_online(linhas, unicas, tokens, header)

# depois (exp 20)
from syntax_verbose import VerboseSyntax
sintaxe = VerboseSyntax()
tcf = sintaxe.encode(linhas, unicas, tokens, header)
```

Para experimentar uma sintaxe nova:

1. Criar `syntax_nova.py` com classe que herda `Syntax`
2. Implementar `encode` e `decode`
3. Trocar a linha `sintaxe = VerboseSyntax()` no `run.py`
4. Rodar os mesmos 21 datasets, comparar bytes/unidades

Sem tocar em `online.py`. Sem tocar em outras sintaxes
implementadas. **Mudanças radicais são isoladas em um único
arquivo.**

## O que isto NÃO resolve

- **Não há ainda nenhuma sintaxe alternativa**. A
  modularização cria o esqueleto; o conteúdo de sintaxes
  compactas é tema dos próximos exps.
- **Tokens continuam fixos**. Uma sintaxe que precise de tokens
  novos (ex: token `inferido_pela_posição`) vai exigir extensão
  da interface.
- **Performance não muda**. Modularização é infraestrutura para
  pesquisa, não otimização para produção. A fusão para
  performance fica para depois de a sintaxe estar fechada.

## Pontos a registrar

1. **A separação algoritmo ↔ sintaxe é definida agora**. Mudar
   uma não pode mais quebrar a outra acidentalmente.

2. **21/21 byte-idênticos**: a modularização não introduziu
   regressão em nenhum dataset testado.

3. **A interface é minimal por design** — vai evoluir conforme
   sintaxes futuras pedirem capacidades novas. Não premature
   abstraction.

4. **Cada sintaxe é auto-contida**: encoder + decoder na mesma
   classe, mesmas regras. Impossível um encoder gerar algo que
   o decoder dela não sabe ler.

5. **Output organizado por sintaxe** facilita comparação visual
   entre formatos quando mais de uma estiver implementada.

## O que este experimento não mostra

- Que a interface é suficiente para sintaxes radicalmente
  diferentes (binary-in-text, inferida-pela-posição, etc.)
- Ganho real em bytes (depende de sintaxes implementadas)
- Comportamento sob fusão algoritmo+sintaxe (proposta para
  depois)

## Próximo experimento natural

**Primeira sintaxe compacta** como segunda implementação de
`Syntax`. Implementar 1 das 2 direções da nota
[`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md):

- Direção 1: marcadores compactos explícitos (símbolos de 1
  char)
- Direção 2: marcadores inferidos pela ordem/gramática

Sugestão: começar pela **Direção 1** (compacta explícita) por
ser mais conservadora e fácil de medir. Direção 2 é mais
radical e merece experimento próprio.
