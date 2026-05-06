# Release Candidate Guide

The repository now includes the minimum release-hardening assets for a V1 release candidate.

## Required Checks

- `ruff check .`
- `ruff format --check .`
- `pyright`
- `pytest tests/unit tests/integration`
- `pytest tests/experimental`
- `python -m build`

## Artifacts

- wheel
- sdist
- example outputs
- benchmark summary

## Release Notes Inputs

- compatibility matrix
- schema freeze note
- security review
- changelog
