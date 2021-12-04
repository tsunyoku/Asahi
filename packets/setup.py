from Cython.Build import cythonize
from setuptools import setup

setup(ext_modules=cythonize(["reader.pyx", "writer.pyx"]))
