# Master Plan: Achieving 100% Code Coverage

**Project Goal:** Increase code coverage from 21% to near 100%

**Created:** October 25, 2025  
**Status:** In Planning  
**Branch:** `feat/coverage-improvement`

---

## 📊 Current Status

| Module | Current Coverage | Target | Priority |
|--------|-----------------|--------|----------|
| `__init__.py` | 100% ✅ | 100% | - |
| `_types.py` | 100% ✅ | 100% | - |
| `exceptions.py` | 46% | 100% | **PHASE 1** |
| `localization.py` | 23% | 95% | **PHASE 1** |
| `_logging.py` | 41% | 90% | **PHASE 1** |
| `utils.py` | 20% | 90% | **PHASE 2** |
| `client.py` | 31% | 85% | **PHASE 2** |
| `auth.py` | 21% | 80% | **PHASE 2** |
| `aescipher.py` | 19% | 85% | **PHASE 3** |
| `metadata.py` | 20% | 80% | **PHASE 3** |
| `activation_bytes.py` | 21% | 75% | **PHASE 3** |
| `register.py` | 13% | 75% | **PHASE 3** |
| `login.py` | 12% | 70% | **PHASE 3** |

**Overall Target: 85-90% Code Coverage**

---

## 🎯 Strategy Overview

### Phase 1: Quick Wins (Target: +25% Coverage)
**Time Estimate:** 2-3 hours  
**Focus:** Simple modules with clear test cases
- ✅ Exceptions (46% → 100%)
- ✅ Localization (23% → 95%)
- ✅ Logging (41% → 90%)

**Expected Result:** Coverage increases from 21% to ~46%

### Phase 2: Core Functionality (Target: +25% Coverage)
**Time Estimate:** 5-7 hours  
**Focus:** Central components with mock integration
- ✅ Utils (20% → 90%)
- ✅ Client (31% → 85%)
- ✅ Auth (21% → 80%)

**Expected Result:** Coverage increases from ~46% to ~71%

### Phase 3: Complex Modules (Target: +15% Coverage)
**Time Estimate:** 8-12 hours  
**Focus:** API integration and encryption
- ✅ AESCipher (19% → 85%)
- ✅ Metadata (20% → 80%)
- ✅ Activation Bytes (21% → 75%)
- ✅ Register (13% → 75%)
- ✅ Login (12% → 70%)

**Expected Result:** Coverage reaches 85-90%

---

## 🔄 Git Workflow

### Branch Strategy
- **Base Branch:** `master`
- **Feature Branch:** `feat/coverage-improvement`
- **All commits** happen in feature branch
- **Merge to master** after Phase 3 completion

### Commit Strategy
```bash
# Phase 1 commits
git commit -m "test: add comprehensive tests for exceptions module (100% coverage)"
git commit -m "test: add tests for localization module (95% coverage)"
git commit -m "test: add tests for logging module (90% coverage)"
git commit -m "chore: update fail_under to 46% after Phase 1"

# Phase 2 commits
git commit -m "test: add tests for utils module (90% coverage)"
git commit -m "test: add comprehensive client tests (85% coverage)"
git commit -m "test: add auth module tests (80% coverage)"
git commit -m "chore: update fail_under to 71% after Phase 2"

# Phase 3 commits
git commit -m "test: add aescipher tests (85% coverage)"
git commit -m "test: add metadata tests (80% coverage)"
git commit -m "test: add activation_bytes tests (75% coverage)"
git commit -m "test: add register tests (75% coverage)"
git commit -m "test: add login tests (70% coverage)"
git commit -m "chore: update fail_under to 85% after Phase 3"
```

---

## 📈 Dynamic Coverage Threshold Updates

### Current Configuration
```toml
[tool.coverage.report]
fail_under = 10  # Current threshold
```

### Update Strategy

After each phase, update `pyproject.toml`:

**After Phase 1 (Target: 46%):**
```toml
fail_under = 46  # Increased from 10
```

**After Phase 2 (Target: 71%):**
```toml
fail_under = 71  # Increased from 46
```

**After Phase 3 (Target: 85%):**
```toml
fail_under = 85  # Increased from 71
```

### Automation Script
Create `scripts/update_coverage_threshold.py`:

