---
name: image-ai-generator
description: >
  Generates images via the Google Gemini image generation API.
  Supports two modes: test (fast model for iteration) and production (high-quality model for final output).
  Handles prompt construction, API calls, base64 decoding, aspect ratios, and file saving.
  Supports reference images (logos, mascots) for brand-consistent generation.
  Falls back to OpenRouter when only OPENROUTER_API_KEY is present.
description_pt-BR: >
  Gera imagens via API de geração de imagens do Google Gemini.
  Suporta dois modos: test (modelo rápido para iteração) e production (modelo de alta qualidade para output final).
  Cuida da construção de prompts, chamadas de API, decodificação base64, aspect ratios e salvamento de arquivos.
  Suporta imagens de referência (logos, mascotes) para geração consistente com a marca.
  Usa OpenRouter como fallback quando apenas OPENROUTER_API_KEY está presente.
type: script
version: "1.1.0"
script:
  path: scripts/generate.py
  runtime: python3
  invoke: "python3 {skill_path}/scripts/generate.py --prompt \"{prompt}\" --output \"{output}\" --mode \"{mode}\" --aspect-ratio \"{aspect_ratio}\""
env:
  - GEMINI_API_KEY
categories: [assets, images, ai, generation]
---

# Image Generator

## When to use

Use the Image Generator when you need to create visual assets from text prompts. This skill calls the Google Gemini image generation API directly and saves the resulting images locally.

> **Billing required.** Google's image generation models are not available on the free tier. The API key must belong to a Google AI Studio / Google Cloud project with billing enabled (pay-as-you-go). Without billing, the API returns `limit: 0` and no image is generated. As an alternative, set `OPENROUTER_API_KEY` to use the OpenRouter fallback.

**IMPORTANT: Think twice before generating images.** Image generation costs money and takes time. Before generating:
1. Check if a suitable image already exists in the squad's assets folder
2. Check if a web search could find a free/open image that works
3. Consider if the image is truly necessary for the content quality
4. Only generate when no existing alternative is good enough
5. **Generate only what you need** — never batch-generate "test variations". One image is enough to validate a concept.

## Modes

### Test mode (`--mode test`)
- **Model:** `gemini-3.1-flash-lite-image` (Google) / `sourceful/riverflow-v2-fast` (OpenRouter fallback)
- **When to use:** During iteration, testing layouts, checking composition, reviewing concepts
- **Cost / Speed:** Fast generation, ideal for drafts and rapid prototyping
- **Quality:** Good enough for layout validation and concept approval

### Production mode (`--mode production`)
- **Model:** `gemini-3.1-flash-image` (Google) / `google/gemini-3.1-flash-image-preview` (OpenRouter fallback)
- **When to use:** Only when generating the final images that will be published or delivered
- **Cost / Speed:** High photorealism, sharp typography rendering
- **Quality:** Production-ready quality for social media (Instagram, LinkedIn, YouTube, etc.)

**Default mode is `test`.** Only switch to `production` when the user has approved the layout/composition and you are generating the final deliverable images.

## Instructions

### Single image generation

```bash
python3 skills/image-ai-generator/scripts/generate.py \
  --prompt "A detailed description of the image to generate" \
  --output "squads/{squad}/output/{run_id}/assets/image-name.jpg" \
  --mode test \
  --aspect-ratio 1:1
```

Supported aspect ratios: `1:1` (feed square), `3:4` or `4:3`, `9:16` (stories/reels), `16:9` (banners/thumbnails).

### With a reference image (logo, mascot, brand asset)

Use `--reference` to send a local image to the model as visual context. The model will incorporate the referenced image (e.g., a logo or mascot) into the generated output.

```bash
python3 skills/image-ai-generator/scripts/generate.py \
  --prompt "A social media banner featuring the company logo prominently in the center" \
  --output "squads/{squad}/output/{run_id}/assets/banner.jpg" \
  --reference "squads/{squad}/assets/logo.png" \
  --mode production \
  --aspect-ratio 16:9
```

Supported reference formats: PNG, JPEG, WEBP, GIF.

### Batch generation

```bash
python3 skills/image-ai-generator/scripts/generate.py \
  --batch "squads/{squad}/output/{run_id}/assets/batch.json" \
  --mode production
```

The batch JSON file should contain:
```json
[
  {"prompt": "Description of image 1", "output": "path/to/image1.jpg", "aspect_ratio": "1:1"},
  {"prompt": "Description of image 2", "output": "path/to/image2.jpg", "aspect_ratio": "4:3"}
]
```

Each item can optionally include a `"reference": "path/to/ref.png"` field.

### Prompt guidelines

- Be specific about composition, lighting, style, and mood
- Specify aspect ratio matching the platform target
- Include stylistic descriptors (e.g., "minimalist studio lighting, editorial photography")
- Include "clean composition" to avoid cluttered outputs

## Available operations

- **Single generation** — Generate one image from a text prompt
- **Batch generation** — Generate multiple images from a JSON batch file
- **Mode selection** — Choose between test (fast) and production (high-quality) models
- **Aspect ratio control** — Choose format (`1:1`, `3:4`, `4:3`, `9:16`, `16:9`)
- **Reference image** — Send a logo/mascot/brand asset as visual context for the generation

## Error handling

- If `GEMINI_API_KEY` is not set, the script alerts the user with instructions to get a key from [Google AI Studio](https://aistudio.google.com/) and exits.
- If only `OPENROUTER_API_KEY` is present, the script seamlessly uses backward-compatible fallback mode.
- If the API returns an error, the script prints the status code and body, then exits with code 1.

