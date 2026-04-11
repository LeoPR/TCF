# Quality Report — tpch-sf001

_Generated: 2026-04-11 07:04 UTC_

- **Source:** TPC-H Benchmark (via DuckDB tpch extension)
- **Origin:** https://www.tpc.org/tpch/
- **License:** TPC Fair Use Agreement
- **Citation:** Transaction Processing Performance Council (TPC). TPC Benchmark H (TPC-H) Specification.

## Schema Summary

| Table | Rows | Cols | PK | FKs |
|-------|------|------|-----|-----|
| `region` | 5 | 3 | `r_regionkey` | `—` |
| `nation` | 25 | 4 | `n_nationkey` | `n_regionkey` |
| `supplier` | 100 | 7 | `s_suppkey` | `s_nationkey` |
| `customer` | 1,500 | 8 | `c_custkey` | `c_nationkey` |
| `part` | 2,000 | 9 | `p_partkey` | `—` |
| `partsupp` | 8,000 | 5 | `ps_partkey, ps_suppkey` | `ps_partkey, ps_suppkey` |
| `orders` | 15,000 | 9 | `o_orderkey` | `o_custkey` |
| `lineitem` | 60,175 | 16 | `l_orderkey, l_linenumber` | `l_orderkey, l_partkey, l_suppkey` |

**Total:** 86,805 rows across 8 tables (61 columns combined)

## Table: `region`

- **Rows:** 5
- **Columns:** 3
- **PK:** `r_regionkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `r_regionkey` | int | 0 | 0 | 4 | 2.0000 | 1.5811 |
| `r_name` | string | 0 | 5 | — | — | — |
| `r_comment` | string | 0 | 5 | — | — | — |

### Top values (categorical columns)


**`r_name`** — distinct: 5, entropy: 2.3219 bits
- `MIDDLE EAST`: 1 (20.0%)
- `EUROPE`: 1 (20.0%)
- `ASIA`: 1 (20.0%)
- `AMERICA`: 1 (20.0%)
- `AFRICA`: 1 (20.0%)

**`r_comment`** — distinct: 5, entropy: 2.3219 bits
- `s are. furiously even pinto bea`: 1 (20.0%)
- `e dolphins are furiously about the care…`: 1 (20.0%)
- `c, special dependencies around `: 1 (20.0%)
- `ar packages. regular excuses among the …`: 1 (20.0%)
- ` foxes boost furiously along the carefu…`: 1 (20.0%)

### Sample rows (first 3)


| `r_regionkey` | `r_name` | `r_comment` |
|---|---|---|
| 0 | AFRICA | ar packages. regular excuses among the … |
| 1 | AMERICA | s are. furiously even pinto bea |
| 2 | ASIA | c, special dependencies around  |

## Table: `nation`

- **Rows:** 25
- **Columns:** 4
- **PK:** `n_nationkey`
- **FK:** `n_regionkey` → `region.r_regionkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `n_nationkey` | int | 0 | 0 | 24 | 12.0000 | 7.3598 |
| `n_name` | string | 0 | 25 | — | — | — |
| `n_regionkey` | int | 0 | 0 | 4 | 2.0000 | 1.4434 |
| `n_comment` | string | 0 | 25 | — | — | — |

### Top values (categorical columns)


**`n_name`** — distinct: 25, entropy: 4.6439 bits
- `VIETNAM`: 1 (4.0%)
- `UNITED STATES`: 1 (4.0%)
- `UNITED KINGDOM`: 1 (4.0%)
- `SAUDI ARABIA`: 1 (4.0%)
- `RUSSIA`: 1 (4.0%)

**`n_comment`** — distinct: 25, entropy: 4.6439 bits
- `usly ironic, pending foxes. even, speci…`: 1 (4.0%)
- `uriously unusual deposits about the sly…`: 1 (4.0%)
- `uctions. furiously unusual instructions…`: 1 (4.0%)
- `the slyly regular ideas. silent Tiresia…`: 1 (4.0%)
- `ss deposits wake across the pending fox…`: 1 (4.0%)

