from setuptools import setup
import os

version = os.environ.get('PIJUICE_VERSION')

setup(
    name="pijuice",
    version=version,
    author="Ton van Overbeek",
    author_email="tvoverbeek@gmail.com",
    description="Software package for PiJuice",
    url="https://github.com/PiSupply/PiJuice/",
    license='GPL v2',
    py_modules=['pijuice'],
    #data_files=[],
    scripts=['src/pijuice_sys.py', "Utilities/pijuice_util.py", "Test/pijuiceboot.py", "Test/pijuice_log.py"],
    )
