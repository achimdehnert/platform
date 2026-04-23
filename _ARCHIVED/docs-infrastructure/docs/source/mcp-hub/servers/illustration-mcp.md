# Illustration MCP

AI Image Generation Tools Server.

## Installation

```bash
cd mcp-hub/illustration_mcp
pip install -e .
```

## Konfiguration

```json
{
  "mcpServers": {
    "illustration-mcp": {
      "command": "python",
      "args": ["-m", "illustration_mcp.server"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "STABILITY_API_KEY": "..."
      }
    }
  }
}
```

## Tools

### generate_image

Bild aus Text-Prompt generieren.

```python
result = await generate_image(
    prompt="A fantasy castle on a mountain",
    model="dall-e-3",
    size="1024x1024",
    quality="hd",
)
```

### edit_image

Bestehendes Bild bearbeiten.

```python
result = await edit_image(
    image_path="/path/to/image.png",
    prompt="Add a dragon flying over the castle",
    mask_path="/path/to/mask.png",  # optional
)
```

### generate_variations

Variationen eines Bildes erstellen.

```python
result = await generate_variations(
    image_path="/path/to/image.png",
    n=4,
)
```

## Unterstützte Provider

| Provider | Models |
|----------|--------|
| OpenAI | DALL-E 3, DALL-E 2 |
| Stability AI | Stable Diffusion XL |
| Midjourney | (via API) |
