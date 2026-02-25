## Summary

<!-- Brief description of what this PR does -->

## Changes

<!-- List the main changes -->
-

## SDKs Affected

<!-- Check all that apply -->
- [ ] Python SDK
- [ ] TypeScript SDK
- [ ] Java SDK
- [ ] Rust CLI
- [ ] n8n Node
- [ ] Documentation
- [ ] CI/Build

## Checklist

### Required
- [ ] Code follows the project's style guidelines (`make lint` passes)
- [ ] All existing tests pass (`make test-all` passes)
- [ ] New code has appropriate test coverage
- [ ] Changes are consistent across all affected SDKs

### If Adding New Functionality
- [ ] Added to all relevant SDKs (not just one)
- [ ] Added unit tests for new code
- [ ] Updated type definitions where applicable

### If Fixing a Bug
- [ ] Added test that reproduces the bug
- [ ] Test now passes with the fix

### If Changing API Behavior
- [ ] Changes are backward compatible (or breaking change is documented)
- [ ] Updated any affected documentation

## Testing

<!-- Describe how you tested these changes -->

**Local testing:**
```bash
make lint      # ✅ Pass
make test-all  # ✅ Pass
```

**Integration testing:** (if applicable)
- [ ] Tested against real Metadata instance
- [ ] Streaming works correctly
- [ ] Error handling works as expected

## Additional Notes

<!-- Any additional context, screenshots, or information -->
