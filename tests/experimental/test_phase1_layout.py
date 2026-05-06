from pathlib import Path


def test_examples_and_docs_scaffold_exist() -> None:
    root = Path(__file__).resolve().parents[2]

    expected = [
        root / "examples" / "langgraph_research_swarm",
        root / "examples" / "langchain_support_swarm",
        root / "examples" / "native_runtime",
        root / "examples" / "marl_training",
        root / "examples" / "cell_simulation",
        root / "docs" / "architecture",
        root / "docs" / "api",
        root / "docs" / "guides",
    ]

    for path in expected:
        assert path.is_dir(), f"Expected directory to exist: {path}"
