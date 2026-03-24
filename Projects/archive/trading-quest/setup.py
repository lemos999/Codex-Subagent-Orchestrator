from setuptools import setup, find_packages

setup(
    name="trading-quest",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "pandas>=1.5",
    ],
    extras_require={
        "binance": ["python-binance>=1.0"],
        "telegram": [],  # uses stdlib urllib
    },
    entry_points={
        "console_scripts": [
            "tq=tq.cli.main:cli",
        ],
    },
)
