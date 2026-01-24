#!/usr/bin/env python3
"""
Memory Bank Optimizer - Intelligent Memory Management
Optimizes Windsurf Memory Bank for better performance
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


# ANSI Color codes for terminal output
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_colored(text, color):
    """Print text with color"""
    print(f"{color}{text}{Colors.END}")


class MemoryBankOptimizer:
    def __init__(self, memory_bank_path: str = "."):
        self.memory_bank_path = Path(memory_bank_path)
        self.backup_path = self.memory_bank_path / "backup"

        # Performance thresholds
        self.MAX_FILE_SIZE = 15000  # 15 KB per file
        self.OPTIMAL_TOTAL = 30000  # 30 KB total
        self.WARNING_THRESHOLD = 50000  # 50 KB

        # Optimization stats
        self.stats = {
            "files_processed": 0,
            "files_split": 0,
            "files_archived": 0,
            "bytes_saved": 0,
            "duplicates_removed": 0,
        }

    def analyze(self) -> Dict:
        """Analyze current memory bank state"""
        print_colored("🔍 ANALYZING MEMORY BANK", Colors.CYAN)
        print("=" * 50)

        analysis = {
            "total_size": 0,
            "file_count": 0,
            "oversized_files": [],
            "old_files": [],
            "duplicate_content": [],
            "optimization_potential": 0,
        }

        md_files = list(self.memory_bank_path.glob("*.md"))

        for file_path in md_files:
            try:
                size = file_path.stat().st_size
                analysis["total_size"] += size
                analysis["file_count"] += 1

                # Check for oversized files
                if size > self.MAX_FILE_SIZE:
                    analysis["oversized_files"].append(
                        {
                            "path": file_path,
                            "size": size,
                            "size_kb": round(size / 1024, 1),
                        }
                    )

                # Check for old files (older than 30 days without updates)
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mod_time < datetime.now() - timedelta(days=30):
                    analysis["old_files"].append(
                        {
                            "path": file_path,
                            "age_days": (datetime.now() - mod_time).days,
                        }
                    )

                self.stats["files_processed"] += 1

            except Exception as e:
                print_colored(f"❌ Error analyzing {file_path.name}: {e}", Colors.RED)

        # Calculate optimization potential
        analysis["optimization_potential"] = sum(
            f["size"] - self.MAX_FILE_SIZE for f in analysis["oversized_files"]
        )

        self._print_analysis(analysis)
        return analysis

    def _print_analysis(self, analysis: Dict):
        """Print analysis results"""
        total_kb = round(analysis["total_size"] / 1024, 1)

        print(f"📁 Total Files: {analysis['file_count']}")
        print(f"📊 Total Size: {total_kb} KB")
        print(f"⚠️ Oversized Files: {len(analysis['oversized_files'])}")
        print(f"🕰️ Old Files: {len(analysis['old_files'])}")
        print(
            f"💾 Optimization Potential: {round(analysis['optimization_potential'] / 1024, 1)} KB"
        )

        if analysis["oversized_files"]:
            print_colored("\n🔧 OVERSIZED FILES:", Colors.YELLOW)
            for file_info in analysis["oversized_files"]:
                print(f"   📄 {file_info['path'].name}: {file_info['size_kb']} KB")

    def optimize(self) -> bool:
        """Perform comprehensive optimization"""
        print_colored("🚀 STARTING MEMORY BANK OPTIMIZATION", Colors.CYAN)
        print("=" * 50)

        # Create backup first
        self._create_backup()

        # Analyze current state
        analysis = self.analyze()

        if not analysis["oversized_files"] and analysis["total_size"] < self.OPTIMAL_TOTAL:
            print_colored("✅ Memory bank is already optimized!", Colors.GREEN)
            return True

        # Optimize oversized files
        for file_info in analysis["oversized_files"]:
            self._optimize_file(file_info["path"])

        # Remove duplicates
        self._remove_duplicates()

        # Archive old files if needed
        if analysis["total_size"] > self.WARNING_THRESHOLD:
            self._archive_old_files(analysis["old_files"])

        # Print optimization results
        self._print_optimization_results()

        return True

    def _create_backup(self):
        """Create backup of memory bank"""
        print_colored("💾 Creating backup...", Colors.YELLOW)

        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)

        self.backup_path.mkdir(exist_ok=True)

        for md_file in self.memory_bank_path.glob("*.md"):
            shutil.copy2(md_file, self.backup_path)

        print_colored(f"✅ Backup created at {self.backup_path}", Colors.GREEN)

    def _optimize_file(self, file_path: Path):
        """Optimize a single oversized file"""
        print_colored(f"🔧 Optimizing {file_path.name}...", Colors.YELLOW)

        try:
            content = file_path.read_text(encoding="utf-8")
            original_size = len(content.encode("utf-8"))

            # Strategy 1: Remove excessive whitespace
            content = self._compress_whitespace(content)

            # Strategy 2: Remove redundant sections
            content = self._remove_redundant_content(content)

            # Strategy 3: Split if still too large
            if len(content.encode("utf-8")) > self.MAX_FILE_SIZE:
                self._split_file(file_path, content)
                self.stats["files_split"] += 1
            else:
                # Write optimized content
                file_path.write_text(content, encoding="utf-8")

            new_size = len(content.encode("utf-8"))
            self.stats["bytes_saved"] += original_size - new_size

            print_colored(
                f"   ✅ Reduced by {round((original_size - new_size) / 1024, 1)} KB",
                Colors.GREEN,
            )

        except Exception as e:
            print_colored(f"   ❌ Error optimizing {file_path.name}: {e}", Colors.RED)

    def _compress_whitespace(self, content: str) -> str:
        """Remove excessive whitespace"""
        # Remove multiple blank lines
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        # Remove trailing whitespace
        lines = [line.rstrip() for line in content.split("\n")]

        return "\n".join(lines)

    def _remove_redundant_content(self, content: str) -> str:
        """Remove redundant or outdated content"""
        lines = content.split("\n")
        filtered_lines = []
        seen_sections = set()

        for line in lines:
            # Skip duplicate section headers
            if line.startswith("#"):
                section_key = line.lower().strip()
                if section_key in seen_sections:
                    continue
                seen_sections.add(section_key)

            # Skip very long repetitive lines
            if len(line) > 200 and line.count("=") > 50:
                continue

            filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _split_file(self, file_path: Path, content: str):
        """Split large file into smaller parts"""
        print_colored(f"   ✂️ Splitting {file_path.name}...", Colors.YELLOW)

        # Split by major sections (## headers)
        sections = re.split(r"\n(?=##\s)", content)

        if len(sections) <= 1:
            # If no major sections, split by size
            self._split_by_size(file_path, content)
            return

        # Create base name
        base_name = file_path.stem

        # Save first section as original file
        file_path.write_text(sections[0], encoding="utf-8")

        # Save additional sections as separate files
        for i, section in enumerate(sections[1:], 1):
            new_file = file_path.parent / f"{base_name}_part{i}.md"
            new_file.write_text(f"# {base_name} - Part {i}\n\n{section}", encoding="utf-8")
            print_colored(f"   📄 Created {new_file.name}", Colors.GREEN)

    def _split_by_size(self, file_path: Path, content: str):
        """Split file by size when no clear sections exist"""
        lines = content.split("\n")
        current_chunk = []
        current_size = 0
        chunk_num = 1
        base_name = file_path.stem

        for line in lines:
            line_size = len(line.encode("utf-8"))

            if current_size + line_size > self.MAX_FILE_SIZE and current_chunk:
                # Save current chunk
                chunk_content = "\n".join(current_chunk)
                if chunk_num == 1:
                    file_path.write_text(chunk_content, encoding="utf-8")
                else:
                    new_file = file_path.parent / f"{base_name}_part{chunk_num}.md"
                    new_file.write_text(
                        f"# {base_name} - Part {chunk_num}\n\n{chunk_content}",
                        encoding="utf-8",
                    )

                # Reset for next chunk
                current_chunk = [line]
                current_size = line_size
                chunk_num += 1
            else:
                current_chunk.append(line)
                current_size += line_size

        # Save final chunk
        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            if chunk_num == 1:
                file_path.write_text(chunk_content, encoding="utf-8")
            else:
                new_file = file_path.parent / f"{base_name}_part{chunk_num}.md"
                new_file.write_text(
                    f"# {base_name} - Part {chunk_num}\n\n{chunk_content}",
                    encoding="utf-8",
                )

    def _remove_duplicates(self):
        """Remove duplicate content across files"""
        print_colored("🔍 Checking for duplicates...", Colors.YELLOW)

        # This is a simplified duplicate detection
        # In practice, you might want more sophisticated content comparison
        file_hashes = {}

        for md_file in self.memory_bank_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                content_hash = hash(content.strip())

                if content_hash in file_hashes:
                    print_colored(f"   🗑️ Removing duplicate: {md_file.name}", Colors.YELLOW)
                    md_file.unlink()
                    self.stats["duplicates_removed"] += 1
                else:
                    file_hashes[content_hash] = md_file

            except Exception as e:
                print_colored(f"   ❌ Error checking {md_file.name}: {e}", Colors.RED)

    def _archive_old_files(self, old_files: List[Dict]):
        """Archive old files to reduce memory bank size"""
        if not old_files:
            return

        print_colored("📦 Archiving old files...", Colors.YELLOW)

        archive_path = self.memory_bank_path / "archive"
        archive_path.mkdir(exist_ok=True)

        for file_info in old_files:
            if file_info["age_days"] > 60:  # Archive files older than 60 days
                try:
                    file_path = file_info["path"]
                    archive_file = archive_path / file_path.name
                    shutil.move(str(file_path), str(archive_file))
                    print_colored(f"   📦 Archived {file_path.name}", Colors.GREEN)
                    self.stats["files_archived"] += 1
                except Exception as e:
                    print_colored(f"   ❌ Error archiving {file_path.name}: {e}", Colors.RED)

    def _print_optimization_results(self):
        """Print optimization results"""
        print()
        print_colored("🎉 OPTIMIZATION COMPLETE!", Colors.GREEN)
        print("=" * 50)

        print(f"📁 Files Processed: {self.stats['files_processed']}")
        print(f"✂️ Files Split: {self.stats['files_split']}")
        print(f"📦 Files Archived: {self.stats['files_archived']}")
        print(f"🗑️ Duplicates Removed: {self.stats['duplicates_removed']}")
        print(f"💾 Space Saved: {round(self.stats['bytes_saved'] / 1024, 1)} KB")

        # Re-analyze to show improvement
        print()
        print_colored("📊 POST-OPTIMIZATION ANALYSIS:", Colors.CYAN)
        self.analyze()


def main():
    parser = argparse.ArgumentParser(description="Memory Bank Optimizer")
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze memory bank without optimization",
    )
    parser.add_argument("--optimize", action="store_true", help="Perform full optimization")
    parser.add_argument("--archive-old", action="store_true", help="Archive old files only")
    parser.add_argument("--path", default=".", help="Path to memory bank directory")

    args = parser.parse_args()

    optimizer = MemoryBankOptimizer(args.path)

    try:
        if args.analyze:
            optimizer.analyze()
        elif args.optimize:
            optimizer.optimize()
        elif args.archive_old:
            analysis = optimizer.analyze()
            optimizer._archive_old_files(analysis["old_files"])
        else:
            print_colored("Please specify --analyze, --optimize, or --archive-old", Colors.YELLOW)
            parser.print_help()

    except KeyboardInterrupt:
        print_colored("\n⏹️ Optimization cancelled by user", Colors.YELLOW)
    except Exception as e:
        print_colored(f"❌ Error: {e}", Colors.RED)
        sys.exit(1)


if __name__ == "__main__":
    main()
