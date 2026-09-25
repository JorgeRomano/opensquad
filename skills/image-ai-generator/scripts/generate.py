#!/usr/bin/env python3
"""
Image Generator — Opensquad Skill
Generates images via the Google Gemini image generation API (with OpenRouter fallback).
Note: Google image generation requires a billing-enabled project (not available on the free tier).

Usage:
  # Single image (default 1:1)
  python3 generate.py --prompt "description" --output "path/to/image.jpg" --mode test

  # Single image with aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9)
  python3 generate.py --prompt "description" --output "path/to/image.jpg" --mode production --aspect-ratio 3:4

  # Single image with reference (logo/mascot)
  python3 generate.py --prompt "description" --output "path/to/image.jpg" --reference "path/to/logo.png" --mode production

  # Batch (JSON file with list of {prompt, output, aspect_ratio} objects)
  python3 generate.py --batch "path/to/batch.json" --mode production
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Model configuration per mode (Google Gemini API)
GEMINI_MODELS = {
    "test": "gemini-3.1-flash-lite-image",
    "production": "gemini-3.1-flash-image",
}

# Legacy OpenRouter fallback models if only OPENROUTER_API_KEY is present
OPENROUTER_MODELS = {
    "test": "sourceful/riverflow-v2-fast",
    "production": "google/gemini-3.1-flash-image-preview",
}

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_api_key():
    """Load GEMINI_API_KEY (preferred) or OPENROUTER_API_KEY (fallback)."""
    key = os.environ.get("GEMINI_API_KEY")
    key_source = "GEMINI_API_KEY" if key else None

    if not key:
        key = os.environ.get("OPENROUTER_API_KEY")
        if key:
            key_source = "OPENROUTER_API_KEY"

    if not key:
        # Try loading from .env in project root
        env_candidates = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
        ]
        for env_path in env_candidates:
            env_path = os.path.abspath(env_path)
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("#"):
                            continue
                        if line.startswith("GEMINI_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                key = val
                                key_source = "GEMINI_API_KEY"
                                break
                        elif line.startswith("OPENROUTER_API_KEY=") and not key:
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                key = val
                                key_source = "OPENROUTER_API_KEY"
                if key:
                    break

    if not key:
        print("ERROR: GEMINI_API_KEY not found in environment or .env file.", file=sys.stderr)
        print("Crie sua chave em https://aistudio.google.com/ e configure GEMINI_API_KEY no seu .env", file=sys.stderr)
        print("Atenção: a geração de imagens do Google exige projeto com faturamento ativo (não funciona no free tier).", file=sys.stderr)
        sys.exit(1)

    return key, key_source


def generate_image_gemini(prompt, output_path, mode, api_key, reference_image=None, aspect_ratio="1:1"):
    """Generate an image using Google Gemini Image Generation API (generateContent)."""
    model = GEMINI_MODELS.get(mode, GEMINI_MODELS["test"])
    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"

    parts = []
    if reference_image and os.path.exists(reference_image):
        ext = os.path.splitext(reference_image)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
        mime = mime_map.get(ext, "image/png")
        with open(reference_image, "rb") as img_f:
            ref_b64 = base64.b64encode(img_f.read()).decode("utf-8")
        parts.append({
            "inlineData": {
                "mimeType": mime,
                "data": ref_b64
            }
        })
        parts.append({
            "text": f"Generate an image incorporating the logo or reference asset provided. Description: {prompt}. Output format aspect ratio: {aspect_ratio}."
        })
    else:
        parts.append({
            "text": f"Generate an image: {prompt}. Aspect ratio: {aspect_ratio}. Do not output explanatory text, generate only the visual image."
        })

    payload = json.dumps({
        "contents": [{"parts": parts}]
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        if "limit: 0" in error_body or e.code == 429:
            print(f"\n⚠️  AVISO DE COTA DO GOOGLE GEMINI:", file=sys.stderr)
            print(f"A API de geração de imagens do Google ({model}) exige um projeto com faturamento vinculado (Pay-as-you-go).", file=sys.stderr)
            print(f"No plano Free Tier sem cartão, o Google define 'limit: 0' para modelos de imagem.", file=sys.stderr)
            print(f"Para resolver:", file=sys.stderr)
            print(f"  1. Ative o faturamento no Google Cloud / AI Studio (https://aistudio.google.com/)", file=sys.stderr)
            print(f"  2. OU configure OPENROUTER_API_KEY no seu .env como fallback.\n", file=sys.stderr)
        else:
            print(f"  Google API error [{e.code}]: {error_body[:250]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Request error: {e}", file=sys.stderr)
        return False

    candidates = data.get("candidates", [])
    if not candidates:
        print(f"  No content returned by Google model {model}: {data}", file=sys.stderr)
        return False

    parts_resp = candidates[0].get("content", {}).get("parts", [])
    img_data = None

    for p in parts_resp:
        if "inlineData" in p and p["inlineData"].get("data"):
            img_data = p["inlineData"]["data"]
            break
        elif "text" in p and p["text"].startswith("data:image"):
            raw_text = p["text"]
            img_data = raw_text.split(",", 1)[1] if "," in raw_text else raw_text
            break

    if not img_data:
        print(f"  Model response did not contain image data: {parts_resp}", file=sys.stderr)
        return False

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(img_data))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  OK: {output_path} ({size_kb:.0f} KB) [Google Gemini Image: {model}]")
    return True


def generate_image_openrouter(prompt, output_path, mode, api_key, reference_image=None):
    """Fallback generator for legacy OpenRouter credentials."""
    model = OPENROUTER_MODELS.get(mode, OPENROUTER_MODELS["test"])

    if reference_image and os.path.exists(reference_image):
        ext = os.path.splitext(reference_image)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
        mime = mime_map.get(ext, "image/png")
        with open(reference_image, "rb") as img_f:
            img_b64 = base64.b64encode(img_f.read()).decode("utf-8")
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            {"type": "text", "text": f"Generate an image using the logo/mascot shown in the reference image above. {prompt}. Only output the image, no text."}
        ]
    else:
        content = f"Generate an image: {prompt}. Only output the image, no text."

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}]
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"  OpenRouter error [{e.code}]: {error_body[:200]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Request error: {e}", file=sys.stderr)
        return False

    images = data.get("choices", [{}])[0].get("message", {}).get("images", [])
    if not images:
        content_resp = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if content_resp and isinstance(content_resp, str) and content_resp.startswith("data:image"):
            img_data = content_resp.split(",", 1)[1] if "," in content_resp else content_resp
        else:
            print(f"  No image returned by model {model}", file=sys.stderr)
            return False
    else:
        img_data = images[0].get("image_url", {}).get("url", "")
        if img_data.startswith("data:"):
            img_data = img_data.split(",", 1)[1]

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(img_data))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  OK: {output_path} ({size_kb:.0f} KB) [OpenRouter fallback: {model}]")
    return True


def generate_image(prompt, output_path, mode, api_key, key_source, reference_image=None, aspect_ratio="1:1"):
    """Route image generation to Gemini or OpenRouter fallback based on key source."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if key_source == "GEMINI_API_KEY" or not api_key.startswith("sk-or-"):
        return generate_image_gemini(prompt, output_path, mode, api_key, reference_image=reference_image, aspect_ratio=aspect_ratio)
    else:
        return generate_image_openrouter(prompt, output_path, mode, api_key, reference_image=reference_image)


