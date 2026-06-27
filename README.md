# WaveSpeed Batch Avatar Image Pipeline

Generate avatar images in batch using the [WaveSpeed](https://wavespeed.ai) API.

## Setup

```bash
pip install -r requirements.txt
export WAVESPEED_API_KEY=your_api_key_here
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
    "guidance_scale": 3.5
  }
]
```

## Output

Images are saved to `output/avatars/<name>.png`. A `results.json` summary is written there as well.
