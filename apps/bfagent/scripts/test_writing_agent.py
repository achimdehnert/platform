#!/usr/bin/env python
"""Test WritingAgent - Text Analysis, Character Extraction, Style."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.bfagent.agents import WritingAgent, analyze_writing

agent = WritingAgent()

# Test text
text = """
Der junge Ritter Alaric ritt durch den dunklen Wald. Seine Rüstung glänzte im Mondlicht.
Er suchte den Drachen, der das Königreich bedrohte. Alaric war mutig, aber auch vorsichtig.

"Wo versteckst du dich, Bestie?" rief er in die Nacht.

Der Wind antwortete mit einem kalten Heulen. Alaric zog sein Schwert. Der Kampf würde bald beginnen.
Die Magie in der Luft war spürbar. Der Zauber des alten Königs schützte ihn noch.
"""

print("=" * 60)
print("WRITING AGENT TEST")
print("=" * 60)

# Analyze
analysis = agent.analyze_text(text)

print(f"\n📊 Text Stats:")
print(f"  Words: {analysis.text_stats['word_count']}")
print(f"  Sentences: {analysis.text_stats['sentence_count']}")
print(f"  Reading time: {analysis.text_stats['reading_time_minutes']} min")

print(f"\n👤 Characters found:")
for c in analysis.characters:
    print(f"  - {c.name} (mentions: {c.mentions})")

print(f"\n✍️ Style Metrics:")
for key, value in analysis.style_metrics.items():
    print(f"  - {key}: {value}")

print(f"\n⚠️ Style Issues ({len(analysis.issues)}):")
for issue in analysis.issues[:3]:
    print(f"  - [{issue['type']}] {issue['message']}")

print(f"\n💡 Suggestions:")
for sug in analysis.suggestions:
    print(f"  - {sug}")

# Genre detection
genre, confidence = agent.detect_genre(text)
print(f"\n📚 Genre: {genre} ({confidence:.0%} confidence)")

# Summary
summary = agent.generate_chapter_summary(text)
print(f"\n📝 Summary: {summary[:150]}...")

# Dialog analysis
dialog = agent.analyze_dialog_quality(text)
print(f"\n💬 Dialog Analysis:")
print(f"  - Count: {dialog['dialog_count']}")
print(f"  - Avg length: {dialog['avg_length']} words")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
