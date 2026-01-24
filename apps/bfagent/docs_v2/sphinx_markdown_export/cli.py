#!/usr/bin/env python3
"""
Standalone CLI für Sphinx → Markdown Konvertierung.
Kann ohne Django-Installation verwendet werden.

Usage:
    python cli.py /path/to/sphinx/docs -o output.md
    python cli.py /path/to/docs --title "My Docs" --no-toc
    python cli.py /path/to/docs --stdout | head -100

Author: BF Agent Framework
License: MIT
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Konvertiert Sphinx-Dokumentation zu einer einzelnen Markdown-Datei',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s /path/to/docs -o complete.md
  %(prog)s ./docs --title "API Documentation"
  %(prog)s ./docs --python-src src/mymodule --python-src src/utils
  %(prog)s ./docs --stdout | head -50

Abhängigkeiten:
  pip install sphinx sphinx-markdown-builder  (optional, verbessert Qualität)
        """
    )
    
    parser.add_argument(
        'source',
        help='Pfad zum Sphinx source-Verzeichnis (mit conf.py)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='documentation.md',
        help='Ausgabe-Dateiname (default: documentation.md)'
    )
    
    parser.add_argument(
        '-t', '--title',
        help='Dokumenttitel'
    )
    
    parser.add_argument(
        '--no-toc',
        action='store_true',
        help='Kein Inhaltsverzeichnis generieren'
    )
    
    parser.add_argument(
        '--no-meta',
        action='store_true',
        help='Keine Metadaten (Datum, Quelle) im Header'
    )
    
    parser.add_argument(
        '--no-api',
        action='store_true',
        help='Keine API-Referenz aus Python-Sourcen'
    )
    
    parser.add_argument(
        '--python-src',
        action='append',
        default=[],
        metavar='PATH',
        help='Python-Source-Pfade für API-Referenz (kann mehrfach angegeben werden)'
    )
    
    parser.add_argument(
        '--intersphinx',
        action='append',
        default=[],
        metavar='NAME=URL',
        help='Intersphinx-Mapping (z.B. python=https://docs.python.org/3)'
    )
    
    parser.add_argument(
        '--stdout',
        action='store_true',
        help='Ausgabe auf stdout statt in Datei'
    )
    
    parser.add_argument(
        '--install-deps',
        action='store_true',
        help='Installiere Abhängigkeiten (sphinx, sphinx-markdown-builder)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Verbose output (-v für Warnungen, -vv für Debug)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Keine Ausgabe außer Fehler'
    )
    
    args = parser.parse_args()
    
    # Abhängigkeiten installieren
    if args.install_deps:
        import subprocess
        print("📦 Installiere Abhängigkeiten...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'sphinx', 'sphinx-markdown-builder', '-q'
        ])
        print("✅ Abhängigkeiten installiert")
    
    # Import nach möglicher Installation
    from sphinx_markdown_export import (
        SphinxToMarkdownService,
        ExportConfig,
    )
    
    source_path = Path(args.source)
    
    # Validierung
    if not source_path.exists():
        print(f"❌ Fehler: Pfad existiert nicht: {source_path}", file=sys.stderr)
        sys.exit(1)
    
    if not (source_path / 'conf.py').exists():
        print(f"❌ Fehler: Keine conf.py gefunden in: {source_path}", file=sys.stderr)
        sys.exit(1)
    
    if not args.quiet:
        print(f"📚 Exportiere: {source_path}")
    
    # Intersphinx-Mapping parsen
    intersphinx = {}
    for mapping in args.intersphinx:
        if '=' in mapping:
            name, url = mapping.split('=', 1)
            intersphinx[name.strip()] = url.strip()
    
    # Konfiguration
    config = ExportConfig(
        title=args.title,
        include_toc=not args.no_toc,
        include_metadata=not args.no_meta,
        include_api_reference=not args.no_api,
        intersphinx_mapping=intersphinx,
        python_source_paths=args.python_src,
    )
    
    # Export
    service = SphinxToMarkdownService(source_path, config)
    output_path = None if args.stdout else Path(args.output)
    
    success, result_path, metadata = service.export(output_path)
    
    # Warnungen ausgeben
    if args.verbose >= 1 and not args.quiet:
        for warning in metadata.warnings:
            print(f"  ⚠️  {warning}", file=sys.stderr)
    
    # Fehler
    if not success:
        print(f"❌ Export fehlgeschlagen:", file=sys.stderr)
        for error in metadata.errors:
            print(f"   {error}", file=sys.stderr)
        sys.exit(1)
    
    # Output
    if args.stdout:
        print(result_path.read_text(encoding='utf-8'))
    else:
        if not args.quiet:
            print(f"\n✅ Exportiert: {result_path}")
            print(f"   Seiten:   {metadata.pages_count}")
            print(f"   Wörter:   {metadata.word_count:,}")
            print(f"   Zeichen:  {metadata.char_count:,}")
            print(f"   Dauer:    {metadata.duration_seconds:.1f}s")
            print(f"   Features: {', '.join(metadata.features_used)}")


if __name__ == '__main__':
    main()
