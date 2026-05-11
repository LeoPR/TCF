"""Gera amostras grandes (1000 linhas) seguindo as regras de ideias.md.

Determinista por seed. Sem dependencias externas (stdlib apenas).

Uso:
    python gerar.py                # gera todos em amostras/grandes/
    python gerar.py datas          # gera apenas datas.csv
    python gerar.py --n 5000       # tamanho customizado
    python gerar.py --seed 42      # seed customizado
"""

import argparse
import csv
import random
import string
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

OUT = Path(__file__).parent / "amostras" / "grandes"

# -- pools sinteticos (curtos, suficientes para variar) --
PRIMEIROS_NOMES = [
    "Maria", "Joao", "Ana", "Carlos", "Pedro", "Beatriz", "Lucas",
    "Julia", "Rafael", "Paula", "Bruno", "Clara", "Diego", "Erica",
    "Fabio", "Gabi", "Heitor", "Igor", "Jose", "Mariana",
]
SOBRENOMES = [
    "Silva", "Souza", "Lima", "Costa", "Pereira", "Santos", "Oliveira",
    "Rodrigues", "Alves", "Ferreira", "Gomes", "Martins", "Araujo",
    "Carvalho", "Melo", "Dias", "Cruz", "Paiva", "Faria", "Macedo",
]
DOMINIOS_EMAIL = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "uol.com.br"]
UF = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "CE", "PE", "GO",
      "DF", "AM", "MA", "PA", "MT", "MS", "RO", "AC", "RR", "AP",
      "TO", "SE", "AL", "PB", "RN", "PI", "ES"]
PAISES_PARETO = (["Brasil"] * 90 + ["Estados Unidos"] * 5 +
                 ["Argentina"] * 2 + ["Mexico", "Portugal", "Japao"])
MKT_SEGMENT = ["BUILDING", "AUTOMOBILE", "MACHINERY", "HOUSEHOLD", "FURNITURE"]
PRIORIDADE = ["1-URGENT", "2-HIGH", "3-MEDIUM", "4-NOT SPECIFIED", "5-LOW"]
EDUCATION = [
    "Bachelors", "HS-grad", "Some-college", "Masters", "Doctorate",
    "11th", "Assoc-acdm", "Assoc-voc", "9th", "10th", "12th",
    "Prof-school", "7th-8th", "5th-6th", "Preschool", "1st-4th",
]
PRODUTOS_NOME = ["Caneta", "Caderno", "Lapis", "Regua", "Borracha",
                 "Mochila", "Apontador", "Marcador", "Estojo", "Grampeador"]
ESPECIES_GENERO = {
    "Maca": ("Apple", "Malus domestica", ["Fuji", "Gala", "Verde", "Argentina"]),
    "Banana": ("Banana", "Musa acuminata", ["Prata", "Nanica", "Maca", "Ouro"]),
    "Laranja": ("Orange", "Citrus sinensis", ["Pera", "Bahia", "Lima"]),
    "Limao": ("Lime", "Citrus aurantifolia", ["Tahiti", "Galego", "Siciliano"]),
    "Cachorro": ("Dog", "Canis lupus familiaris",
                 ["Labrador", "Golden", "Pastor", "Poodle"]),
    "Gato": ("Cat", "Felis catus", ["Siames", "Persa", "Maine Coon"]),
}


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {name}: {len(rows)} linhas -> {path}")