### Sample rows (first 3)


| `n_nationkey` | `n_name` | `n_regionkey` | `n_comment` |
|---|---|---|---|
| 0 | ALGERIA | 0 | furiously regular requests. platelets a… |
| 1 | ARGENTINA | 1 | instructions wake quickly. final deposi… |
| 2 | BRAZIL | 1 | asymptotes use fluffily quickly bold in… |

## Table: `supplier`

- **Rows:** 100
- **Columns:** 7
- **PK:** `s_suppkey`
- **FK:** `s_nationkey` → `nation.n_nationkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `s_suppkey` | int | 0 | 1 | 100 | 50.5000 | 29.0115 |
| `s_name` | string | 0 | 100 | — | — | — |
| `s_address` | string | 0 | 100 | — | — | — |
| `s_nationkey` | int | 0 | 0 | 24 | 13.2200 | 7.2955 |
| `s_phone` | string | 0 | 100 | — | — | — |
| `s_acctbal` | float | 0 | -966.2000 | 9,915.2400 | 4,009.3000 | 3,082.8416 |
| `s_comment` | string | 0 | 100 | — | — | — |

### Top values (categorical columns)


**`s_name`** — distinct: 100, entropy: 6.6439 bits
- `Supplier#000000100`: 1 (1.0%)
- `Supplier#000000099`: 1 (1.0%)
- `Supplier#000000098`: 1 (1.0%)
- `Supplier#000000097`: 1 (1.0%)
- `Supplier#000000096`: 1 (1.0%)

**`s_address`** — distinct: 100, entropy: 6.6439 bits
- `zaux5FTzToEg`: 1 (1.0%)
- `yeXt5WdcOUQVvdNCulURp4rSaxnuAwhxP9hzq`: 1 (1.0%)
- `wS,hHEibrFlCfN6I9xyPxSZKkGAAB4XbapMdy826`: 1 (1.0%)
- `wNZNHIg370XspE`: 1 (1.0%)
- `w5yO 0yjXou 8I4ffzADq,R8tD06x1vbeMpLJF2`: 1 (1.0%)

**`s_phone`** — distinct: 100, entropy: 6.6439 bits
- `34-876-912-6007`: 1 (1.0%)
- `34-869-118-7803`: 1 (1.0%)
- `34-860-229-1674`: 1 (1.0%)
- `34-852-489-8585`: 1 (1.0%)
- `34-748-308-3215`: 1 (1.0%)

_(showing 3 of 4 categorical columns — see metadata.json for full list)_

### Sample rows (first 3)

_ (showing 6 of 7 columns)_
| `s_suppkey` | `s_name` | `s_address` | `s_nationkey` | `s_phone` | `s_acctbal` |
|---|---|---|---|---|---|
| 1 | Supplier#000000001 | sdrGnXCDRcfriBvY0KL,ipCanOTyK t NN1 | 17 | 27-918-335-1736 | 5755.94 |
| 2 | Supplier#000000002 | TRMhVHz3XiFuhapxucPo1 | 5 | 15-679-861-2259 | 4032.68 |
| 3 | Supplier#000000003 | BZ0kXcHUcHjx62L7CjZSql7gbWQ6RPn5X | 1 | 11-383-516-1199 | 4192.4 |

## Table: `customer`

- **Rows:** 1,500
- **Columns:** 8
- **PK:** `c_custkey`
- **FK:** `c_nationkey` → `nation.n_nationkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `c_custkey` | int | 0 | 1 | 1,500 | 750.5000 | 433.1570 |
| `c_name` | string | 0 | 1,500 | — | — | — |
| `c_address` | string | 0 | 1,500 | — | — | — |
| `c_nationkey` | int | 0 | 0 | 24 | 11.8560 | 7.1676 |
| `c_phone` | string | 0 | 1,500 | — | — | — |
| `c_acctbal` | float | 0 | -994.7900 | 9,987.7100 | 4,454.5771 | 3,159.2992 |
| `c_mktsegment` | string | 0 | 5 | — | — | — |
| `c_comment` | string | 0 | 1,500 | — | — | — |

### Top values (categorical columns)


**`c_name`** — distinct: 1,500, entropy: 10.5507 bits
- `Customer#000001500`: 1 (0.1%)
- `Customer#000001499`: 1 (0.1%)
- `Customer#000001498`: 1 (0.1%)
- `Customer#000001497`: 1 (0.1%)
- `Customer#000001496`: 1 (0.1%)

