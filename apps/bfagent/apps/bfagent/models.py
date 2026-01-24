"""
Django Models for BF Agent
Re-exports from modular model files
"""

# Import ALL models from the main file (includes handlers, registry imports)
from .models_main import *  # noqa

# Import additional models not in models_main
from .models_domains import (
    DomainArt,
    DomainType,
    DomainPhase,
)

from .models_context_enrichment import (
    ContextSource,
    ContextSchema,
    ContextEnrichmentLog,
)

from .models_feature_documents import (
    FeatureDocument,
    FeatureDocumentKeyword,
)

# Illustration System Lookup Tables
from .models_lookups_illustration import (
    IllustrationArtStyle,
    IllustrationImageType,
    IllustrationAIProvider,
    IllustrationImageStatus,
)

# Cascade Autonomous Work Sessions
from .models_cascade import (
    CascadeWorkSession,
    CascadeWorkLog,
)

# Autocoding System
from .models_autocoding import (
    AutocodingRun,
    ToolCall,
    Artifact,
)
