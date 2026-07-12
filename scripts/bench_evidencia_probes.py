"""Sondas de telemetria do material comprobatório (T-QA-8 F1; F0-3 PORTÁVEL).

DUAS CAMADAS (decisão do owner, 2026-07-10 — independente de OS/hardware/linguagem):

1. CONCEITOS — a interface. Nomes/semântica portáveis, fáceis de identificar e
   transportar (um port Rust implementa 1:1: `Instant`, `process CPU time`,
   allocator peak, RSS peak do processo):
       wall_time_ns()      relógio monotônico de parede
       cpu_time_ns()       tempo de CPU do processo
       measure_repeat(fn)  protocolo de medição: warmup + n runs + mediana/p95
                           (o repeat é PARTE do conceito — relógios de CPU têm
                           tick grosso em algumas plataformas, ex. 15.625ms)
       peak_heap_bytes(fn) pico de alocação do heap durante fn
       peak_rss_bytes()    pico de memória residente do processo (melhor-esforço)
       env_fingerprint()   proveniência do ambiente + QUAIS sondas estão ativas

2. SONDAS — adaptadores POR PLATAFORMA, isolados NESTE arquivo, com fallback
   gracioso: plataforma sem a sonda -> o conceito retorna None -> o campo fica
   AUSENTE no relatório (a medição NUNCA quebra por plataforma). O fingerprint
   declara qual sonda respondeu. Roda em qualquer lugar que o Python rode.

stdlib-only (zero dependência; psutil só entraria como extra [bench] opt-in,
decisão do owner — F0-3).
"""
from __future__ import annotations

import os
import platform
import statistics
import sys
import time

# ---------------------------------------------------------------------------
# CONCEITO: tempo
# ---------------------------------------------------------------------------

def wall_time_ns() -> int:
    """Relógio monotônico de parede (portável em qualquer plataforma)."""
    return time.perf_counter_ns()


def cpu_time_ns() -> int | None:
    """Tempo de CPU do processo (user+system). Tick pode ser grosso —
    por isso o protocolo é SEMPRE measure_repeat, nunca 1 medida."""
    try:
        return time.process_time_ns()
    except Exception:
        return None


def measure_repeat(fn, n: int = 9, warmup: int = 2) -> dict:
    """Protocolo de medição de latência (conceito portável, T-QA-8 §2.4):
    `warmup` execuções descartadas + `n` medidas de wall-time -> mediana/p95.

    Retorna dict com unidades EXPLÍCITAS no nome do campo (_ns)."""
    for _ in range(warmup):
        fn()
    samples: list[int] = []
    for _ in range(n):
        t0 = wall_time_ns()
        fn()
        samples.append(wall_time_ns() - t0)
    samples.sort()
    return {
        "n": n,
        "warmup": warmup,
        "median_ns": int(statistics.median(samples)),
        "p95_ns": samples[min(n - 1, int(round(0.95 * (n - 1))))],
        "min_ns": samples[0],
        "max_ns": samples[-1],
    }


# ---------------------------------------------------------------------------
# CONCEITO: memória (heap)
# ---------------------------------------------------------------------------

def peak_heap_bytes(fn) -> tuple[object, int | None]:
    """Executa fn medindo o PICO de alocação de heap; retorna (resultado, pico).

    Sonda: tracemalloc (CPython; overhead relevante -> rodar em RUN SEPARADA
    da medição de tempo — regra do protocolo). Sem a sonda: (resultado, None).

    HONESTIDADE (nota da verificação F1): tracemalloc mede o heap do allocator
    PYTHON — alocações NATIVAS fora dele (ex.: acelerador Cython) NÃO entram.
    Num port Rust (global_allocator instrumentado) o mesmo conceito cobriria
    tudo do processo: comparação cross-linguagem exige esta nota. Pra visão de
    processo inteiro, use peak_rss_bytes."""
    try:
        import tracemalloc
    except ImportError:            # implementação sem tracemalloc: fallback
        return fn(), None
    tracemalloc.start()
    try:
        result = fn()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, int(peak)


