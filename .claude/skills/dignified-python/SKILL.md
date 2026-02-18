---
name: dignified-python
description: Load ONLY for Python code
  Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception
  handling patterns, modern type syntax (list[str], str | None), pathlib operations,
  ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level.
  Also provides production-tested code smell patterns from Dagster Labs for API design,
  parameter complexity, and code organization. Essential for maintaining erk's dignified
  Python standards.
---

# Dignified Python - Python 3.12 Coding Standards

## Core Knowledge (ALWAYS Loaded)

@dignified-python-core.md
@type-annotations.md

## How to Use This Skill

1. **Core knowledge** is loaded automatically (LBYL, pathlib, ABC, imports, exceptions)
2. **Type annotations** are loaded automatically (Python 3.12 specific features including PEP 695)
3. **Each file is self-contained** with complete guidance for its domain
