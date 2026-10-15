"""Private Manga Director-owned ComfyUI workflow for one prompt-only PNG."""

from __future__ import annotations

import re
from typing import Final

COMFYUI_OUTPUT_NODE_ID: Final = "7"
COMFYUI_FIXED_NODE_TYPES: Final = (
    "CheckpointLoaderSimple",
    "CLIPTextEncode",
    "EmptyLatentImage",
    "KSampler",
    "VAEDecode",
    "SaveImage",
)
_CHECKPOINT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,199}\.(?:ckpt|safetensors)$")
_MAX_PROMPT_CHARS = 8_000
_MAX_SEED = 2**63 - 1


def validate_comfyui_checkpoint_name(value: object) -> str:
    """Return one safe local checkpoint basename or fail closed."""

    if (
        not isinstance(value, str)
        or value != value.strip()
        or not _CHECKPOINT_NAME.fullmatch(value)
        or ".." in value
    ):
        raise ValueError("ComfyUI checkpoint name is unavailable")
    return value


def build_comfyui_fixed_workflow(
    prompt: str,
    checkpoint_name: str,
    *,
    seed: int,
) -> dict[str, object]:
    """Build the exact v1 core-node graph; callers cannot supply graph structure."""

    if (
        not isinstance(prompt, str)
        or not prompt.strip()
        or prompt != prompt.strip()
        or len(prompt) > _MAX_PROMPT_CHARS
        or "\x00" in prompt
    ):
        raise ValueError("ComfyUI prompt is unavailable")
    checkpoint = validate_comfyui_checkpoint_name(checkpoint_name)
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= _MAX_SEED:
        raise ValueError("ComfyUI seed is unavailable")

    graph = _workflow_template(prompt, checkpoint, seed)
    validate_comfyui_fixed_workflow(
        graph,
        prompt=prompt,
        checkpoint_name=checkpoint,
        seed=seed,
    )
    return graph


def _workflow_template(prompt: str, checkpoint_name: str, seed: int) -> dict[str, object]:
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint_name},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        COMFYUI_OUTPUT_NODE_ID: {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "manga_director_v7_04",
                "images": ["6", 0],
            },
        },
    }


def validate_comfyui_fixed_workflow(
    graph: object,
    *,
    prompt: str,
    checkpoint_name: str,
    seed: int,
) -> None:
    """Reject arbitrary nodes, custom nodes, altered edges, scripts, and batches."""

    checkpoint = validate_comfyui_checkpoint_name(checkpoint_name)
    expected = _workflow_template(prompt, checkpoint, seed)
    if type(graph) is not dict or graph != expected:
        raise ValueError("ComfyUI workflow graph is not the fixed v1 graph")
