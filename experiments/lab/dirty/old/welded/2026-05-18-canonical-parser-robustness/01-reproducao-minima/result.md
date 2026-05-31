# Sub-exp 01 — Resultado

**Total casos**: 10
- OK: 7
- FAIL: 3
- ERROR: 0

## Resumo

| # | Caso | RT |
|---|---|---|
| `1-single-string-with-comma` | OK |
| `2-comma-at-start` | OK |
| `3-comma-at-end` | OK |
| `4-multiple-commas` | OK |
| `5-prefix-and-comma` | FAIL |
| `6-comma-and-suffix` | OK |
| `7-pref-lit-comma-suf` | FAIL |
| `8-tpch-pathological` | OK |
| `9-strong-prefix-comma` | OK |
| `10-multiple-with-shared-prefix` | FAIL |

## Detalhes por caso

### 1-single-string-with-comma

**Status**: OK

**Strings input**:
```
'a,b'
```

**Body emitido (canonical)**:
```
a,b
```

### 2-comma-at-start

**Status**: OK

**Strings input**:
```
',abc'
```

**Body emitido (canonical)**:
```
,abc
```

### 3-comma-at-end

**Status**: OK

**Strings input**:
```
'abc,'
```

**Body emitido (canonical)**:
```
abc,
```

### 4-multiple-commas

**Status**: OK

**Strings input**:
```
'a,b,c'
```

**Body emitido (canonical)**:
```
a,b,c
```

### 5-prefix-and-comma

**Status**: FAIL

**Strings input**:
```
'abcXYZ'
'abcXYZ,def'
```

**Body emitido (canonical)**:
```
abcXYZ
1,def
```

**Strings decodadas (DIFF)**:
```
OK  orig: 'abcXYZ'
**DIFF**  orig: 'abcXYZ,def'
      dec:  'abcXYZdef'
```

### 6-comma-and-suffix

**Status**: OK

**Strings input**:
```
'xyzABC'
'def,xyzABC'
```

**Body emitido (canonical)**:
```
xyzABC
def,1
```

### 7-pref-lit-comma-suf

**Status**: FAIL

**Strings input**:
```
'abcXYZ...endZZZ'
'abcXYZ,def,endZZZ'
```

**Body emitido (canonical)**:
```
abcXYZ*...*endZZZ
1,def,3
```

**Strings decodadas (DIFF)**:
```
OK  orig: 'abcXYZ...endZZZ'
**DIFF**  orig: 'abcXYZ,def,endZZZ'
      dec:  'abcXYZdef,endZZZ'
```

### 8-tpch-pathological

**Status**: OK

**Strings input**:
```
'ar packages. regular excuses among the ironic requests cajole fluffily blithely final requests. furiously express p'
's are. furiously even pinto bea'
'c, special dependencies around '
'e dolphins are furiously about the carefully '
' foxes boost furiously along the carefully dogged tithes. slyly regular orbits according to the special epit'
```

**Body emitido (canonical)**:
```
ar packages. regular excuses among the ironic requests cajole fluffily blithely final requests. furiously express p
s are. furiously even pinto bea
c, special dependencies around 
e dolphins are furiously about the carefully 
 foxes boost furiously along the carefully dogged tithes. slyly regular orbits according to the special epit
```

### 9-strong-prefix-comma

**Status**: OK

**Strings input**:
```
'pending, bold reques'
'pending, calm reques'
```

**Body emitido (canonical)**:
```
pending, *bold* reques
1calm3
```

### 10-multiple-with-shared-prefix

**Status**: FAIL

**Strings input**:
```
'prefix abc'
'prefix def'
'prefix a,b,c'
'prefix x,y,z'
```

**Body emitido (canonical)**:
```
prefix *a*bc
1def
1,2,b,c
1x,y,z
```

**Strings decodadas (DIFF)**:
```
OK  orig: 'prefix abc'
OK  orig: 'prefix def'
**DIFF**  orig: 'prefix a,b,c'
      dec:  'prefix ab,c'
OK  orig: 'prefix x,y,z'
```