**`c_address`** — distinct: 1,500, entropy: 10.5507 bits
- `zwrDoaY2gxCkdTXFaxNc`: 1 (0.1%)
- `zox9qZ4RtVJIk O8TQW7tg`: 1 (0.1%)
- `zn9Q7pT6KlQp3T5mUO533aq,`: 1 (0.1%)
- `zn1MYmFiukI LRu1DUdZzx,nP5t6G89x`: 1 (0.1%)
- `zm,F5hgXysWqkYrkQFY3kvmWSWKVe3U`: 1 (0.1%)

**`c_phone`** — distinct: 1,500, entropy: 10.5507 bits
- `34-992-529-2023`: 1 (0.1%)
- `34-985-422-6009`: 1 (0.1%)
- `34-973-735-5374`: 1 (0.1%)
- `34-969-612-1458`: 1 (0.1%)
- `34-956-232-6103`: 1 (0.1%)

_(showing 3 of 5 categorical columns — see metadata.json for full list)_

### Sample rows (first 3)

_ (showing 6 of 8 columns)_
| `c_custkey` | `c_name` | `c_address` | `c_nationkey` | `c_phone` | `c_acctbal` |
|---|---|---|---|---|---|
| 1 | Customer#000000001 | j5JsirBM9PsCy0O1m | 15 | 25-989-741-2988 | 711.56 |
| 2 | Customer#000000002 | 487LW1dovn6Q4dMVymKwwLE9OKf3QG | 13 | 23-768-687-3665 | 121.65 |
| 3 | Customer#000000003 | fkRGN8nY4pkE | 1 | 11-719-748-3364 | 7498.12 |

## Table: `part`

- **Rows:** 2,000
- **Columns:** 9
- **PK:** `p_partkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `p_partkey` | int | 0 | 1 | 2,000 | 1,000.5000 | 577.4946 |
| `p_name` | string | 0 | 2,000 | — | — | — |
| `p_mfgr` | string | 0 | 5 | — | — | — |
| `p_brand` | string | 0 | 25 | — | — | — |
| `p_type` | string | 0 | 150 | — | — | — |
| `p_size` | int | 0 | 1 | 50 | 25.2555 | 14.4173 |
| `p_container` | string | 0 | 40 | — | — | — |
| `p_retailprice` | float | 0 | 901.0000 | 1,900.9900 | 1,400.4960 | 289.0346 |
| `p_comment` | string | 0 | 1,962 | — | — | — |

### Top values (categorical columns)


**`p_name`** — distinct: 2,000, entropy: 10.9658 bits
- `yellow white puff orange rosy`: 1 (0.1%)
- `yellow white ghost lavender salmon`: 1 (0.1%)
- `yellow turquoise peru purple cornflower`: 1 (0.1%)
- `yellow tomato lawn rosy lemon`: 1 (0.1%)
- `yellow powder navajo maroon chartreuse`: 1 (0.1%)

**`p_mfgr`** — distinct: 5, entropy: 2.3211 bits
- `Manufacturer#3`: 426 (21.3%)
- `Manufacturer#4`: 400 (20.0%)
- `Manufacturer#2`: 396 (19.8%)
- `Manufacturer#5`: 392 (19.6%)
- `Manufacturer#1`: 386 (19.3%)

**`p_brand`** — distinct: 25, entropy: 4.6409 bits
- `Brand#35`: 93 (4.7%)
- `Brand#32`: 88 (4.4%)
- `Brand#43`: 87 (4.3%)
- `Brand#33`: 87 (4.3%)
- `Brand#52`: 85 (4.2%)

