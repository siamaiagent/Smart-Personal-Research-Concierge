# Contributing to Smart Personal Research Concierge

## Code Style

- Follow PEP 8 Python style guide
- Maximum line length: 120 characters
- Use docstrings for all classes and public methods
- Add inline comments for complex logic

## Documentation

- All classes must have docstrings describing purpose, inputs, outputs
- Update README.md when adding new features
- Include examples in docstrings where helpful

## Dependencies

When adding new dependencies:
1. Add to `requirements.txt`
2. Document in README.md
3. Ensure compatibility with Python 3.10+

## Testing

Before committing:
1. Run `python src/main.py` to verify pipeline works
2. Check that all agents complete successfully
3. Verify no API keys are hardcoded in files

## Commit Messages

Use clear, descriptive commit messages:
- `feat: Add new feature`
- `fix: Fix bug in agent`
- `docs: Update README`
- `refactor: Improve code structure`