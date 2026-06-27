"""
WaveSpeed Batch Image Pipeline for Avatar Generation
Uses openai/gpt-image-2/edit
"""

import os
import asyncio
import aiohttp
import json
from pathlib import Path
from dataclasses import dataclass, field


WAVESPEED_API_URL = "https://api.wavespeed.ai/api/v2"
DEFAULT_MODEL = "openai/gpt-image-2/edit"
OUTPUT_DIR = Path("output/avatars")


@dataclass
class AvatarRequest:
    prompt: str
    reference_image_url: str
    name: str = ""
    aspect_ratio: str = "1:1"
    output_format: str = "png"


@dataclass
class PipelineConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    max_concurrent: int = 4
    output_dir: Path = field(default_factory=lambda: OUTPUT_DIR)
    poll_interval: float = 2.0
    timeout: int = 300


class WaveSpeedBatchPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self._headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    async def _submit(self, session: aiohttp.ClientSession, request: AvatarRequest) -> str:
        payload = {
            "prompt": request.prompt,
            "images": [request.reference_image_url],
            "aspect_ratio": request.aspect_ratio,
            "output_format": request.output_format,
            "enable_base64_output": False,
            "enable_sync_mode": False,
        }
        url = f"{WAVESPEED_API_URL}/{self.config.model}/run"
        async with session.post(url, headers=self._headers, json=payload) as resp:
            if not resp.ok:
                body = await resp.text()
                raise RuntimeError(f"HTTP {resp.status} from WaveSpeed: {body}")
            data = await resp.json()
            return data["data"]["id"]

    async def _poll(self, session: aiohttp.ClientSession, request_id: str) -> dict:
        url = f"{WAVESPEED_API_URL}/predictions/{request_id}/fetch"
        deadline = asyncio.get_event_loop().time() + self.config.timeout
        while asyncio.get_event_loop().time() < deadline:
            async with session.get(url, headers=self._headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
            status = data["data"]["status"]
            if status == "completed":
                return data["data"]
            if status in ("failed", "canceled"):
                raise RuntimeError(f"Request {request_id} ended with status: {status}")
            await asyncio.sleep(self.config.poll_interval)
        raise TimeoutError(f"Request {request_id} timed out after {self.config.timeout}s")

    async def _download(self, session: aiohttp.ClientSession, url: str, path: Path) -> None:
        async with session.get(url) as resp:
            resp.raise_for_status()
            path.write_bytes(await resp.read())

    async def _process_one(
        self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, request: AvatarRequest, index: int
    ) -> dict:
        async with semaphore:
            label = request.name or f"avatar_{index:03d}"
            print(f"[{label}] Submitting...")
            request_id = await self._submit(session, request)
            print(f"[{label}] Polling {request_id}...")
            result = await self._poll(session, request_id)

            outputs = result.get("outputs", [])
            saved = []
            for i, img_url in enumerate(outputs):
                suffix = f"_{i}" if len(outputs) > 1 else ""
                out_path = self.config.output_dir / f"{label}{suffix}.png"
                await self._download(session, img_url, out_path)
                saved.append(str(out_path))
                print(f"[{label}] Saved → {out_path}")

            return {"name": label, "request_id": request_id, "files": saved}

    async def run(self, requests: list[AvatarRequest]) -> list[dict]:
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._process_one(session, semaphore, req, i)
                for i, req in enumerate(requests)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        summary = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                label = requests[i].name or f"avatar_{i:03d}"
                print(f"[{label}] ERROR: {result}")
                summary.append({"name": label, "error": str(result)})
            else:
                summary.append(result)
        return summary


def load_requests(path: str) -> list[AvatarRequest]:
    with open(path) as f:
        data = json.load(f)
    return [AvatarRequest(**item) for item in data]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="WaveSpeed batch avatar image pipeline")
    parser.add_argument("input", help="JSON file with list of avatar request configs")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--concurrent", type=int, default=4)
    parser.add_argument("--output-dir", default="output/avatars")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--api-key", help="WaveSpeed API key (overrides WAVESPEED_API_KEY env var)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("WAVESPEED_API_KEY")
    if not api_key:
        raise SystemExit("Error: provide --api-key or set WAVESPEED_API_KEY")

    config = PipelineConfig(
        api_key=api_key,
        model=args.model,
        max_concurrent=args.concurrent,
        output_dir=Path(args.output_dir),
        timeout=args.timeout,
    )

    requests = load_requests(args.input)
    print(f"Starting batch pipeline: {len(requests)} avatar(s), model={config.model}")

    results = asyncio.run(WaveSpeedBatchPipeline(config).run(requests))

    summary_path = config.output_dir / "results.json"
    summary_path.write_text(json.dumps(results, indent=2))
    print(f"\nDone. Summary written to {summary_path}")

    ok = sum(1 for r in results if "error" not in r)
    print(f"{ok}/{len(results)} succeeded.")


if __name__ == "__main__":
    main()
