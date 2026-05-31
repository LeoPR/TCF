# Algoritmo — decl aninhada recursiva

## Encoder

Mantém os mesmos elementos do exp 03 (`map_emit`, `declarado`,
`get_eid`, body com decls inline + refs), mas com duas mudanças:

1. **`_render_lado_filho(no)`** — renderiza `filho_de(...) + "X"`.
   Se o pai já está em `declarado`, gera ref simples
   (`filho_de(no2) + "X"`). Se não, **chama `render_decl_aninhada(pai)`
   inline** e usa o resultado.

2. **`render_decl_aninhada(no_id)`** — gera `no{eid}=decl <forma>`.
   Marca esse eid como declarado. **Se o pai do pai também não
   estiver declarado**, chama a si mesma para o avô, e assim por
   diante até atingir um nó top-level ou um nó já declarado.

3. **Eliminação da fase 2 (decls tardias)**. No exp 03 havia um
   loop pós-body para emitir decls de pais Patricia ainda
   pendentes. Aqui esse loop não existe — todo pai necessário já
   foi declarado dentro de uma decl filho.

### Pseudo-código

```python
def encode_aninhado(nos, body_rle):
    out = ["<body>"]
    for no_id, count in body_rle:
        eid = get_eid(no_id)
        if eid not in declarado:
            out.append(render_decl_externa(no_id, count))
        else:
            out.append(f"  {count}x ref:no{eid}")  # ou sem count se ==1
    out.append("</body>")
    return "\n".join(out)

def render_decl_externa(no_id, count):
    n = nos[no_id]
    if n.pai_id is None:
        forma = f'folha "{n.fragmento}"'
    else:
        forma = _render_lado_filho(n)
    declarado.add(get_eid(no_id))
    return f"  no{get_eid(no_id)}: {count}x {forma}"  # ou sem count

def _render_lado_filho(n):
    if n.pai_id in {no_id_de(eid) for eid in declarado}:
        return f'filho_de(no{get_eid(n.pai_id)}) + "{n.fragmento}"'
    else:
        pai_decl = render_decl_aninhada(n.pai_id)  # RECURSIVO
        return f'filho_de({pai_decl}) + "{n.fragmento}"'

def render_decl_aninhada(no_id):
    n = nos[no_id]
    eid = get_eid(no_id)
    if n.pai_id is None:
        forma = f'decl folha "{n.fragmento}"'
    else:
        forma = "decl " + _render_lado_filho(n)  # recursa se pai não decl
    declarado.add(eid)
    return f"no{eid}={forma}"
```

### Ordem de invocação

Para uma decl externa cujo nó é folha N3 com pai N5 com avô N7,
nenhum dos quais declarado:

1. `render_decl_externa(3)` chama `_render_lado_filho(N3)`.
2. N3.pai_id = N5 não declarado → chama `render_decl_aninhada(5)`.
3. Em `render_decl_aninhada(5)`, N5 não é folha → forma é
   `"decl " + _render_lado_filho(N5)`.
4. `_render_lado_filho(N5)`: N5.pai_id = N7 não declarado → chama
   `render_decl_aninhada(7)`.
5. `render_decl_aninhada(7)`: N7 é folha (top) → `"decl folha \"...\""`.
   Marca N7 declarado. Retorna `no{eid7}=decl folha "..."`.
6. `_render_lado_filho(N5)` retorna `filho_de(no{eid7}=decl folha "...") + "..."`.
7. `render_decl_aninhada(5)` retorna `no{eid5}=decl filho_de(no{eid7}=...) + "..."`.
   Marca N5 declarado.
8. `_render_lado_filho(N3)` retorna `filho_de(no{eid5}=decl filho_de(no{eid7}=...) + "...") + "..."`.
9. `render_decl_externa(3)` retorna a linha final com `no{eid3}:`.

A profundidade da recursão é igual à profundidade da árvore Patricia.

### Ordem de eids

Pela ordem de invocação de `get_eid`. Quando uma decl externa exige
seu pai, o eid do pai é alocado **dentro** da renderização da decl
externa. Logo o eid do pai pode ser maior que o do filho — o que é
normal nesta serialização.

Exemplo (D2): Marina é a 1ª linha do body. Marina recebe `eid=1`.
Dentro da renderização, seu pai `Mar` recebe `eid=2`. Output:

```
no1: filho_de(no2=decl folha "Mar") + "ina"
```

## Decoder

Parser recursivo manual. Regex não é adequado porque a sintaxe é
recursiva.

### Gramática

```
linha           := decl_externa | ref
decl_externa    := "no" INT ":" count_opc forma
ref             := count_opc "ref:no" INT
count_opc       := INT "x" | ε

forma           := folha | filho
folha           := 'folha "' STR '"'
filho           := 'filho_de(' pai_descritor ')' ' + "' STR '"'
pai_descritor   := "no" INT                          # ref a pai
                 | "no" INT "=decl" SP forma         # decl aninhada
```

### Implementação

`Parser` com cursor de posição (`pos`) e métodos `consume`,
`consume_int`, `consume_string`, `try_consume_count`, `peek`.

A função central é `_parse_forma_dentro(p, nos, eid_atual)`: parseia
uma forma e registra `nos[eid_atual] = (pai_eid_ou_None, frag)`. Se
encontra `=decl`, chama a si mesma para o eid aninhado **antes** de
registrar o eid atual — assim a ordem de registro respeita a cadeia.

Após a passada única pelo body, executa reconstrução com cache:

```python
def texto(eid):
    if eid in cache: return cache[eid]
    pai_eid, frag = nos[eid]
    t = frag if pai_eid is None else texto(pai_eid) + frag
    cache[eid] = t
    return t
```

Forward refs **não são necessárias** porque pais sempre são
declarados antes de serem referenciados pela 2ª vez em diante. Na
1ª vez já vêm embutidos. A passada única é suficiente.

## Comparação com exp 03/04

| Aspecto | Exp 03/04 | Exp 05 |
|---|---|---|
| onde pais Patricia são declarados | `<patricia>` separado (02) ou decl tardia no fim do body (03) | embutidos na 1ª decl filho que os precisa |
| forward refs no encode | usadas em 03/04 (pais ainda não declarados) | inexistentes |
| decode em 2 passadas | sim (03/04) | não, 1 passada |
| ordem dos nós no body | folhas primeiro (na 1ª ocorrência), pais no fim | decl folha + decl(s) pai(s) aparecem juntas, na mesma linha |
| chars de marcador "decl" | `decl ` por pai (no 03/04) | `decl ` por pai (no 05) — mesmo número total |

Os bytes não foram comparados numericamente porque os 4 datasets do
exp 05 são distintos dos do 03/04. Comparação direta exigiria
re-rodar exp 04 com mesmos inputs ou re-rodar exp 05 com inputs do
exp 04.
