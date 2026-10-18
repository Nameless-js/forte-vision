"""Bundle runtime resources from their canonical repository locations into wheels."""
from pathlib import Path
from shutil import copy2, copytree
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildPy(build_py):
    def run(self):
        super().run()
        root = Path(__file__).resolve().parent
        package = Path(self.build_lib) / "forte_ai"
        copytree(root / "configs", package / "configs", dirs_exist_ok=True)
        copytree(root / "kb", package / "kb_data", dirs_exist_ok=True)
        copy2(root / "forte_ai" / "result_schema.json", package / "result_schema.json")

setup(cmdclass={"build_py": BuildPy})
