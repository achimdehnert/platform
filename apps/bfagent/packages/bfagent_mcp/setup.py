"""
BF Agent MCP Server - Setup Configuration
==========================================
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
version = "2.0.0.dev0"
try:
    init_file = Path(__file__).parent / "bfagent_mcp" / "__init__.py"
    with open(init_file) as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"').strip("'")
                break
except Exception:
    pass

# Read README if exists
readme = ""
readme_file = Path(__file__).parent / "README.md"
if readme_file.exists():
    with open(readme_file, encoding="utf-8") as f:
        readme = f.read()

setup(
    name="bfagent-mcp",
    version=version,
    author="BF Agent Team",
    author_email="team@bfagent.dev",
    description="Model Context Protocol Server for BF Agent",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/bfagent/bfagent-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        "django>=5.2",
        "pydantic>=2.0",
        "pydantic-settings>=2.0",
        "mcp>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
            "black>=23.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bfagent-mcp=bfagent_mcp.server:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
