"""Focused tests for the Manga Director-owned ComfyUI v1 graph."""

from __future__ import annotations

import copy

import pytest

from manga_director.production.next_generation_comfyui_fixed_workflow import (
    COMFYUI_FIXED_NODE_TYPES,
    build_comfyui_fixed_workflow,
    validate_comfyui_checkpoint_name,
    validate_comfyui_fixed_workflow,
)

_PROMPT = "one monochrome manga panel"
_CHECKPOINT = "local-model.safetensors"


def test_fixed_graph_has_only_owned_core_nodes_and_one_output() -> None:
    graph = build_comfyui_fixed_workflow(_PROMPT, _CHECKPOINT, seed=17)

    assert tuple(dict.fromkeys(node["class_type"] for node in graph.values())) == (
        "CheckpointLoaderSimple",
        "CLIPTextEncode",
        "EmptyLatentImage",
        "KSampler",
        "VAEDecode",
        "SaveImage",
    )
    assert set(node["class_type"] for node in graph.values()) == set(
        COMFYUI_FIXED_NODE_TYPES
    )
    assert graph["4"]["inputs"] == {"width": 1024, "height": 1024, "batch_size": 1}
    assert graph["7"] == {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "manga_director_v7_04", "images": ["6", 0]},
    }
    validate_comfyui_fixed_workflow(
        graph, prompt=_PROMPT, checkpoint_name=_CHECKPOINT, seed=17
    )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda graph: graph.update({"8": {"class_type": "CustomScript", "inputs": {}}}),
        lambda graph: graph["5"]["inputs"].update({"batch_size": 2}),
        lambda graph: graph["4"]["inputs"].update({"batch_size": 2}),
        lambda graph: graph["7"]["inputs"].update({"images": ["5", 0]}),
        lambda graph: graph["7"]["inputs"].update({"filename_prefix": "../escape"}),
    ),
)
def test_fixed_graph_rejects_arbitrary_nodes_edges_batches_and_paths(mutation: object) -> None:
    graph = build_comfyui_fixed_workflow(_PROMPT, _CHECKPOINT, seed=17)
    changed = copy.deepcopy(graph)
    mutation(changed)  # type: ignore[operator]

    with pytest.raises(ValueError, match="fixed v1 graph"):
        validate_comfyui_fixed_workflow(
            changed, prompt=_PROMPT, checkpoint_name=_CHECKPOINT, seed=17
        )


@pytest.mark.parametrize(
    "value",
    (
        "../model.safetensors",
        "folder/model.safetensors",
        "folder\\model.ckpt",
        "model.py",
        "*.safetensors",
        "https://example.invalid/model.safetensors",
    ),
)
def test_checkpoint_is_one_exact_safe_local_basename(value: str) -> None:
    with pytest.raises(ValueError, match="checkpoint"):
        validate_comfyui_checkpoint_name(value)


def test_prompt_seed_and_caller_graph_are_deterministic() -> None:
    first = build_comfyui_fixed_workflow(_PROMPT, _CHECKPOINT, seed=17)
    second = build_comfyui_fixed_workflow(_PROMPT, _CHECKPOINT, seed=17)

    assert first == second
    assert first is not second
    assert first["2"]["inputs"]["text"] == _PROMPT
    with pytest.raises(ValueError, match="prompt"):
        build_comfyui_fixed_workflow("", _CHECKPOINT, seed=17)
    with pytest.raises(ValueError, match="seed"):
        build_comfyui_fixed_workflow(_PROMPT, _CHECKPOINT, seed=-1)
