from typing import List

from setuptools import setup, find_packages

def get_requirements(filename:str) -> List[str]:
    with open(filename, 'r') as f:
        requirementsList=[line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('-e .')]
        print(requirementsList)
        return requirementsList

setup(
    name="my_app",
    version="0.1",
    author="Vivek",
    author_email="Vivekpatel8770032887@gmail.com",
    packages=find_packages(),
    install_requires=get_requirements('requirements.txt')
)