# -- 1. Datas --
def gerar_datas(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    base = date(2020, 1, 1)
    rows = []
    meses_pt = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    for i in range(n):
        offset = rnd.randint(0, 365 * 7)
        d = base + timedelta(days=offset)
        h = rnd.randint(0, 23)
        m = rnd.randint(0, 59)
        s = rnd.randint(0, 59)
        dt = datetime(d.year, d.month, d.day, h, m, s)
        rows.append({
            "id": i + 1,
            "iso": d.isoformat(),
            "br_slash": d.strftime("%d/%m/%Y"),
            "br_hifen": d.strftime("%d-%m-%Y"),
            "us_slash": d.strftime("%m/%d/%Y"),
            "extenso_pt": f"{d.day} de {meses_pt[d.month - 1]} de {d.year}",
            "iso_hora": dt.isoformat(),
            "unix_ts": int(dt.timestamp()),
            "com_tz": dt.isoformat() + "-03:00",
        })
    return rows


# -- 2.1 Nomes --
def gerar_nomes(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        prim = rnd.choice(PRIMEIROS_NOMES)
        sob1 = rnd.choice(SOBRENOMES)
        sob2 = rnd.choice(SOBRENOMES)
        rows.append({
            "id": i + 1,
            "simples": prim,
            "composto": f"{prim} {sob1}",
            "multi_sobrenome": f"{prim} {sob1} {sob2}",
            "com_titulo": f"Sr. {prim} {sob1}" if i % 2 else f"Sra. {prim} {sob1}",
            "com_inicial": f"{prim[0]}. {sob1}",
        })
    return rows


# -- 2.2/2.3 CPF/CNPJ --
def gerar_cpf_cnpj(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    base_empresas = [rnd.randint(10000000, 99999999) for _ in range(n // 4 + 1)]
    for i in range(n):
        cpf_n = f"{rnd.randint(10**10, 10**11 - 1):011d}"
        emp = rnd.choice(base_empresas)
        filial = rnd.randint(1, 5)
        cnpj_n = f"{emp:08d}{filial:04d}{rnd.randint(10, 99):02d}"
        rows.append({
            "id": i + 1,
            "cpf_fmt": f"{cpf_n[:3]}.{cpf_n[3:6]}.{cpf_n[6:9]}-{cpf_n[9:]}",
            "cpf_sem_mask": cpf_n,
            "cnpj_fmt": f"{cnpj_n[:2]}.{cnpj_n[2:5]}.{cnpj_n[5:8]}/{cnpj_n[8:12]}-{cnpj_n[12:]}",
            "cnpj_sem_mask": cnpj_n,
            "filial_num": filial,
        })
    return rows


# -- 3.1 Telefones --
def gerar_telefones(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        ddd = rnd.choice([11, 21, 31, 41, 48, 51, 61, 71, 81, 85])
        n1 = rnd.randint(10000, 99999)
        n2 = rnd.randint(1000, 9999)
        rows.append({
            "id": i + 1,
            "br_celular_fmt": f"({ddd}) 9{n1}-{n2}",
            "br_celular_sem": f"{ddd}9{n1}{n2}",
            "br_fixo_fmt": f"({ddd}) {rnd.randint(2000, 5999)}-{rnd.randint(1000, 9999)}",
            "com_ddi": f"+55 {ddd} 9{n1}-{n2}",
            "tpch_style": f"{ddd}-{rnd.randint(100, 999)}-{rnd.randint(100, 999)}-{rnd.randint(1000, 9999)}",
        })
    return rows


# -- 3.2 Emails --
def gerar_emails(n: int, seed: int, dominios: int = 5) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    pool = DOMINIOS_EMAIL[:dominios]
    for i in range(n):
        prim = rnd.choice(PRIMEIROS_NOMES).lower()
        sob = rnd.choice(SOBRENOMES).lower()
        d = rnd.choice(pool)
        rows.append({
            "id": i + 1,
            "um_dominio": f"user{i:04d}@gmail.com",
            "multi_dominio": f"{prim}.{sob}@{d}",
            "com_tag": f"{prim}.{sob}+tag{i}@gmail.com",
        })
    return rows


# -- 4.1 IDs --
def gerar_ids(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    orgs = ["ACME", "TECH", "LOGI"]
    depts = ["FIN", "OPS", "MKT"]
    for i in range(n):
        rows.append({
            "id": i + 1,
            "sequencial": i + 1,
            "padded_4": f"{i + 1:04d}",
            "com_prefixo": f"INV-2026-{i + 1:04d}",
            "tpch_style": f"Customer#{i + 1:09d}",
            "uuid_v4": "-".join(["".join(rnd.choices(string.hexdigits.lower(), k=k))
                                  for k in (8, 4, 4, 4, 12)]),
            "hierarquico": f"{rnd.choice(orgs)}-{rnd.choice(depts)}-USER-{i % 100:02d}",
        })
    return rows


# -- 4.2 URLs --
def gerar_urls(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    cats = ["eletronicos", "roupa", "celular", "livro", "casa"]
    subs = ["tv", "celular", "notebook", "tablet", "fone"]
    for i in range(n):
        cat = rnd.choice(cats)
        sub = rnd.choice(subs)
        rows.append({
            "id": i + 1,
            "curta": "example.com",
            "com_path_raso": f"https://example.com/page-{i + 1}",
            "padrao_id_variavel": f"https://api.example.com/v1/users/{i + 1}",
            "hierarquica": f"https://shop.example.com/cat-{cat}/sub-{sub}/item-{i + 1:04d}",
        })
    return rows


# -- 4.3 Enderecos --
def gerar_enderecos(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    cidades = [("Sao Paulo", "SP", "01310"), ("Rio de Janeiro", "RJ", "22640"),
               ("Belo Horizonte", "MG", "30130"), ("Salvador", "BA", "40020"),
               ("Curitiba", "PR", "80010"), ("Porto Alegre", "RS", "90010"),
               ("Recife", "PE", "50050"), ("Fortaleza", "CE", "60110")]
    for i in range(n):
        cidade, uf, cep_pre = rnd.choice(cidades)
        cep_suf = f"{rnd.randint(0, 999):03d}"
        rows.append({
            "id": i + 1,
            "cep_fmt": f"{cep_pre}-{cep_suf}",
            "cep_sem": f"{cep_pre}{cep_suf}",
            "logradouro": rnd.choice(["Av. Principal", "Rua das Flores", "Av. Brasil", "Rua XV"]),
            "numero": rnd.randint(1, 9999),
            "cidade": cidade,
            "uf": uf,
        })
    return rows


# -- 5.1 Produtos --
def gerar_produtos(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    cores = ["Azul", "Vermelha", "Preta", "Verde", "Branca"]
    for i in range(n):
        nome = rnd.choice(PRODUTOS_NOME)
        cor = rnd.choice(cores)
        rows.append({
            "id": i + 1,
            "nome_simples": nome,
            "sku": f"PRD-2026-{i + 1:05d}",
            "com_marca_modelo": f"Marca{rnd.randint(1, 10)} {nome} {cor}",
            "categoria": rnd.choice(["Papelaria", "Roupas", "Eletronicos", "Casa"]),
        })
    return rows


# -- 5.2 Monetarios --
def gerar_monetarios(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        # bimodal: 80% perto de baseline, 10% zero, 10% extremo
        r = rnd.random()
        if r < 0.10:
            v = 0.0
        elif r < 0.20:
            v = rnd.uniform(50000, 500000)
        else:
            v = rnd.uniform(1, 1000)
        v = round(v, 2)
        rows.append({
            "id": i + 1,
            "br_fmt": f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "us_fmt": f"${v:,.2f}",
            "iso_brl": f"BRL {v:.2f}",
            "sem_moeda": f"{v:.2f}",
            "centavos_inteiro": int(v * 100),
        })
    return rows


# -- 6.2 Enums --
def gerar_enums(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        rows.append({
            "id": i + 1,
            "bool_card2": rnd.choice([True, False]),
            "sex_card2": rnd.choice(["M", "F"]),
            "mktsegment_card5": rnd.choice(MKT_SEGMENT),
            "prioridade_prefixo": rnd.choice(PRIORIDADE),
            "education_card16": rnd.choice(EDUCATION),
            "uf_card27": rnd.choice(UF),
            "pais_pareto": rnd.choice(PAISES_PARETO),
        })
    return rows


# -- 7. Numericos --
def gerar_numericos(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        idade = rnd.randint(18, 65)
        # bimodal com zero majoritario (capital-gain style)
        cap = 0 if rnd.random() < 0.92 else rnd.randint(1000, 99999)
        rows.append({
            "id": i + 1,
            "int_pequeno": idade,
            "int_medio": rnd.randint(10000, 999999),
            "int_grande": rnd.randint(10**9, 10**12),
            "decimal_2": round(rnd.uniform(0, 10000), 2),
            "decimal_quantizado": round(rnd.randint(0, 10) / 100, 2),
            "com_zeros_dominantes": cap,
        })
    return rows


# -- 8. Especies --
def gerar_especies(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    generos = list(ESPECIES_GENERO.keys())
    for i in range(n):
        g = rnd.choice(generos)
        en, sci, vars_ = ESPECIES_GENERO[g]
        v = rnd.choice(vars_)
        rows.append({
            "id": i + 1,
            "comum_pt": g,
            "comum_en": en,
            "cientifico": sci,
            "com_variedade_pt": f"{g} {v}",
        })
    return rows


# -- 10. Nulos (esparso 70%) --
def gerar_nulos(n: int, seed: int, pct_null: float = 0.7) -> list[dict]:
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        is_null = rnd.random() < pct_null
        rows.append({
            "id": i + 1,
            "vazio": "" if is_null else f"valor_{i}",
            "null_literal": "NULL" if is_null else f"valor_{i}",
            "na_curto": "N/A" if is_null else f"valor_{i}",
            "interrogacao": "?" if is_null else f"valor_{i}",
            "nao_informado": "nao informado" if is_null else f"valor_{i}",
        })
    return rows


GERADORES = {
    "datas": gerar_datas,
    "nomes-pessoas": gerar_nomes,
    "cpf-cnpj": gerar_cpf_cnpj,
    "telefones": gerar_telefones,
    "emails": gerar_emails,
    "ids": gerar_ids,
    "urls": gerar_urls,
    "enderecos": gerar_enderecos,
    "produtos": gerar_produtos,
    "monetarios": gerar_monetarios,
    "enums": gerar_enums,
    "numericos": gerar_numericos,
    "especies": gerar_especies,
    "nulos": gerar_nulos,
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("alvo", nargs="?", default="todos",
                   help="Nome do gerador ou 'todos'")
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    alvos = list(GERADORES.keys()) if args.alvo == "todos" else [args.alvo]
    if args.alvo != "todos" and args.alvo not in GERADORES:
        print(f"alvo desconhecido: {args.alvo}", file=sys.stderr)
        print(f"disponiveis: {', '.join(GERADORES)}", file=sys.stderr)
        sys.exit(1)

    print(f"gerando n={args.n}, seed={args.seed} -> {OUT}")
    for name in alvos:
        rows = GERADORES[name](args.n, args.seed)
        write_csv(f"{name}.csv", rows)


if __name__ == "__main__":
    main()
