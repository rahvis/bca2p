from pathlib import Path


def test_core_directories_exist() -> None:
    root = Path(__file__).resolve().parents[2]

    expected = [
        root / "src" / "bca2p" / "core",
        root / "src" / "bca2p" / "graph",
        root / "src" / "bca2p" / "runtime",
        root / "src" / "bca2p" / "learning",
        root / "src" / "bca2p" / "transport",
        root / "src" / "bca2p" / "registry",
        root / "src" / "bca2p" / "observability",
        root / "src" / "bca2p" / "integrations" / "langgraph",
        root / "src" / "bca2p" / "integrations" / "langchain",
        root / "src" / "bca2p" / "native",
        root / "src" / "bca2p" / "marl",
        root / "src" / "bca2p" / "sim",
        root / "src" / "bca2p" / "distributed",
    ]

    for path in expected:
        assert path.is_dir(), f"Expected directory to exist: {path}"