_(showing 3 of 6 categorical columns — see metadata.json for full list)_

### Sample rows (first 3)

_ (showing 6 of 9 columns)_
| `p_partkey` | `p_name` | `p_mfgr` | `p_brand` | `p_type` | `p_size` |
|---|---|---|---|---|---|
| 1 | goldenrod lavender spring chocolate lace | Manufacturer#1 | Brand#13 | PROMO BURNISHED COPPER | 7 |
| 2 | blush thistle blue yellow saddle | Manufacturer#1 | Brand#13 | LARGE BRUSHED BRASS | 1 |
| 3 | spring green yellow purple cornsilk | Manufacturer#4 | Brand#42 | STANDARD POLISHED BRASS | 21 |

## Table: `partsupp`

- **Rows:** 8,000
- **Columns:** 5
- **PK:** `ps_partkey, ps_suppkey`
- **FK:** `ps_partkey` → `part.p_partkey`, `ps_suppkey` → `supplier.s_suppkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `ps_partkey` | int | 0 | 1 | 2,000 | 1,000.5000 | 577.3863 |
| `ps_suppkey` | int | 0 | 1 | 100 | 50.5000 | 28.8679 |
| `ps_availqty` | int | 0 | 3 | 9,998 | 5,009.9274 | 2,890.1503 |
| `ps_supplycost` | float | 0 | 1.0500 | 999.9900 | 494.6797 | 288.5436 |
| `ps_comment` | string | 0 | 7,998 | — | — | — |

### Top values (categorical columns)


**`ps_comment`** — distinct: 7,998, entropy: 12.9653 bits
- `s. furiously regular platelets integrat…`: 2 (0.0%)
- ` instructions sleep slyly. silent depos…`: 2 (0.0%)
- `ze requests. furiously ironic accounts …`: 1 (0.0%)
- `ze at the packages. final, even deposit…`: 1 (0.0%)
- `ze along the slyly careful foxes. blith…`: 1 (0.0%)

### Sample rows (first 3)


| `ps_partkey` | `ps_suppkey` | `ps_availqty` | `ps_supplycost` | `ps_comment` |
|---|---|---|---|---|
| 1 | 2 | 3325 | 771.64 | blithely regular theodolites sleep slyl… |
| 1 | 27 | 8076 | 993.49 | ts boost carefully ironic, regular acco… |
| 1 | 52 | 3956 | 337.09 |  fluffily regular multipliers? sheaves … |

## Table: `orders`

- **Rows:** 15,000
- **Columns:** 9
- **PK:** `o_orderkey`
- **FK:** `o_custkey` → `customer.c_custkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `o_orderkey` | int | 0 | 1 | 60,000 | 29,991.5000 | 11,547.5829 |
| `o_custkey` | int | 0 | 1 | 1,499 | 755.4497 | 435.6682 |
| `o_orderstatus` | string | 0 | 3 | — | — | — |
| `o_totalprice` | float | 0 | 874.8900 | 466,001.2800 | 141,826.4553 | 82,761.1684 |
| `o_orderdate` | date | 0 | 2,401 | — | — | — |
| `o_orderpriority` | string | 0 | 5 | — | — | — |
| `o_clerk` | string | 0 | 1,000 | — | — | — |
| `o_shippriority` | int | 0 | 0 | 0 | 0.0000e+00 | 0.0000e+00 |
| `o_comment` | string | 0 | 14,984 | — | — | — |

### Top values (categorical columns)


**`o_orderstatus`** — distinct: 3, entropy: 1.1402 bits
- `O`: 7,333 (48.9%)
- `F`: 7,304 (48.7%)
- `P`: 363 (2.4%)

**`o_orderdate`** — distinct: 2,401, entropy: 11.1205 bits
- `1995-12-19`: 16 (0.1%)
- `1995-09-16`: 16 (0.1%)
- `1998-03-16`: 15 (0.1%)
- `1995-12-11`: 15 (0.1%)
- `1995-02-07`: 15 (0.1%)

