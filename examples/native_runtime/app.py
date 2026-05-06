from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from examples.langgraph_research_swarm.app import build_biograph

from bca2p.native import NativeBioRuntime
from bca2p.runtime import RuntimeConfig


def run_native_example() -> dict:
    runtime = NativeBioRuntime.from_graph(
        build_biograph(),
        config=RuntimeConfig(max_steps=5),
    )
    result = runtime.invoke({"workflow_id": "native-example"})
    return {
        "final_state": result.final_state,
        "steps_executed": result.steps_executed,
        "completed": result.completed,
    }


if __name__ == "__main__":
    print(run_native_example())
