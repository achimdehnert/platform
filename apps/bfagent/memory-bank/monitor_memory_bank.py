#!/usr/bin/env python3
"""
Memory Bank Performance Monitor - Python Version
Based on Windsurf Memory Bank Best Practices
"""

import glob
import os
import sys
from datetime import datetime
from pathlib import Path


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


def main():
    """Main memory bank monitoring function"""
    print_colored("📊 Windsurf Memory Bank Performance Monitor", Colors.CYAN)
    print("=" * 50)

    # Performance Thresholds (from best practices)
    OPTIMAL_TOTAL = 30000  # 30 KB
    WARNING_THRESHOLD = 50000  # 50 KB
    CRITICAL_THRESHOLD = 100000  # 100 KB
    MAX_FILE_SIZE = 15000  # 15 KB per file

    # Get memory bank path
    memory_bank_path = Path(".")
    if not memory_bank_path.exists():
        print_colored("❌ Memory bank directory not found!", Colors.RED)
        return

    # Analyze current memory bank
    total_size = 0
    file_count = 0
    oversized_files = []
    health_score = 100

    print_colored("🔍 Analyzing Memory Bank Files...", Colors.YELLOW)

    # Find all .md files
    md_files = list(memory_bank_path.glob("*.md"))

    if not md_files:
        print_colored("⚠️ No .md files found in memory bank!", Colors.YELLOW)
        return

    for file_path in md_files:
        try:
            size = file_path.stat().st_size
            total_size += size
            file_count += 1

            size_kb = round(size / 1024, 1)

            if size > MAX_FILE_SIZE:
                oversized_files.append(
                    {
                        "name": file_path.name,
                        "size": size_kb,
                        "overage": round((size - MAX_FILE_SIZE) / 1024, 1),
                    }
                )
                health_score -= 15
                print_colored(
                    f"   ⚠️  {file_path.name}: {size_kb}KB (>{MAX_FILE_SIZE/1024}KB limit)",
                    Colors.RED,
                )
            else:
                print_colored(f"   ✅ {file_path.name}: {size_kb}KB", Colors.GREEN)

        except Exception as e:
            print_colored(f"   ❌ Error reading {file_path.name}: {e}", Colors.RED)

    # Calculate metrics
    total_kb = round(total_size / 1024, 1)
    avg_file_size = round(total_size / file_count / 1024, 1) if file_count > 0 else 0

    # Determine status
    status = "OPTIMAL"
    status_color = Colors.GREEN
    if total_size > CRITICAL_THRESHOLD:
        status = "CRITICAL"
        status_color = Colors.RED
        health_score = 0
    elif total_size > WARNING_THRESHOLD:
        status = "WARNING"
        status_color = Colors.YELLOW
        health_score = max(30, health_score - 20)

    print()
    print_colored("📈 MEMORY BANK PERFORMANCE REPORT", Colors.CYAN)
    print("=" * 50)

    print(f"📁 Total Files: {file_count}")
    print(f"📊 Total Size: {total_kb} KB")
    print(f"📏 Average File Size: {avg_file_size} KB")
    print(f"🎯 Health Score: {health_score}/100")
    print_colored(f"🚦 Status: {status}", status_color)

    # Recommendations
    print()
    print_colored("💡 OPTIMIZATION RECOMMENDATIONS", Colors.CYAN)
    print("=" * 50)

    if oversized_files:
        print_colored("🔧 OVERSIZED FILES DETECTED:", Colors.RED)
        for file_info in oversized_files:
            print(
                f"   📄 {file_info['name']}: {file_info['size']}KB (reduce by {file_info['overage']}KB)"
            )
        print()
        print_colored("   Recommendations:", Colors.YELLOW)
        print("   • Split large files into smaller, focused topics")
        print("   • Archive old or rarely used memories")
        print("   • Remove redundant information")
        print("   • Use more concise language")

    if total_size > WARNING_THRESHOLD:
        print_colored("⚠️ TOTAL SIZE WARNING:", Colors.YELLOW)
        print(f"   Current: {total_kb}KB, Optimal: <{OPTIMAL_TOTAL/1024}KB")
        print("   Consider:")
        print("   • Regular cleanup of outdated memories")
        print("   • Consolidation of related memories")
        print("   • Archiving completed project memories")

    if health_score >= 80:
        print_colored("✅ MEMORY BANK IS HEALTHY!", Colors.GREEN)
        print("   Continue current practices")
    elif health_score >= 60:
        print_colored("⚠️ MINOR OPTIMIZATIONS NEEDED", Colors.YELLOW)
        print("   Address oversized files when convenient")
    else:
        print_colored("🚨 IMMEDIATE ATTENTION REQUIRED", Colors.RED)
        print("   Memory bank performance is degraded")

    # Auto-optimization suggestions
    print()
    print_colored("🤖 AUTO-OPTIMIZATION AVAILABLE", Colors.CYAN)
    print("=" * 50)
    print("Run the following commands to optimize:")
    print("1. python memory-bank/optimize_memory_bank.py --analyze")
    print("2. python memory-bank/optimize_memory_bank.py --optimize")
    print("3. python memory-bank/optimize_memory_bank.py --archive-old")

    return {
        "total_size": total_size,
        "file_count": file_count,
        "health_score": health_score,
        "status": status,
        "oversized_files": oversized_files,
    }


if __name__ == "__main__":
    try:
        result = main()
        if result and result["health_score"] < 60:
            sys.exit(1)  # Exit with error code for CI/CD
    except KeyboardInterrupt:
        print_colored("\n⏹️ Monitoring cancelled by user", Colors.YELLOW)
    except Exception as e:
        print_colored(f"❌ Error: {e}", Colors.RED)
        sys.exit(1)
