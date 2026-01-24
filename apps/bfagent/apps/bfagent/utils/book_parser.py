"""
Book Parser Utility
Parses AI-generated complete book content into structured chapters
"""

import re
from typing import Any, Dict, List


def parse_complete_book(content: str, project) -> List[Dict[str, Any]]:
    """
    Parse AI-generated complete book into structured chapters

    Expected format:
    #### Chapter 1: [Title]
    [Content]

    #### Chapter 2: [Title]
    [Content]

    Args:
        content: AI-generated book content
        project: BookProjects instance

    Returns:
        List of chapter dictionaries ready for BookChapters creation
    """
    chapters = []

    # Split by chapter markers (#### Chapter N: Title or #### N. Title)
    chapter_pattern = r"####\s*(?:Chapter\s+)?(\d+)[\.:]\s*([^\n]+)\n([\s\S]+?)(?=####\s*(?:Chapter\s+)?\d+[\.:]\s*|$)"
    matches = re.findall(chapter_pattern, content, re.MULTILINE)

    print(f"📖 parse_complete_book: Found {len(matches)} chapters")

    for chapter_num, title, chapter_content in matches:
        chapter_num = int(chapter_num)
        title = title.strip()
        chapter_content = chapter_content.strip()

        # Extract summary if present (first paragraph or first 200 chars)
        summary_match = re.match(r"^(.+?)\n\n", chapter_content)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            summary = chapter_content[:200].strip() + "..."

        chapter_data = {
            "project": project,
            "chapter_number": chapter_num,
            "title": title,
            "content": chapter_content,
            "summary": summary,
            "status": "draft",
            "word_count": len(chapter_content.split()),
        }

        chapters.append(chapter_data)
        print(f"  ✅ Chapter {chapter_num}: {title} ({chapter_data['word_count']} words)")

    # Fallback: If no structured chapters found, try simpler split
    if not chapters:
        print("⚠️  No structured chapters found, trying alternative parsing...")
        # Try splitting by "Chapter N" headers
        simple_pattern = r"(?:^|\n)(?:Chapter|CHAPTER)\s+(\d+)[:\s]*([^\n]*)\n([\s\S]+?)(?=(?:^|\n)(?:Chapter|CHAPTER)\s+\d+|$)"
        matches = re.findall(simple_pattern, content, re.MULTILINE)

        for chapter_num, title, chapter_content in matches:
            chapter_num = int(chapter_num)
            title = title.strip() if title else f"Chapter {chapter_num}"
            chapter_content = chapter_content.strip()

            chapter_data = {
                "project": project,
                "chapter_number": chapter_num,
                "title": title,
                "content": chapter_content,
                "summary": chapter_content[:200].strip() + "...",
                "status": "draft",
                "word_count": len(chapter_content.split()),
            }

            chapters.append(chapter_data)
            print(f"  ✅ Chapter {chapter_num}: {title} ({chapter_data['word_count']} words)")

    # If still no chapters, create a single chapter from all content
    if not chapters:
        print("⚠️  Falling back to single chapter creation")
        chapters.append(
            {
                "project": project,
                "chapter_number": 1,
                "title": "Complete Book",
                "content": content,
                "summary": content[:200].strip() + "...",
                "status": "draft",
                "word_count": len(content.split()),
            }
        )

    return chapters
