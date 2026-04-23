# iil-hub-identity

AI-detection-resistant Hub Visual & Language Identity System for the IIL Platform.

## Install

```bash
pip install iil-hub-identity
pip install iil-hub-identity[mutation]  # + aifw for LLM mutations
pip install iil-hub-identity[cli]       # + typer CLI
```

## Usage

```python
from hub_identity.core.schema import HubDNA
from hub_identity.auditors import audit_hub
from hub_identity.mutations import MutationPipeline

# Load hub DNA (with _base.yaml inheritance)
dna = HubDNA.from_yaml("hub_dnas/risk-hub.yaml")

# Audit
score = audit_hub(dna)
print(score.explain())

# Mutate (deterministic first, LLM only if needed)
pipeline = MutationPipeline(threshold=25.0)
new_dna = pipeline.mutate(dna, score)
```
