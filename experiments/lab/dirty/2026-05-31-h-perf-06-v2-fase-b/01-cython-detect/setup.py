"""Build do porte Cython: python setup.py build_ext --inplace (rodar nesta pasta)."""
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="detect_cy",
    ext_modules=cythonize(
        "detect_cy.pyx",
        language_level=3,
        annotate=True,  # gera detect_cy.html (linhas amarelas = Python-level)
    ),
)
