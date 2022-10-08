from setuptools import setup
import os

version = os.environ.get('PIJUICE_VERSION')

setup(
    name="pijuice_scripts",
    version=version,
    author="Ralf Sieger",
    description="Scripts for PiJuice",
    license='GPL v3',
    scripts=[],
    )