def main():
    parser = argparse.ArgumentParser(description="Generate images via the Google Gemini image generation API")
    parser.add_argument("--prompt", help="Text prompt for single image generation")
    parser.add_argument("--output", help="Output file path for single image")
    parser.add_argument("--batch", help="Path to JSON batch file")
    parser.add_argument("--mode", choices=["test", "production"], default="test",
                        help="Generation mode: test (fast) or production (high-quality)")
    parser.add_argument("--reference", help="Path to reference image to include in the prompt")
    parser.add_argument("--aspect-ratio", choices=["1:1", "3:4", "4:3", "9:16", "16:9"], default="1:1",
                        help="Aspect ratio for image generation (default: 1:1)")
    args = parser.parse_args()

    if not args.prompt and not args.batch:
        parser.error("Either --prompt or --batch is required")

    api_key, key_source = load_api_key()
    provider_name = "Google Gemini Image" if key_source == "GEMINI_API_KEY" else "OpenRouter (legacy fallback)"
    model_name = GEMINI_MODELS[args.mode] if key_source == "GEMINI_API_KEY" else OPENROUTER_MODELS[args.mode]
    print(f"Image Generator — Provider: {provider_name} | Mode: {args.mode} | Model: {model_name} | Ratio: {args.aspect_ratio}")

    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            items = json.load(f)
        print(f"Generating {len(items)} images...\n")
        success = 0
        for i, item in enumerate(items, 1):
            prompt = item["prompt"]
            output = item["output"]
            ref = item.get("reference")
            ratio = item.get("aspect_ratio", args.aspect_ratio)
            print(f"[{i}/{len(items)}] {os.path.basename(output)} ({ratio})...")
            if generate_image(prompt, output, args.mode, api_key, key_source, reference_image=ref, aspect_ratio=ratio):
                success += 1
            if i < len(items):
                time.sleep(1)  # Rate limiting
        print(f"\nDone: {success}/{len(items)} images generated.")
        sys.exit(0 if success == len(items) else 1)
    else:
        if not args.output:
            parser.error("--output is required for single image generation")
        print(f"Generating: {os.path.basename(args.output)}...")
        ok = generate_image(args.prompt, args.output, args.mode, api_key, key_source, reference_image=args.reference, aspect_ratio=args.aspect_ratio)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
