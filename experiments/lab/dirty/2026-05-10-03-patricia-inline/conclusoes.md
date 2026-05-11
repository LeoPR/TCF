# Conclusões — comportamento observado

## Cenário A — nomes simples (Patricia inativo)

Patricia não fatorou (igual exp 02): 5 nós top-level, nenhum filho.
Body do TCF inline:

```
<body>
  no1: 2x folha "Ana"
  no2: 1x folha "Bob"
  1x ref:no1
  2x ref:no2
  no3: 3x folha "Carlos"
  no4: 1x folha "Diana"
  2x ref:no1
  no5: 1x folha "Edu"
  ... (28 refs adicionais)
</body>
```

5 declarações inline (na ordem em que `Ana`, `Bob`, `Carlos`, `Diana`,
`Edu` aparecem pela 1ª vez). 28 refs depois. **Zero decls tardias** —
sem Patricia, não há pais sem ocorrência.

### Comparação de bytes com exp 02

| | Bytes |
|---|---|
| exp 02 (separado) | 571 |
| exp 03 (inline) | 689 |
| diferença | +118 (+20.7%) |

O inline aumentou em A. Causa: cada string aparece uma vez
explicitamente no body (na 1ª ocorrência, com `folha "..."` e
overhead de marcador), enquanto no exp 02 ela aparecia uma vez no
header (`no1 = folha "Ana"`) e todas as referências do body eram
curtas (`ref:no1`). O custo da decl no body do exp 03 é maior que a
economia obtida ao remover os marcadores de seção `<patricia>` e o
header.

Esta observação vale só neste cenário (A) e neste tamanho. Não
generaliza.

## Cenário B — identificadores hierárquicos (Patricia ativo)

Body do TCF inline (extrato):

```
<body>
  no1: 2x filho_de(no2) + "1"          ← USR0001 1a ocorrencia
  no3: 1x filho_de(no2) + "2"          ← USR0002 1a ocorrencia
  no4: 2x filho_de(no5) + "1"          ← PRD0001 1a ocorrencia
  no6: 3x filho_de(no2) + "3"          ← USR0003 1a ocorrencia
  no7: 1x filho_de(no5) + "2"          ← PRD0002 1a ocorrencia
  ... (mais 1as ocorrencias)
  no16: 2x filho_de(no17) + "10"       ← USR0010 (note: pai eh no17, nao no2)
  no18: 1x filho_de(no5) + "5"         ← PRD0005
  2x ref:no1
  1x ref:no4
  2x ref:no3
  no2: decl filho_de(no17) + "0"       ← USR000 (pai sem ocorrencia)
  no5: decl folha "PRD000"             ← PRD000 (pai sem ocorrencia)
  no17: decl folha "USR00"             ← USR00 (pai sem ocorrencia)
</body>
```

**Forward refs em ação**: a linha 1 do body declara `no1` como filho
de `no2`, mas `no2` só aparece na decl tardia 27 linhas depois.

**Encadeamento de forward refs**: `no2` (decl tardia) referencia
`no17` (decl tardia que vem depois). O decoder em 2 passadas resolve
ambos.

### Distribuição das linhas no TCF inline

| Categoria | Quantidade |
|---|---|
| decls inline (1ª ocorrência) | 15 |
| decls tardias (sem ocorrência) | 3 |
| refs (ocorrência em nó já visto) | 5 |
| total linhas no body | 23 |

15 das 30 linhas do CSV viraram decl inline (são as 15 strings únicas
do dataset). 9 das 30 ocorrências viraram refs adjacentes (RLE
agrupou). As 3 decls tardias correspondem aos 3 nós Patricia internos
(`USR000`, `PRD000`, `USR00`).

### Comparação de bytes com exp 02

| | Bytes |
|---|---|
| exp 02 (separado) | 848 |
| exp 03 (inline) | 824 |
| diferença | -24 (-2.8%) |

O inline ficou marginalmente menor em B. Causa: muitos nós aparecem 1
ou 2 vezes (cardinalidade alta em relação a N=30), de modo que o
custo de declaração inline ≈ custo da decl no header. A pequena
economia vem da remoção dos marcadores de seção `<patricia>`.

A magnitude (-24 bytes, -2.8%) é descritiva, não conclusiva. Em outros
cenários — N maior, mais ocorrências por nó, mais nós internos
Patricia — o sinal e a magnitude podem mudar.

## Pontos a registrar

1. **Forward ref funciona**. Um filho Patricia pode ser declarado
   antes do seu pai aparecer; decoder de 2 passadas resolve. Em B,
   `no1` (1ª linha do body) precisou esperar `no2` (linha 23 do body)
   ser declarado.

2. **Encadeamento de forward refs também funciona**. `no2` referencia
   `no17`, que vem depois de `no2`. Não há limite imposto pelo
   algoritmo; apenas o requisito de que toda ref termine em uma decl
   no fim.

3. **Sinal da diferença de bytes depende do cenário**. Em A (sem
   Patricia, baixa cardinalidade) inline aumentou; em B (com
   Patricia, cardinalidade alta) inline reduziu marginalmente. Não
   há serialização universalmente menor entre as duas testadas.

4. **Roundtrip preservado em ambos**. Decode de 2 passadas reconstrói
   exatamente as 50 linhas de A e as 30 linhas de B sem perda.

5. **A árvore é a mesma em 02 e 03**. Os ids visíveis no arquivo são
   diferentes (numeração por ordem de aparição vs ordem de criação na
   construção), mas a estrutura pai/filho é byte-a-byte equivalente.

## O que este experimento NÃO mostra

- Comportamento em N maior que 50.
- Comportamento em colunas com cardinalidade intermediária (10–100
  valores únicos), onde a relação entre decls inline, refs e decls
  tardias muda.
- Comparação com formatos compactos (sem marcadores verbosos).
- Robustez do decoder contra inputs malformados.
- Comparação de tempo de encode/decode (não foi medido).
- Outras estratégias de serialização (ex: refs por slot `?N`,
  declarações pós-ordem topológica). Apenas duas — separado e inline
  — foram testadas.
