"""
Security validators for prompt injection detection.

This module provides robust detection of prompt injection attempts,
including handling of Unicode normalization and leetspeak bypass attempts.
"""

import re
import unicodedata
from typing import NamedTuple


class InjectionMatch(NamedTuple):
    """Result of an injection check."""

    detected: bool
    pattern_name: str | None
    matched_text: str | None


# Leetspeak mapping for normalization
LEETSPEAK_MAP: dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "@": "a",
    "$": "s",
    "!": "i",
    "+": "t",
    "€": "e",
    "£": "e",
}

# Unicode confusables (common substitutions)
UNICODE_CONFUSABLES: dict[str, str] = {
    "\u0430": "a",  # Cyrillic а
    "\u0435": "e",  # Cyrillic е
    "\u043e": "o",  # Cyrillic о
    "\u0440": "p",  # Cyrillic р
    "\u0441": "c",  # Cyrillic с
    "\u0443": "y",  # Cyrillic у
    "\u0445": "x",  # Cyrillic х
    "\u0456": "i",  # Cyrillic і
    "\u0458": "j",  # Cyrillic ј
    "\u04bb": "h",  # Cyrillic һ
    "\u2010": "-",  # Hyphen
    "\u2011": "-",  # Non-breaking hyphen
    "\u2012": "-",  # Figure dash
    "\u2013": "-",  # En dash
    "\u2014": "-",  # Em dash
    "\u2018": "'",  # Left single quote
    "\u2019": "'",  # Right single quote
    "\u201c": '"',  # Left double quote
    "\u201d": '"',  # Right double quote
    "\u00a0": " ",  # Non-breaking space
    "\u2000": " ",  # En quad
    "\u2001": " ",  # Em quad
    "\u2002": " ",  # En space
    "\u2003": " ",  # Em space
    "\u200b": "",   # Zero-width space (remove)
    "\ufeff": "",   # BOM (remove)
}


def normalize_text(text: str) -> str:
    """
    Normalize text for injection detection.

    This function:
    1. Applies Unicode NFKC normalization
    2. Converts to lowercase
    3. Replaces Unicode confusables with ASCII equivalents
    4. Converts leetspeak to normal letters
    5. Collapses multiple whitespace to single space
    6. Removes zero-width characters

    Args:
        text: Input text to normalize

    Returns:
        Normalized text for pattern matching
    """
    # Step 1: Unicode NFKC normalization (handles many confusables)
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Lowercase
    text = text.lower()

    # Step 3: Replace known Unicode confusables
    for char, replacement in UNICODE_CONFUSABLES.items():
        text = text.replace(char, replacement)

    # Step 4: Replace leetspeak
    for char, replacement in LEETSPEAK_MAP.items():
        text = text.replace(char, replacement)

    # Step 5: Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Step 6: Strip
    text = text.strip()

    return text


# Injection patterns with names for logging
INJECTION_PATTERNS: dict[str, re.Pattern] = {
    # Role manipulation
    "role_override": re.compile(
        r"(you are now|act as|pretend to be|roleplay as|assume the role|"
        r"from now on you|forget your instructions|ignore previous)",
        re.IGNORECASE,
    ),
    # Instruction override
    "instruction_override": re.compile(
        r"(ignore (all |the |your )?(previous |prior |above )?(instructions?|rules?|guidelines?)|"
        r"disregard (all |the |your )?(previous |prior |above )?(instructions?|rules?|guidelines?)|"
        r"override (all |the |your )?(previous |prior |above )?(instructions?|rules?|guidelines?))",
        re.IGNORECASE,
    ),
    # System prompt extraction
    "system_extraction": re.compile(
        r"(what (is|are) your (instructions?|rules?|system prompt|guidelines?)|"
        r"show me your (instructions?|rules?|system prompt|guidelines?)|"
        r"reveal your (instructions?|rules?|system prompt|guidelines?)|"
        r"print your (instructions?|rules?|system prompt|guidelines?)|"
        r"output your (instructions?|rules?|system prompt|guidelines?))",
        re.IGNORECASE,
    ),
    # Jailbreak attempts
    "jailbreak": re.compile(
        r"(dan mode|developer mode|jailbreak|bypass (safety|filter|restriction)|"
        r"unlock (your |the )?(full |true )?potential|"
        r"remove (all |your )?(restrictions?|limitations?|filters?))",
        re.IGNORECASE,
    ),
    # Prompt leaking
    "prompt_leak": re.compile(
        r"(repeat (the |your )?(text|words|prompt) (above|before)|"
        r"what (did i|have i) (just )?(say|said|write|wrote)|"
        r"echo (the |your )?(previous|last|above))",
        re.IGNORECASE,
    ),
    # Delimiter injection
    "delimiter_injection": re.compile(
        r"(\[system\]|\[user\]|\[assistant\]|<\|im_start\|>|<\|im_end\|>|"
        r"###\s*(system|user|assistant)|"
        r"```system|```user|```assistant)",
        re.IGNORECASE,
    ),
    # Code execution attempts
    "code_execution": re.compile(
        r"(exec\s*\(|eval\s*\(|import\s+os|subprocess\.|"
        r"__import__|system\s*\(|popen\s*\()",
        re.IGNORECASE,
    ),
}


def check_injection(
    text: str,
    patterns: dict[str, re.Pattern] | None = None,
    normalize: bool = True,
) -> InjectionMatch:
    """
    Check text for potential prompt injection patterns.

    Args:
        text: Text to check
        patterns: Custom patterns to use (defaults to INJECTION_PATTERNS)
        normalize: Whether to normalize text before checking

    Returns:
        InjectionMatch with detection result
    """
    if patterns is None:
        patterns = INJECTION_PATTERNS

    # Normalize if requested
    check_text = normalize_text(text) if normalize else text

    # Check each pattern
    for pattern_name, pattern in patterns.items():
        match = pattern.search(check_text)
        if match:
            return InjectionMatch(
                detected=True,
                pattern_name=pattern_name,
                matched_text=match.group(0),
            )

    return InjectionMatch(
        detected=False,
        pattern_name=None,
        matched_text=None,
    )


def is_safe(text: str) -> bool:
    """
    Simple check if text is safe (no injection detected).

    Args:
        text: Text to check

    Returns:
        True if no injection detected
    """
    return not check_injection(text).detected
