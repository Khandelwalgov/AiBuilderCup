"""Pinned public model artifacts. Downloads weights only, never invokes hosted inference."""

import hashlib
import os
from pathlib import Path
from urllib.request import urlopen

MODEL = "Xenova/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "b9e20f0c6dd7e5f88c72259765011e6a3a9196bc"
FILES = {
    "onnx/model_quantized.onnx": "b3234f3f2e79d23c1cc844c7ce1305563d51ee2f2a449f9f1d8fbe3f7668d9a3",
    "tokenizer.json": "b60b6b43406a48bf3638526314f3d232d97058bc93472ff2de930d43686fa441",
}


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(root: Path) -> None:
    for name, expected in FILES.items():
        if checksum(root / name) != expected:
            raise ValueError("Local embedding artifact checksum mismatch")


def download(root: Path) -> None:
    for name, expected in FILES.items():
        target = root / name
        if target.exists() and checksum(target) == expected:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".part")
        try:
            with (
                urlopen(
                    f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}", timeout=60
                ) as source,
                temp.open("wb") as dest,
            ):
                size = 0
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > 125_000_000:
                        raise ValueError("Model download exceeds pinned artifact bound")
                    dest.write(chunk)
            if checksum(temp) != expected:
                raise ValueError("Downloaded embedding artifact checksum mismatch")
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
    verify(root)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    download(args.directory)
    print(f"Verified local CPU embedding model {MODEL}@{REVISION}")