```python
#!/usr/bin/env python3
"""Update coverage threshold in pyproject.toml based on actual coverage."""

import re
import subprocess
from pathlib import Path


def get_current_coverage() -> float:
    """Get current coverage percentage from coverage report."""
    result = subprocess.run(
        ["coverage", "report", "--precision=2"],
        capture_output=True,
        text=True
    )
    # Parse TOTAL line: TOTAL  1417   1042    408     16    21.23%
    for line in result.stdout.split("\n"):
        if line.startswith("TOTAL"):
            coverage_str = line.split()[-1].rstrip("%")
            return float(coverage_str)
    return 0.0


def update_fail_under(new_threshold: int) -> None:
    """Update fail_under in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    
    # Update fail_under value
    pattern = r'fail_under = \d+'
    replacement = f'fail_under = {new_threshold}'
    new_content = re.sub(pattern, replacement, content)
    
    pyproject_path.write_text(new_content)
    print(f"✅ Updated fail_under to {new_threshold}%")


def main():
    current = get_current_coverage()
    # Round down to nearest integer
    new_threshold = int(current)
    
    print(f"Current coverage: {current:.2f}%")
    print(f"Setting fail_under to: {new_threshold}%")
    
    update_fail_under(new_threshold)


if __name__ == "__main__":
    main()
```

Usage after each phase:
```bash
# Run tests and generate coverage
uv run nox --session=coverage

# Update threshold automatically
python scripts/update_coverage_threshold.py

# Commit the change
git add pyproject.toml
git commit -m "chore: update fail_under to XX% after Phase Y"
```

---

## 🛠️ Test Infrastructure

### New Test Structure
```
tests/
├── __init__.py
├── conftest.py                    # Fixtures and helpers
├── unit/
│   ├── test_exceptions.py         # Phase 1
│   ├── test_localization.py       # Phase 1
│   ├── test_logging.py            # Phase 1
│   ├── test_utils.py              # Phase 2
│   ├── test_client.py             # Phase 2
│   ├── test_auth.py               # Phase 2
│   ├── test_aescipher.py          # Phase 3
│   ├── test_metadata.py           # Phase 3
│   ├── test_activation_bytes.py   # Phase 3
│   ├── test_register.py           # Phase 3
│   └── test_login.py              # Phase 3
├── integration/
│   ├── test_auth_flow.py
│   └── test_api_client.py
├── fixtures/
│   ├── sample_responses.json
│   ├── test_credentials.json
│   └── mock_data.py
└── scripts/
    └── update_coverage_threshold.py
```

### Required Tools & Dependencies
- ✅ pytest (already present)
- ✅ pytest-mock (already present)
- ✅ coverage (already present)
- ➕ pytest-httpx (for HTTP mocking)
- ➕ pytest-asyncio (for async tests)
- ➕ freezegun (for time-based tests)

### Common Test Fixtures (conftest.py)
- Mock HTTP responses
- Sample credentials
- Locale templates
- Mock file system
- Logger capture
- Encrypted/decrypted test files

---

## 📈 Milestones

### Milestone 1: Phase 1 Complete
- **Criteria:**
  - `exceptions.py`: 100% coverage
  - `localization.py`: 95% coverage
  - `_logging.py`: 90% coverage
  - Overall coverage: ≥45%
  - `fail_under` updated to 46

### Milestone 2: Phase 2 Complete
- **Criteria:**
  - `utils.py`: 90% coverage
  - `client.py`: 85% coverage
  - `auth.py`: 80% coverage
  - Overall coverage: ≥70%
  - `fail_under` updated to 71

### Milestone 3: Phase 3 Complete
- **Criteria:**
  - All complex modules: ≥70% coverage
  - Overall coverage: ≥85%
  - `fail_under` updated to 85
  - CI/CD pipeline green

### Milestone 4: Maintenance & Documentation
- **Criteria:**
  - Test documentation created
  - CI/CD coverage reporting active
  - Coverage badge in README
  - PR ready for review

---

## 🚀 Implementation Order

### Week 1: Quick Wins + Setup
1. ✅ Create feature branch
2. ✅ Set up test infrastructure (conftest.py)
3. ✅ Phase 1: Exceptions
4. ✅ Phase 1: Localization
5. ✅ Phase 1: Logging
6. ✅ Update fail_under to 46%
7. ✅ Add dependencies (pytest-httpx, etc.)

