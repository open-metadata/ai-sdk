---
name: debug-ci
description: Use when CI/CD pipeline fails. Provides systematic diagnosis for lint,
  type, test, and build failures across Python, TypeScript, Java, Rust, and n8n SDKs.
---

# Debug CI Failures

Systematically diagnose and fix CI failures across all SDKs.

## Usage
```
/debug-ci [workflow-url]
```

## Diagnosis Process

### 1. Identify the Failing Job

Check the CI summary to identify which SDK(s) failed:
- Rust CLI
- Python SDK
- TypeScript SDK
- Java SDK
- n8n Node

### 2. Categorize the Failure

| Category | Symptoms | Common Causes |
|----------|----------|---------------|
| **Lint** | "cargo fmt", "ruff", "eslint", "spotless" errors | Code not formatted, style violations |
| **Type** | "ty", "tsc", "clippy" errors | Type mismatches, missing types |
| **Test** | "pytest", "vitest", "mvn test", "cargo test" failures | Logic bugs, missing mocks, flaky tests |
| **Build** | Compilation errors | Syntax errors, missing dependencies |
| **Integration** | Timeout, 401, 404 errors | Credentials, network, API changes |

### 3. Fix by Category

#### Lint Failures
```bash
# Fix all formatting/linting
make format

# Then verify
make lint
```

#### Type Failures (Python)
```bash
cd python && ty check src tests
```

#### Test Failures
```bash
# Run specific SDK tests locally
cd <sdk> && <test-command>

# Run with verbose output
pytest -v --tb=long  # Python
npm test -- --reporter=verbose  # TypeScript
mvn test -X  # Java
cargo test -- --nocapture  # Rust
```

#### Build Failures
- Check for syntax errors in recent changes
- Verify dependencies are installed
- Check for version mismatches

### 4. Verify Fix

```bash
# Run the same checks CI runs
make lint
make test-all
```

## Common CI Issues

### Python
| Error | Fix |
|-------|-----|
| `ruff check` fails | `cd python && ruff check --fix src tests` |
| `ruff format` fails | `cd python && ruff format src tests` |
| Import errors | Check `__init__.py` exports |
| pytest collection error | Check for syntax errors in test files |

### TypeScript
| Error | Fix |
|-------|-----|
| ESLint errors | `cd typescript && npm run lint -- --fix` |
| Type errors | Fix type annotations, check `models.ts` |
| Module not found | `npm ci` to reinstall deps |

### Java
| Error | Fix |
|-------|-----|
| Spotless check fails | `cd java && mvn spotless:apply` |
| Compilation error | Check Java 11 compatibility |
| Test failure | Check mocks, Jackson annotations |

### Rust
| Error | Fix |
|-------|-----|
| `cargo fmt` fails | `cd cli && cargo fmt` |
| Clippy warnings | Fix the warning or add `#[allow(...)]` with justification |
| Test failure | Check assertions, mock responses |

### n8n
| Error | Fix |
|-------|-----|
| ESLint errors | `cd n8n-nodes-metadata && npm run lint:fix` |
| Build error | Rebuild TypeScript SDK first: `cd typescript && npm run build` |

## After Fixing

1. Run `make lint && make test-all` locally
2. Commit with descriptive message
3. Push and verify CI passes
