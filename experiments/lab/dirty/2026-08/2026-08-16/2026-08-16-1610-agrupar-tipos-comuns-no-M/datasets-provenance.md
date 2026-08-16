# Procedência — sintético, e a variável é `k`

## Os dados

Tudo gerado em `run.py`, sem `Z:`, determinístico.

| conjunto | forma | por que |
|---|---|---|
| cadastro com flags | 9 colunas, n=2000, `random.Random(20260816)` | **5 flags `S`/`N`** = o exemplo do owner ("true/false") + `uf`/`origem`/`destino` do mesmo domínio (k=6) |
| curva de domínio | 2 colunas, n=2000, `random.Random(7)`, k ∈ {2,6,50,500,2000} | isola **k** como variável — mesmo n, mesma forma, só o tamanho do domínio muda |
| contra-prova disjunta | 2 colunas, k ∈ {50,500}, `random.Random(11)` | `cidade-*` × `produto-*` — mesma cardinalidade, **zero sobreposição** |

**A CONSTANTE**: em cada bloco só uma coisa varia. No Bloco 2 é `k` (n, forma dos valores e
distribuição são idênticos). No Bloco 4 é a sobreposição (k e n idênticos).

## O que os números são — e o que NÃO são

Todas as medidas de "compartilhar" são **TETOS**, não ganhos de um mecanismo implementado:
mede-se o quanto existe de **duplicado** hoje (a tabela do `@dict` que aparece nas duas
colunas), que é o limite superior do que um dicionário compartilhado poderia recuperar. Um
mecanismo real pagaria overhead de referência — logo o ganho real é **menor** que o teto.

Os números de "candidato certo" (Bloco 3) **não são teto** — são medição direta: `encode` da
mesma coluna como flat, com RT validado.

## Vieses declarados

- **Valores aleatórios uniformes.** Domínio real costuma ser enviesado (Zipf), o que **aumenta**
  o ganho do dict e muda a curva de `k`. Não medido.
- **Sobreposição total ou zero.** O caso realista (sobreposição parcial — 70% das cidades em
  comum) **não foi medido**, e é justamente onde o "híbrido V2" do H-GDICT viveria.
- **k=2000 com n=2000** cai fora do gate `K < N` do `dict_v2b.py:61` — o `@dict` não se aplica
  e o 0% dali é artefato do gate, não propriedade do compartilhamento.
- **Flags como string `S`/`N`**, não `bool` nativo: bool nativo ejetaria a tabela para o `.8H`
  (lab `1400` Bloco 4), o que mudaria o assunto. Mantido em string de propósito, para o teste
  ficar sobre o `.8M`.
