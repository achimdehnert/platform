"""
Setup script for sphinx_markdown_export package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="sphinx-markdown-export",
    version="1.0.0",
    author="BF Agent Framework",
    author_email="",
    description="Konvertiert Sphinx-Dokumentation zu einer einzelnen Markdown-Datei",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bf-agent/sphinx-markdown-export",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 5.0",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Documentation",
        "Topic :: Documentation :: Sphinx",
        "Topic :: Software Development :: Documentation",
        "Topic :: Text Processing :: Markup :: Markdown",
        "Topic :: Text Processing :: Markup :: reStructuredText",
    ],
    python_requires=">=3.9",
    install_requires=[
        # Keine harten Abhängigkeiten für Basis-Funktionalität
    ],
    extras_require={
        "sphinx": [
            "sphinx>=4.0",
            "sphinx-markdown-builder>=0.6.0",
        ],
        "django": [
            "django>=4.0",
        ],
        "full": [
            "sphinx>=4.0",
            "sphinx-markdown-builder>=0.6.0",
            "django>=4.0",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-django>=4.5",
            "black",
            "isort",
            "mypy",
        ],
    },
    entry_points={
        "console_scripts": [
            "sphinx-to-markdown=sphinx_markdown_export.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