# ---------------------------------------------------------------------------
# CONCEITO: memória (RSS do processo) — sondas por plataforma, isoladas
# ---------------------------------------------------------------------------

def _probe_rss_posix():
    """Sonda POSIX: resource.getrusage(ru_maxrss). Unidade varia por OS —
    normalizada AQUI, dentro da sonda:
    - Linux/FreeBSD/NetBSD/OpenBSD/AIX = KiB (*1024);
    - macOS = bytes;
    - Solaris/illumos = PÁGINAS (unidade ambígua) -> a sonda se declara
      INDISPONÍVEL (fallback None é mais honesto que número errado)."""
    import resource  # ImportError fora de POSIX -> caller faz fallback

    if sys.platform.startswith(("sunos", "solaris")):
        raise RuntimeError("ru_maxrss em paginas (Solaris) — sonda indisponivel")

    def read() -> int:
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return int(peak)            # bytes
        return int(peak) * 1024         # KiB -> bytes (Linux/BSDs/AIX)

    return "getrusage-posix", read


def _probe_rss_win32():
    """Sonda win32: GetProcessMemoryInfo.PeakWorkingSetSize via ctypes.
    Detalhe de plataforma fica CONFINADO aqui (F0-3: nada engessado fora
    das sondas)."""
    import ctypes
    import ctypes.wintypes as wt

    class _PMC(ctypes.Structure):
        _fields_ = [
            ("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # Win7+: a export vive no kernel32 como K32GetProcessMemoryInfo; o alias
    # em psapi.dll nem sempre resolve via ctypes — tentar kernel32 primeiro.
    try:
        fn = kernel32.K32GetProcessMemoryInfo
        probe_name = "k32-getprocessmemoryinfo"
    except AttributeError:
        fn = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
        probe_name = "psapi-win32"
    fn.argtypes = [wt.HANDLE, ctypes.POINTER(_PMC), wt.DWORD]
    fn.restype = wt.BOOL
    kernel32.GetCurrentProcess.restype = wt.HANDLE

    def read() -> int:
        pmc = _PMC()
        pmc.cb = ctypes.sizeof(_PMC)
        if not fn(kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            raise OSError(f"GetProcessMemoryInfo falhou "
                          f"(err={ctypes.get_last_error()})")
        return int(pmc.PeakWorkingSetSize)

    read()  # smoke: sonda que não responde no probe -> fallback do caller
    return probe_name, read


def _resolve_rss_probe():
    """Escolhe a sonda de RSS disponível; None se nenhuma (fallback gracioso)."""
    for factory in (_probe_rss_posix, _probe_rss_win32):
        try:
            return factory()
        except Exception:
            continue
    return None, None


_RSS_PROBE_NAME, _RSS_READ = _resolve_rss_probe()


def peak_rss_bytes() -> int | None:
    """Pico de memória residente do processo (bytes), melhor-esforço.
    None = plataforma sem sonda (campo ausente, medição não quebra)."""
    if _RSS_READ is None:
        return None
    try:
        return _RSS_READ()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CONCEITO: proveniência do ambiente
# ---------------------------------------------------------------------------

def env_fingerprint() -> dict:
    """Proveniência da medição: ambiente + versão do tcf + sondas ATIVAS
    (o relatório declara COM O QUE mediu — parte do contrato de honestidade)."""
    try:
        import tcf
        tcf_version = getattr(tcf, "__version__", None)
    except Exception:
        tcf_version = None
    try:
        from tcf.composicional.syntax import M8AVirtualRefsSyntax
        cython_accel = bool(getattr(
            M8AVirtualRefsSyntax, "_detect_compositions_accelerated", False))
    except Exception:
        cython_accel = None
    try:
        import tracemalloc  # noqa: F401
        heap_probe = "tracemalloc"
    except ImportError:
        heap_probe = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "tcf_version": tcf_version,
        "cython_accel": cython_accel,
        "probes": {"wall": "perf_counter", "cpu": "process_time",
                   "heap": heap_probe, "rss": _RSS_PROBE_NAME},
    }
