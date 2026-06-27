# WaveSpeed Batch Avatar Image Pipeline

Generate avatar images in batch using the [WaveSpeed](https://wavespeed.ai) API.

## Setup

```bash
pip install -r requirements.txt
export WAVESPEED_API_KEY=your_api_key_here   # get this from wavespeed.ai → API Keys
```

## Usage

```bash
python pipeline.py avatars.json
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `wavespeed-ai/flux-dev` | WaveSpeed model ID |
| `--concurrent` | `4` | Max parallel requests |
| `--output-dir` | `output/avatars` | Where to save images |
| `--timeout` | `300` | Seconds before a request times out |

## Input format (`avatars.json`)

```json
[
  {
    "name": "my_avatar",
    "prompt": "Professional headshot, studio lighting",
    "negative_prompt": "blurry, low quality",
    "width": 512,
    "height": 512,
    "num_inference_steps": 28,
    "guidance_scale": 3.5,
    "reference_image_url": "https://your-public-url.com/your-avatar.jpg",
    "image_strength": 0.75
  }
]
```

| Field | Description |
|-------|-------------|
| `reference_image_url` | Publicly accessible URL of your reference avatar image. The model uses it as a visual starting point. |
| `image_strength` | `0.0–1.0` — how much the reference influences the result. Higher = closer to your reference. Default `0.75`. |

## Output

Images are saved to `output/avatars/<name>.png`. A `results.json` summary is written there as well.
