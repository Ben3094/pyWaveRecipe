from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-16") as fh:
    install_requires = [line.strip() for line in fh.readlines()]

setup(
    name='pyWaveRecipe',
    version='0.0.37',
    author='Benjamin SAGGIN',
    description='Tools for storing S-parameters from electromagnetic components and combine them while preserving external dependencies of each components',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='',
    project_urls = {
        "Bug Tracker": ""
    },
    license='MIT',
    packages=find_packages(),
    install_requires=install_requires,
)