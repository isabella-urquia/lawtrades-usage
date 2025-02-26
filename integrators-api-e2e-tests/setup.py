from setuptools import setup, find_packages

setup(
    name="integrators_api_e2e_tests",
    version="0.1",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "pytest",
        "requests",
    ],
    python_requires=">=3.8",
) 