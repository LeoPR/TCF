---
title: FUNIL DE FECHAMENTO — JSON na linguagem → datasets da linguagem → estruturas gerais
type: report
status: aberta
created: 2026-07-17
related:
  - experiments/lab/dirty/notas/dataset-json-dois-contratos.md
  - experiments/lab/dirty/notas/matriz-caminhos-hierarquia-2026-07-17.md
  - experiments/lab/dirty/notas/escala-implementacao-paridade-json.md
  - experiments/lab/dirty/notas/perfil-json-like-condicoes-parametro.md
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md
  - docs/adr/0033-hierarchical-codec-weld.md
---

# Funil de fechamento — JSON na linguagem → datasets da linguagem → estruturas gerais

**[recomendação]** Esta nota fixa uma régua de utilidade e ROI. Ela não reduz a ambição do TCF e
não transforma JSON em dependência do core. Seu objetivo é permitir que uma etapa seja declarada
funcional e encerrada antes de cobrir toda a amplitude teórica das estruturas de dados.

## 1. A perspectiva

O TCF não lê nem escreve texto JSON. O caminho relevante é composto por dois contratos:

```text
texto JSON -> biblioteca da linguagem -> primitivas da linguagem
primitivas -> TCF -> primitivas idênticas
```

A biblioteca de JSON resolve ou perde tudo que pertence ao primeiro contrato antes de o TCF receber
o dataset. Duplicate keys, coerções e extensões não transmissíveis não são responsabilidade do core.
O TCF começa na estrutura primitiva já construída.

A imagem **possível** das bibliotecas é maior que o perfil **comum** usado por grande parte das APIs.
Essa diferença é útil: possibilidade define o teto; frequência, custo e risco definem a ordem.

## 2. Os cinco patamares

### J0 — dataset JSON-language comum

Perfil mínimo de produção, deliberadamente regular:

- raiz como coleção de registros (`list[dict]`);
- objetos aninhados, campos opcionais e `null`;
- arrays homogêneos por região estrutural;
- arrays aninhados e vazios;
- `str`, `int`, número finito, `bool` e `None`;
- chaves string, Unicode transmissível e framing de LF;
- round-trip do dataset primitivo, não do texto JSON original.

**Estado**: capacidade implementada no `.8H`. É legítimo chamá-la de **JSON-like comum fechado**.
Não implica cobertura de toda combinação recursiva possível.

### J1 — documento JSON-language comum

J0 mais as formas usuais de raiz:

- objeto único;
- array na raiz;
- escalar e `null` na raiz;
- estruturas sem folhas (`{}`, `[]`, `[{}]`) com contagem explícita.

**Próximo marco recomendado**: P4b. Ao fechar J1, o TCF cobre o fluxo comum de documentos e datasets
produzidos pelas bibliotecas nativas sem depender de um wrapper artificial de registros.

### J2 — imagem recursiva completa das primitivas JSON

Fecho recursivo do mapeamento lossless da biblioteca:

```text
dict[str, D] | list[D] | str | int | número finito | bool | null
```

Inclui unions e heterogeneidade em qualquer nível: tipos distintos entre registros, arrays mistos e
alternância objeto/array/escalar. Essas formas são possíveis nas primitivas, mas não precisam bloquear
J0/J1 quando custo e frequência não pagam o weld.

**Candidato principal**: P5. Tratar como expansão de capacidade posterior, possivelmente ainda antes
da versão 1.0, mas com pausa explícita após J1.

### L — datasets além do JSON da linguagem

Primitivas e tipos que a aplicação possui, mas cujo adaptador JSON perde, coage ou não transporta:

- `Decimal`, datetime, bytes e tuplas com identidade própria;
- NaN e infinitos tipados;
- mapas com chaves não-string;
- enums, IDs e tipos de domínio;
- objetos da linguagem convertidos por adaptadores declarados.

Aqui o TCF pode superar JSON, mas cada tipo precisa de semântica e wire próprios. Não copiar perdas
silenciosas das bibliotecas. A regra continua: representar ou falhar alto.

### G — estruturas gerais

Capacidades que ultrapassam a árvore de primitivas:

- referências compartilhadas e identidade;
- DAG, N:N, snowflake e grafos;
- schemas/contratos externos;
- lazy/query por subárvore e índices;
- múltiplas representações físicas por perfil.

É a ambição ampla do DatasetH/TCF, separada do fechamento JSON-language.

## 3. Regra de passagem

Um patamar pode ser fechado quando:

1. seu domínio está definido por exemplos positivos e fronteiras fail-loud;
2. o round-trip é executável e pinado;
3. há pelo menos um corpus realista e um adversarial;
4. não existe corrupção silenciosa conhecida no domínio aceito;
5. o patamar seguinte está registrado, mas não é contado como dívida do atual.

A nomenclatura deve sempre incluir o patamar. Evitar “hierarquia completa” sem qualificador:

- `J0 fechado`: JSON-like comum em dataset de registros;
- `J1 fechado`: documento JSON-language comum, com raiz generalizada;
- `J2 fechado`: imagem recursiva das primitivas JSON;
- `L/G`: expansões além do JSON.

## 4. Ordem por ROI

```text
J0 já implementado
  -> J1 / P4b
  -> corrigir R0 e validar população
  -> observabilidade SideOutputs
  -> PAUSA e revisão do marco
  -> J2 / P5 se frequência e custo justificarem
  -> L por tipos de domínio demandados
  -> G por casos reais de relações e consulta
```

O perfil comum não deve ser definido somente por intuição. Para promover uma forma de J2 para J1,
exigir ao menos um destes sinais:

- aparece em corpus real de API/transmissão;
- bloqueia um usuário ou workflow concreto;
- fecha várias lacunas com um único mecanismo;
- reduz risco ou simplifica o contrato existente;
- tem implementação pequena e gate forte.

Caso contrário, registrar e adiar é uma conclusão válida.

## 5. O que aprender com as bibliotecas JSON

Os limites das bibliotecas são evidência de custo de design, não defeitos que o TCF precisa corrigir
agora. Eles ensinam quatro escolhas úteis:

- modelo pequeno e interoperável antes de extensões;
- comportamento lossy documentado não deve virar perda silenciosa no TCF;
- adaptadores resolvem política de origem; o core preserva primitivas recebidas;
- capacidades raras entram por representação explícita, não por tolerância implícita.

Portanto, estar temporariamente “preso” ao patamar JSON-language comum é um **critério de fechamento**,
não uma limitação arquitetural. J0/J1 entregam compatibilidade prática; J2/L/G preservam a direção de
crescimento sem manter o marco atual permanentemente aberto.

## 6. Sugestão de decisão

Adotar formalmente J0–J2/L/G como régua de roadmap:

- reconhecer J0 como fechado;
- fechar J1 com P4b;
- fazer uma pausa explícita depois de validade populacional e SideOutputs;
- reavaliar P5 como primeiro candidato J2, sem torná-lo condição retroativa de J1;
- manter L e G como trilhas orientadas por demanda e evidência real.

Essa divisão torna simultaneamente verdadeiras duas metas: o TCF cobre o básico usado hoje e continua
arquitetado para datasets mais amplos amanhã.
