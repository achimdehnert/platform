# LLM MCP

LLM Integration Server für OpenAI, Anthropic und lokale Modelle.

## Installation

```bash
cd mcp-hub/llm_mcp
pip install -e .
```

## Konfiguration

```json
{
  "mcpServers": {
    "llm-mcp": {
      "command": "python",
      "args": ["-m", "llm_mcp.server"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

## Tools

### generate_text

Generiert Text mit einem LLM.

```python
result = await generate_text(
    prompt="Write a short story",
    model="gpt-4o",
    temperature=0.7,
    max_tokens=1000,
)
```

### chat

Chat-Completion mit Konversationshistorie.

```python
result = await chat(
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"},
    ],
    model="claude-3-sonnet",
)
```

### embed

Text-Embeddings generieren.

```python
result = await embed(
    text="Hello world",
    model="text-embedding-3-small",
)
```

## HTTP Gateway

Optional: HTTP-Gateway für REST-API Zugriff.

```bash
python -m llm_mcp.http_gateway --port 8100
```

```bash
curl -X POST http://localhost:8100/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "model": "gpt-4o"}'
```

## Unterstützte Provider

| Provider | Models |
|----------|--------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo |
| Anthropic | claude-3-opus, claude-3-sonnet, claude-3-haiku |
| Groq | llama-3.3-70b, mixtral-8x7b |
| Ollama | llama3, mistral, codellama (lokal) |
