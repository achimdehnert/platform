"""Core abstractions for hub identity system."""

from hub_identity.core.merge import deep_merge
from hub_identity.core.plugins import AuditorPlugin, MutationStrategy, OutputPlugin
from hub_identity.core.schema import HubDNA, VisualDNA, VoiceDNA
from hub_identity.core.scoring import ScoreNode, ScoreTree

__all__ = [
    "AuditorPlugin",
    "HubDNA",
    "MutationStrategy",
    "OutputPlugin",
    "ScoreNode",
    "ScoreTree",
    "VisualDNA",
    "VoiceDNA",
    "deep_merge",
]
