"""Load an EcoSort .tflite model, assert the Flutter tensor contract, return a predict function.

TensorFlow is imported lazily so the rest of ecosort_ml stays importable (and testable) without it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np

Runner = Callable[[np.ndarray], np.ndarray]


class ContractError(AssertionError):
    """The model does not match the [1,224,224,3] float32 -> [1,20] contract agreed with mobile."""


def _interpreter_cls():
    try:
        import tensorflow as tf

        return tf.lite.Interpreter
    except ImportError:  # pragma: no cover - optional lightweight runtimes
        try:
            from ai_edge_litert.interpreter import Interpreter
        except ImportError:
            from tflite_runtime.interpreter import Interpreter  # type: ignore[no-redef]
        return Interpreter


def make_tflite_runner(model_path: Path, num_threads: int = 4) -> Runner:
    interpreter = _interpreter_cls()(model_path=str(model_path), num_threads=num_threads)
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()
    out = interpreter.get_output_details()
    if len(inp) != 1 or len(out) != 1:
        raise ContractError(f"{model_path.name}: expected 1 input/1 output, got {len(inp)}/{len(out)}")
    if list(inp[0]["shape"]) != [1, 224, 224, 3] or inp[0]["dtype"] != np.float32:
        raise ContractError(f"{model_path.name}: bad input tensor {inp[0]['shape']} {inp[0]['dtype']}")
    if list(out[0]["shape"]) != [1, 20]:
        raise ContractError(f"{model_path.name}: bad output tensor {out[0]['shape']}")
    in_idx, out_idx = inp[0]["index"], out[0]["index"]

    def run(img: np.ndarray) -> np.ndarray:
        interpreter.set_tensor(in_idx, np.expand_dims(img.astype(np.float32), axis=0))
        interpreter.invoke()
        return interpreter.get_tensor(out_idx)[0]

    return run
