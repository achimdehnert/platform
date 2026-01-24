"""
Similarity service for document comparison.
Uses sentence-transformers for semantic similarity scoring.
"""
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Lazy load to avoid startup overhead
_model = None


def get_model():
    """Lazy load the sentence-transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded sentence-transformer model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer: {e}")
            _model = False  # Mark as failed
    return _model if _model else None


def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity between two texts.
    Returns a score between 0.0 and 1.0.
    """
    model = get_model()
    if not model:
        # Fallback to simple word overlap
        return _simple_similarity(text1, text2)
    
    try:
        from sentence_transformers import util
        embeddings = model.encode([text1[:5000], text2[:5000]], convert_to_tensor=True)
        similarity = util.cos_sim(embeddings[0], embeddings[1])
        return float(similarity.item())
    except Exception as e:
        logger.error(f"Similarity computation failed: {e}")
        return _simple_similarity(text1, text2)


def _simple_similarity(text1: str, text2: str) -> float:
    """Fallback: Simple word overlap similarity (Jaccard)."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def compute_file_similarity(file1: Path, file2: Path) -> float:
    """Compute similarity between two files."""
    try:
        text1 = file1.read_text(encoding='utf-8', errors='ignore')
        text2 = file2.read_text(encoding='utf-8', errors='ignore')
        return compute_similarity(text1, text2)
    except Exception as e:
        logger.error(f"Failed to compute file similarity: {e}")
        return 0.0


def validate_redundancy_group(
    docs_root: Path,
    files: List[str],
    threshold: float = 0.4
) -> Tuple[bool, float, str]:
    """
    Validate if files in a group are truly similar.
    
    Returns:
        (is_valid, avg_similarity, reason)
    """
    if len(files) < 2:
        return False, 0.0, "Need at least 2 files"
    
    # Find actual file paths
    file_paths = []
    for f in files:
        # Try direct path
        path = docs_root / f
        if not path.exists():
            # Search in subdirectories
            matches = list(docs_root.rglob(f))
            if matches:
                path = matches[0]
        if path.exists():
            file_paths.append(path)
    
    if len(file_paths) < 2:
        return False, 0.0, f"Only {len(file_paths)} files found"
    
    # Compute pairwise similarities
    similarities = []
    for i in range(len(file_paths)):
        for j in range(i + 1, len(file_paths)):
            sim = compute_file_similarity(file_paths[i], file_paths[j])
            similarities.append(sim)
            logger.debug(f"Similarity {file_paths[i].name} <-> {file_paths[j].name}: {sim:.3f}")
    
    avg_sim = sum(similarities) / len(similarities) if similarities else 0.0
    
    if avg_sim >= threshold:
        return True, avg_sim, f"Average similarity: {avg_sim:.1%}"
    else:
        return False, avg_sim, f"Too different: {avg_sim:.1%} < {threshold:.0%} threshold"


def get_similarity_label(score: float) -> str:
    """Get human-readable label for similarity score."""
    if score >= 0.8:
        return "very_high"
    elif score >= 0.6:
        return "high"
    elif score >= 0.4:
        return "medium"
    elif score >= 0.2:
        return "low"
    else:
        return "none"
