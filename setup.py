"""Fallback setup.py for older pip versions that don't support pyproject.toml."""

from setuptools import setup

setup(
    name="clp-rat-tracker",
    version="1.0.0",
    description="Conditioned Place Preference (CPP) tracker for laboratory rat experiments",
    author="Leo Blakeley",
    url="https://github.com/LeoBlakeley/CLP_rat_tracker",
    py_modules=["main", "app", "tracker"],
    python_requires=">=3.8",
    install_requires=[
        "opencv-python>=4.8.0",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
    ],
    entry_points={
        "console_scripts": [
            "clp-rat-tracker=main:main",
        ],
    },
)
