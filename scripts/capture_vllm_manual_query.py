from __future__ import annotations

import json
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots" / "vllm_manual_query.png"
MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"
BASE_URL = "http://localhost:8000"


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    models = get_json(f"{BASE_URL}/v1/models")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Convert this question to SQLite SQL only. Question: "
                    "How many users received commentator badges in 2014?"
                ),
            }
        ],
        "temperature": 0,
        "max_tokens": 256,
    }
    result = post_json(f"{BASE_URL}/v1/chat/completions", payload)

    sql = result["choices"][0]["message"]["content"].strip()
    text = "\n".join(
        [
            "$ curl http://localhost:8000/v1/models",
            json.dumps(models, indent=2)[:1400],
            "",
            "$ curl http://localhost:8000/v1/chat/completions ...",
            "Question: How many users received commentator badges in 2014?",
            "",
            "Model response:",
            sql,
        ]
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1600, 1000), "#0f172a")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    x, y = 36, 32
    line_height = 18
    for paragraph in text.splitlines():
        for line in textwrap.wrap(paragraph, width=150) or [""]:
            draw.text((x, y), line, fill="#e5e7eb", font=font)
            y += line_height
            if y > 960:
                break
        if y > 960:
            break
    image.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
