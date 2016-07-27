from setuptools import setup, find_packages

dev_requires = ['flake8']
install_requires = []

setup(
    author="Grahame Bowland",
    author_email="grahame@angrygoats.net",
    description="process single-transferable-vote elections as used for the Australian Senate under the Commonwealth Electoral Act (1918)",
    license="Apache2",
    keywords="stv senate voting",
    url="https://github.com/grahame/dividebatur",
    name="dividebatur",
    version="0.2.2",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    extras_require={
        'dev': dev_requires
    },
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'dividebatur = dividebatur.cli:main',
        ],
    }
)