### Week 2: Core Modules
8. ✅ Phase 2: Utils
9. ✅ Phase 2: Client (sync)
10. ✅ Phase 2: Client (async)
11. ✅ Phase 2: Auth (Basics)
12. ✅ Phase 2: Auth (Advanced)
13. ✅ Update fail_under to 71%

### Week 3-4: Complex Modules
14. ✅ Phase 3: AESCipher
15. ✅ Phase 3: Metadata
16. ✅ Phase 3: Activation Bytes
17. ✅ Phase 3: Register
18. ✅ Phase 3: Login (OAuth flow)
19. ✅ Update fail_under to 85%

### Week 5: Integration & Polish
20. ✅ Integration tests
21. ✅ Cover edge cases
22. ✅ Configure CI/CD
23. ✅ Documentation
24. ✅ Code review & refactoring
25. ✅ Merge to master

---

## 📋 Acceptance Criteria

### Minimum Requirements (Must-Have)
- ✅ Overall coverage ≥85%
- ✅ All critical paths tested
- ✅ CI/CD pipeline works
- ✅ No failing tests
- ✅ `fail_under` reflects actual coverage

### Desired Goals (Should-Have)
- ✅ Coverage ≥90%
- ✅ Integration tests present
- ✅ Edge cases covered
- ✅ Test documentation complete

### Stretch Goals (Nice-to-Have)
- ✅ Coverage ≥95%
- ✅ Property-based testing (hypothesis)
- ✅ Performance tests
- ✅ Mutation testing (mutmut)

---

## 🔍 Quality Assurance

### Coverage Monitoring
- Run coverage report after each phase
- Stop and analyze if coverage drops >2%
- All new features must include tests

### Code Review Checklist
- [ ] Tests follow AAA pattern (Arrange-Act-Assert)
- [ ] Fixtures are reused
- [ ] Mocks are minimal and precise
- [ ] Test names are descriptive
- [ ] Edge cases are covered
- [ ] Async tests use pytest-asyncio
- [ ] No flaky tests
- [ ] All test code in English
- [ ] All docstrings in English

### Performance Targets
- Total test runtime: <30 seconds
- Single test: <100ms (except integration)
- CI/CD pipeline: <5 minutes

---

## 📚 Resources & References

### Documentation
- [pytest Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Coverage.py Docs](https://coverage.readthedocs.io/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [pytest-httpx](https://colin-b.github.io/pytest_httpx/)

### Project-Specific Docs
- `CLAUDE.md` - Project setup and conventions
- `CONTRIBUTING.md` - Contribution guidelines
- Individual phase plans in this folder

---

## ⚠️ Risks & Mitigation

### Risk 1: OAuth Flow Complexity
**Probability:** High  
**Impact:** Medium  
**Mitigation:** Extensive mocking, incremental tests

### Risk 2: Async Test Complexity
**Probability:** Medium  
**Impact:** Medium  
**Mitigation:** Use pytest-asyncio, write sync tests first

### Risk 3: File Encryption Tests
**Probability:** Medium  
**Impact:** Low  
**Mitigation:** Test fixtures with known encrypted files

### Risk 4: Flaky HTTP Tests
**Probability:** Medium  
**Impact:** High  
**Mitigation:** No real HTTP calls, only mocks

---

## 📞 Next Steps

1. ✅ Review this master plan
2. ✅ Read `PHASE_1_QUICK_WINS.md`
3. ✅ Set up test infrastructure in `conftest.py`
4. ✅ Implement first tests
5. ✅ Measure and document coverage
6. ✅ Update `fail_under` after each phase

---

## 🔄 Language Requirements

### All Documentation
- ✅ Plans written in **English**
- ✅ Comments in **English**
- ✅ Commit messages in **English**

### All Code
- ✅ Test code in **English**
- ✅ Variable names in **English**
- ✅ Function names in **English**
- ✅ Docstrings in **English**
- ✅ Error messages in **English**

Example:
```python
def test_authenticator_refreshes_token_on_expiry():
    """Test that authenticator automatically refreshes expired tokens.
    
    Given an authenticator with an expired access token,
    When making an API request,
    Then the token should be refreshed automatically.
    """
    # Arrange
    mock_auth = Mock()
    mock_auth.access_token = "expired_token"
    
    # Act
    result = mock_auth.refresh_access_token()
    
    # Assert
    assert result is not None
```

---

**Author:** Claude (AI Assistant)  
**Project:** Audible Python Library  
**Version:** 2.0 (English)
