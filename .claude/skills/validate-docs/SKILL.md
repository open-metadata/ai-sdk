---
name: validate-docs
description: Use when reviewing or validating documentation. Checks for clarity,
  completeness, broken links, undefined terms, and ensures beginners can follow
  guides without prior knowledge of the SDK.
---

# Validate Documentation

Reviews documentation for clarity, completeness, and beginner-friendliness. Ensures technical people with no prior knowledge of the SDK can succeed.

## Usage
```
/validate-docs [path]
```

If no path provided, validates all docs in `docs/`.

## Validation Checklist

### 1. Prerequisites & Setup (Critical)

- [ ] **Environment variables are explicit**: Any `from_env()` usage must be preceded by showing which env vars to set
- [ ] **Prerequisites section exists**: Each guide explains what the user needs before starting
- [ ] **Credentials explained**: How to get `METADATA_HOST` and `METADATA_TOKEN` is documented
- [ ] **No assumed knowledge**: Don't assume user knows what "bot JWT token", "Dynamic Agent", etc. means

### 2. Code Examples

- [ ] **Examples are copy-pasteable**: User can run examples with minimal modification
- [ ] **Placeholder values are obvious**: Use `"https://your-org.getcollate.io"` not `"https://metadata.example.com"`
- [ ] **Required vs optional is clear**: Distinguish required parameters from optional ones
- [ ] **Output shown when helpful**: Show what the user should expect to see

### 3. Links & References

- [ ] **No broken links**: All `../` relative paths point to existing files
- [ ] **No dead external links**: External URLs should be valid (or removed)
- [ ] **Cross-references work**: Links between docs files are correct

### 4. Terminology

- [ ] **Terms are defined before use**: Don't use jargon without explaining it
- [ ] **Consistent naming**: Use the same terms throughout (OpenMetadata/Collate, not "Metadata server")

### 5. Error Handling

- [ ] **Troubleshooting section exists**: Common errors and their solutions
- [ ] **Error messages explained**: What each error means and how to fix it

### 6. Structure

- [ ] **Logical flow**: Prerequisites > Installation > Quick Start > Details
- [ ] **Progressive complexity**: Simple examples before complex ones
- [ ] **Scannable**: Headers, tables, and code blocks break up text

## Validation Commands

Run these to check docs:

```bash
# Check for broken relative links
cd docs && for f in *.md; do grep -o '\[.*\]([^)]*\.md)' "$f" | while read link; do
  target=$(echo "$link" | sed 's/.*(\([^)]*\))/\1/')
  [ ! -f "$target" ] && echo "$f: broken link to $target"
done; done

# Check for undefined env var usage
grep -r "from_env()" docs/ --include="*.md" -B5 | grep -v "METADATA_HOST\|METADATA_TOKEN\|export"

# Check for placeholder URLs that should be more explicit
grep -r "example\.com\|your-server\|your-instance" docs/ --include="*.md"
```

## Common Issues to Fix

| Issue | Bad | Good |
|-------|-----|------|
| Unexplained env vars | `config = MetadataConfig.from_env()` | Show `export METADATA_HOST=...` first |
| Vague host URL | `https://metadata.example.com` | `https://your-org.getcollate.io` |
| Undefined terms | "Use your bot JWT token" | "Use your bot's JWT token (from Settings > Bots)" |
| Missing prereqs | Jump straight to code | Start with "Prerequisites" section |
| Broken link | `[Examples](../examples/)` | Remove if folder doesn't exist |

## Output Format

After validation, report:

```
## Documentation Validation Report

### Files Checked
- docs/README.md
- docs/quickstart.md
- ...

### Issues Found

#### Critical (must fix)
1. **docs/README.md:15** - Uses `from_env()` without showing which env vars to set
2. **docs/quickstart.md:42** - Links to non-existent `../examples/` folder

#### Warnings (should fix)
1. **docs/langchain.md:8** - No Prerequisites section
2. **docs/async.md:23** - Uses "Metadata server" instead of "OpenMetadata/Collate"

### Passed Checks
- All code examples have explicit credentials
- Troubleshooting section exists in quickstart.md
- ...
```

## DO NOT

- Skip validation because docs "look fine"
- Leave broken links
- Assume the reader knows anything about OpenMetadata, Collate, or this SDK
- Use jargon without definitions
- Show `from_env()` without showing the env vars first
