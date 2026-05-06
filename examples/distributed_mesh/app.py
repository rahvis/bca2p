from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from bca2p.core import AgentProfile, ReceptorSpec, SignalEnvelope, SignalMode
from bca2p.distributed import DistributedCoordinator


def _profile(agent_id: str, scope: str, receptor_id: str) -> AgentProfile:
    return AgentProfile(
        agent_id=agent_id,
        scopes=[scope],
        receptors=[
            ReceptorSpec(
                receptor_id=receptor_id,
                accepted_modes=[SignalMode.ENDOCRINE, SignalMode.PARACRINE, SignalMode.SYNAPTIC],
            )
        ],
    )


async def run_distributed_example() -> dict:
    coordinator = DistributedCoordinator()
    coordinator.register_agent(
        _profile("planner", "global", "goal"),
        lambda signal: SignalEnvelope(
            signal_id=f"{signal.signal_id}:ack",
            mode=signal.mode,
            sender="planner",
            recipient_scope=signal.sender,
            receptor=signal.receptor,
            payload={"status": "received"},
        ),
    )
    coordinator.register_agent(
        _profile("worker", "global", "goal"),
        lambda signal: SignalEnvelope(
            signal_id=f"{signal.signal_id}:worker",
            mode=signal.mode,
            sender="worker",
            recipient_scope=signal.sender,
            receptor=signal.receptor,
            payload={"status": "executed"},
        ),
    )
    coordinator.connect("planner", "worker", scopes=("global",))

    signal = SignalEnvelope(
        signal_id="distributed-1",
        mode=SignalMode.PARACRINE,
        sender="planner",
        recipient_scope="global",
        receptor="goal",
        payload={"task": "collect evidence"},
    )
    delivered = await coordinator.route(signal)
    coordinator.mesh_transport.isolate("worker")
    dropped = await coordinator.route(
        signal.model_copy(update={"signal_id": "distributed-2", "mode": SignalMode.SYNAPTIC})
    )
    coordinator.mesh_transport.heal("worker")
    replayed = coordinator.replay_signal_log()
    return {
        "delivered": len(delivered),
        "dropped_after_partition": len(dropped),
        "log_entries": len(replayed),
        "statuses": [entry.status for entry in replayed],
    }


if __name__ == "__main__":
    print(asyncio.run(run_distributed_example()))
