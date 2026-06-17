"""CLI: python -m natures_compiler <arquivo.dsl>  (compila + valida round-trip)."""
import sys
from pathlib import Path

from .compiler import compile_file

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "compile"]   # aceita 'compile x.dsl' ou 'x.dsl'
    if not args:
        print("uso: python -m natures_compiler <arquivo.dsl>", file=sys.stderr)
        sys.exit(2)
    try:
        spec = compile_file(args[0])
    except (ValueError, FileNotFoundError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: nature '{spec.name}' compilada e validada (round-trip lossless) "
          f"de {Path(args[0]).name}.")
