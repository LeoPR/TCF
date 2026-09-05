**Português** · [English](post.en.md)

# Resumo curto (reels / feed), apontando para o artigo e o repositório

> Fonte: [`../2026-09-04-lancamento.md`](../2026-09-04-lancamento.md). Todo número vem do
> README. Fora do gate de snippets por orçamento de caracteres; os mesmos exemplos rodam pelo
> artigo.
>
> **As três primeiras linhas** são as que aparecem antes do "ver mais", e não têm jargão de
> propósito.
>
> **Figuras** em [`figuras/pt-BR/`](figuras/pt-BR/), geradas por
> `python scripts/make_divulgacao_figuras.py`. Nada é ilustração: os bytes são medidos e o wire
> desenhado é o que o `encode` devolve.

---

**Comprimir uma tabela sem transformar ela num arquivo que ninguém consegue abrir**

Quando um sistema guarda ou transmite uma tabela, ele escolhe entre formatos que repetem
demais, como o JSON, que grava o nome de cada campo em toda linha, e formatos que comprimem
bem mas viram um bloco opaco, como o gzip, que você só lê depois de descomprimir inteiro.

O TCF fica no meio. Comprime parecido com um gzip, e o resultado continua texto que você abre
e lê. Um cadastro de quatro pessoas: 451 bytes em JSON, 277 em CSV, 242 em TCF. E ele volta
idêntico, sempre.

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf
Ana Souza
Bruno Lima
...
*3|Sao Paulo
Rio de Janeiro
```

O `*3|Sao Paulo` diz que há três linhas iguais ali, escritas uma vez. É essa estrutura visível
que permite perguntar sem descomprimir:

<!-- doctest: skip -->
```python
v = view(blob)                                  # não descomprime nada
v.count()                                       # 6
v.where("cidade", "Sao Paulo").sum("valor")     # 470.0, toca só cidade e valor
v.group_count("plano")                          # {'Premium': 4, 'Basic': 2}
```

Em dado real, 9 tabelas com 136 mil linhas, são 33% a menos que o CSV cru.

Os limites, porque eles importam: sob gzip os formatos empatam, o CSV passa no tamanho
minúsculo, e a otimização de velocidade é o próximo ciclo.

`pip install tcf-format` · Python 3.10+ · zero dependências · MIT · pré-1.0.

Escrevi um artigo com o funcionamento, as medições e os limites:
👉 [link do artigo, preencher depois de publicar]

O código e as medições:
👉 https://github.com/LeoPR/TCF

#Python #Compressao #DataEngineering #OpenSource #FormatosDeDados
