#!/usr/bin/env python3
"""
BF Agent Documentation - API Auto-Generator
============================================

Dieses Script generiert automatisch RST-Dateien für alle Module
im BF Agent Projekt.

Verwendung:
    python scripts/generate_api_docs.py

Author: Achim Grosskopf
"""

import os
import sys
from pathlib import Path
from typing import List, Set

# Konfiguration
PROJECT_ROOT = Path(__file__).parent.parent.parent
BF_AGENT_SRC = PROJECT_ROOT / "bf_agent"
DOCS_SOURCE = Path(__file__).parent.parent / "docs" / "source"
API_OUTPUT = DOCS_SOURCE / "api" / "generated"

# Module die übersprungen werden
SKIP_MODULES: Set[str] = {
    "migrations",
    "tests",
    "__pycache__",
    "conftest",
    "setup",
}

# Domains die dokumentiert werden sollen
DOMAINS: List[str] = [
    "core",
    "handlers",
    "domains.books",
    "domains.comics",
    "domains.cad",
    "domains.exschutz",
]


def ensure_directory(path: Path) -> None:
    """Erstellt Verzeichnis falls nicht vorhanden."""
    path.mkdir(parents=True, exist_ok=True)


def is_python_module(path: Path) -> bool:
    """Prüft ob Pfad ein Python-Modul ist."""
    if path.is_file():
        return path.suffix == ".py" and path.stem not in SKIP_MODULES
    if path.is_dir():
        return (
            path.name not in SKIP_MODULES
            and (path / "__init__.py").exists()
        )
    return False


def get_module_path(file_path: Path, base_path: Path) -> str:
    """Konvertiert Dateipfad zu Python-Modulpfad."""
    relative = file_path.relative_to(base_path)
    parts = list(relative.parts)
    
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    
    if parts[-1] == "__init__":
        parts = parts[:-1]
    
    return ".".join(["bf_agent"] + parts)


def generate_module_rst(module_path: str, output_file: Path) -> None:
    """Generiert RST-Datei für ein Modul."""
    module_name = module_path.split(".")[-1]
    title = module_name.replace("_", " ").title()
    
    content = f"""{title}
{"=" * len(title)}

.. automodule:: {module_path}
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
"""
    
    output_file.write_text(content)
    print(f"  ✓ Generated: {output_file.name}")


def generate_index_rst(modules: List[str], output_dir: Path, title: str) -> None:
    """Generiert Index-RST für ein Verzeichnis."""
    index_file = output_dir / "index.rst"
    
    toctree_entries = "\n   ".join(
        Path(m).stem for m in sorted(modules)
    )
    
    content = f"""{title}
{"=" * len(title)}

.. toctree::
   :maxdepth: 2
   
   {toctree_entries}
"""
    
    index_file.write_text(content)
    print(f"  ✓ Generated: index.rst")


def scan_directory(
    directory: Path,
    base_path: Path,
    output_dir: Path
) -> List[str]:
    """Scannt ein Verzeichnis und generiert RST-Dateien."""
    ensure_directory(output_dir)
    generated_modules = []
    
    for item in sorted(directory.iterdir()):
        if not is_python_module(item):
            continue
        
        module_path = get_module_path(item, base_path)
        
        if item.is_file():
            output_file = output_dir / f"{item.stem}.rst"
            generate_module_rst(module_path, output_file)
            generated_modules.append(str(output_file))
        
        elif item.is_dir():
            sub_output = output_dir / item.name
            sub_modules = scan_directory(item, base_path, sub_output)
            if sub_modules:
                generate_index_rst(
                    sub_modules,
                    sub_output,
                    item.name.replace("_", " ").title()
                )
                generated_modules.append(str(sub_output / "index.rst"))
    
    return generated_modules


def main():
    """Hauptfunktion."""
    print("\n" + "=" * 60)
    print("BF Agent API Documentation Generator")
    print("=" * 60 + "\n")
    
    if not BF_AGENT_SRC.exists():
        print(f"❌ Error: Source directory not found: {BF_AGENT_SRC}")
        print("   Make sure you're running this from the docs directory")
        sys.exit(1)
    
    ensure_directory(API_OUTPUT)
    
    all_modules = []
    
    for domain in DOMAINS:
        domain_path = BF_AGENT_SRC
        for part in domain.split("."):
            domain_path = domain_path / part
        
        if not domain_path.exists():
            print(f"⚠ Warning: Domain not found: {domain}")
            continue
        
        print(f"\n📂 Processing: {domain}")
        output_dir = API_OUTPUT / domain.replace(".", "/")
        
        modules = scan_directory(domain_path, BF_AGENT_SRC, output_dir)
        all_modules.extend(modules)
    
    # Generiere Haupt-Index
    if all_modules:
        print(f"\n📄 Generating main index...")
        generate_index_rst(
            [str(API_OUTPUT / d.replace(".", "/") / "index.rst") 
             for d in DOMAINS if (API_OUTPUT / d.replace(".", "/")).exists()],
            API_OUTPUT,
            "API Reference"
        )
    
    print("\n" + "=" * 60)
    print(f"✅ Generated {len(all_modules)} module documentation files")
    print(f"📁 Output directory: {API_OUTPUT}")
    print("=" * 60 + "\n")
    
    print("Next steps:")
    print("  1. Run 'make html' to build documentation")
    print("  2. Check build/html/api/generated/index.html")
    print("")


if __name__ == "__main__":
    main()