**`o_orderpriority`** — distinct: 5, entropy: 2.3217 bits
- `2-HIGH`: 3,065 (20.4%)
- `4-NOT SPECIFIED`: 3,024 (20.2%)
- `1-URGENT`: 3,020 (20.1%)
- `5-LOW`: 2,950 (19.7%)
- `3-MEDIUM`: 2,941 (19.6%)

_(showing 3 of 5 categorical columns — see metadata.json for full list)_

### Sample rows (first 3)

_ (showing 6 of 9 columns)_
| `o_orderkey` | `o_custkey` | `o_orderstatus` | `o_totalprice` | `o_orderdate` | `o_orderpriority` |
|---|---|---|---|---|---|
| 1 | 370 | O | 172799.49 | 1996-01-02 | 5-LOW |
| 2 | 781 | O | 38426.09 | 1996-12-01 | 1-URGENT |
| 3 | 1234 | F | 205654.3 | 1993-10-14 | 5-LOW |

## Table: `lineitem`

- **Rows:** 60,175
- **Columns:** 16
- **PK:** `l_orderkey, l_linenumber`
- **FK:** `l_orderkey` → `orders.o_orderkey`, `l_partkey` → `part.p_partkey`, `l_suppkey` → `supplier.s_suppkey`

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `l_orderkey` | int | 0 | 1 | 60,000 | 29,958.6136 | 2,890.7541 |
| `l_partkey` | int | 0 | 1 | 2,000 | 1,002.7013 | 573.9479 |
| `l_suppkey` | int | 0 | 1 | 100 | 50.5360 | 28.8163 |
| `l_linenumber` | int | 0 | 1 | 7 | 3.0043 | 1.7283 |
| `l_quantity` | float | 0 | 1.0000 | 50.0000 | 25.5277 | 14.5079 |
| `l_extendedprice` | float | 0 | 904.0000 | 94,949.5000 | 35,765.5133 | 22,057.4193 |
| `l_discount` | float | 0 | 0.0000e+00 | 0.1000 | 0.0499 | 0.0314 |
| `l_tax` | float | 0 | 0.0000e+00 | 0.0800 | 0.0402 | 0.0256 |
| `l_returnflag` | string | 0 | 3 | — | — | — |
| `l_linestatus` | string | 0 | 2 | — | — | — |
| `l_shipdate` | date | 0 | 2,518 | — | — | — |
| `l_commitdate` | date | 0 | 2,460 | — | — | — |
| `l_receiptdate` | date | 0 | 2,529 | — | — | — |
| `l_shipinstruct` | string | 0 | 4 | — | — | — |
| `l_shipmode` | string | 0 | 7 | — | — | — |
| `l_comment` | string | 0 | 58,516 | — | — | — |

### Top values (categorical columns)


**`l_returnflag`** — distinct: 3, entropy: 1.4948 bits
- `N`: 30,397 (50.5%)
- `R`: 14,902 (24.8%)
- `A`: 14,876 (24.7%)

**`l_linestatus`** — distinct: 2, entropy: 1.0 bits
- `F`: 30,126 (50.1%)
- `O`: 30,049 (49.9%)

**`l_shipdate`** — distinct: 2,518, entropy: 11.2398 bits
- `1994-03-15`: 42 (0.1%)
- `1996-04-18`: 41 (0.1%)
- `1994-03-29`: 41 (0.1%)
- `1994-03-17`: 41 (0.1%)
- `1994-03-08`: 40 (0.1%)

_(showing 3 of 8 categorical columns — see metadata.json for full list)_

### Sample rows (first 3)

_ (showing 6 of 16 columns)_
| `l_orderkey` | `l_partkey` | `l_suppkey` | `l_linenumber` | `l_quantity` | `l_extendedprice` |
|---|---|---|---|---|---|
| 1 | 1552 | 93 | 1 | 17.0 | 24710.35 |
| 1 | 674 | 75 | 2 | 36.0 | 56688.12 |
| 1 | 637 | 38 | 3 | 8.0 | 12301.04 |
