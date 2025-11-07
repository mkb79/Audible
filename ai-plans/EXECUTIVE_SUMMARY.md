# Test Coverage Plan - Executive Summary

**Project Goal:** Increase code coverage from 21% to 85-90%

---

## 📊 Current Situation (Updated November 7, 2025)

| Metric                             | Value                                 |
| ---------------------------------- | ------------------------------------- |
| **Current Coverage**               | 74.23% (Phase 3 in progress)          |
| **Target Coverage**                | 85-90%                                |
| **Number of Test Files**           | 19 in tests/unit/ + 3 fixture files   |
| **Tests Passing**                  | 299 passed, 61 skipped                |
| **Critical Modules Without Tests** | 3 (metadata, activation_bytes, login) |

**Progress:** ✅ Phase 2 complete (74% achieved, target was 71%). Phase 3 in progress with aescipher (82%) and register (100%) complete. Major test refactoring with pytest-httpx completed. Fixtures organized in tests/fixtures/. Next: metadata, activation_bytes, login modules.

---

## 🎯 Solution: 3-Phase Plan

### Phase 1: Quick Wins ✅ COMPLETED

**Goal:** 21% → ~46% Coverage (achieved 50%)
**Modules:** exceptions, localization, logging, utils (partial), client helpers (partial)
**Strategy:** Simple modules first for quick wins
**Status (November 6, 2025):** ✅ Complete. All Phase 1 tests implemented and passing. Master branch merged bringing additional test infrastructure (crypto/json providers). Test structure unified under tests/unit/. Ready for Phase 2.

### Phase 2: Core Functionality ✅ COMPLETED

**Goal:** ~46% → ~71% Coverage (achieved 74%)
**Modules:** utils, client, auth
**Strategy:** Secure business-critical components
**Status (November 7, 2025):** ✅ Complete. Client (90%), auth (71%), utils (92%) all exceed targets. Comprehensive test refactoring with pytest-httpx completed.

### Phase 3: Complex Modules (🔄 IN PROGRESS)

**Goal:** ~71% → 85-90% Coverage
**Modules:** aescipher (✅ 82%), register (✅ 100%), metadata (⬜ 20%), activation_bytes (⬜ 21%), login (⬜ 14%)
**Strategy:** Completeness with realistic targets
**Status (November 7, 2025):** 🔄 In progress. aescipher and register complete. Remaining: metadata, activation_bytes, login.

---

## 📈 Expected Results

### Coverage Progression

```
50% (Current) ──→ 71% (Phase 2 target) ──→ 85-90% (Phase 3)
      ↑                  ↑                     ↑
    Now         Core Features          Completeness
```

### Module Coverage Targets

| Module                | Current              | Target   | Status |
| --------------------- | -------------------- | -------- | ------ |
| `__init__.py`         | 100% ✅              | 100%     | ✅     |
| `_types.py`           | 100% ✅              | 100%     | ✅     |
| `exceptions.py`       | 100% ✅ (↑ from 46%) | **100%** | ✅     |
| `localization.py`     | 99% ✅ (↑ from 23%)  | **95%**  | ✅     |
| `_logging.py`         | 100% ✅ (↑ from 41%) | **90%**  | ✅     |
| `utils.py`            | 92% ✅ (↑ from 88%)  | **90%**  | ✅     |
| `client.py`           | 90% ✅ (↑ from 42%)  | **85%**  | ✅     |
| `auth.py`             | 71% ✅ (↑ from 21%)  | **80%**  | 🔄     |
| `aescipher.py`        | 82% ✅ (↑ from 19%)  | **85%**  | 🔄     |
| `register.py`         | 100% ✅ (↑ from 13%) | **75%**  | ✅     |
| `metadata.py`         | 20% ⬜               | **80%**  | ⬜     |
| `activation_bytes.py` | 21% ⬜               | **75%**  | ⬜     |
| `login.py`            | 14% ⬜               | **70%**  | ⬜     |

---

## ⏱️ Timeline

| Phase                | Duration   | Cumulative |
| -------------------- | ---------- | ---------- |
| Setup & Planning     | 1h         | 1h         |
| **Phase 1**          | 2-3h       | 3-4h       |
| **Phase 2**          | 5-7h       | 8-11h      |
| **Phase 3**          | 8-12h      | 16-23h     |
| Integration & Polish | 2-3h       | 18-26h     |
| **TOTAL**            | **18-26h** | -          |

**Recommendation:** Distribute 1-2 hours per day over 2-3 weeks

---

## 🔄 Git Workflow

### Branch Strategy

- **Base:** `master`
- **Feature Branch:** `feat/coverage-improvement`
- **All commits** in feature branch
- **Merge to master** after Phase 3

### Dynamic Threshold Updates

After each phase, `pyproject.toml` is automatically updated:

```toml
[tool.coverage.report]
fail_under = 10  # Start

# After Phase 1
fail_under = 50  # actual Phase 1 coverage (target ≥46)

# After Phase 2
fail_under = 71  # +25 points

# After Phase 3
fail_under = 85  # +14 points
```

### Automation Script

```bash
# Run after each phase
python ai-plans/scripts/update_coverage_threshold.py

# Automatically updates pyproject.toml
# Commit with:
git commit -m "chore: update fail_under to XX% after Phase Y"
```

---

## 🛠️ Required Resources

### Tools (already present)

- ✅ pytest
- ✅ pytest-mock
- ✅ coverage

### Additional Dependencies

- ➕ pytest-asyncio (for async tests)
- ➕ pytest-httpx (optional, for HTTP mocking)

### Test Structure

```
tests/
├── unit/              # Unit tests per module
│   ├── test_exceptions.py
│   ├── test_localization.py
│   ├── test_logging.py
│   ├── test_utils.py
│   ├── test_client.py
│   ├── test_auth.py
│   ├── test_aescipher.py
│   ├── test_metadata.py
│   ├── test_activation_bytes.py
│   ├── test_register.py
│   └── test_login.py
├── integration/       # Integration tests
├── fixtures/          # Test data
├── conftest.py        # Shared fixtures
└── scripts/
    └── update_coverage_threshold.py
```

---

## ✅ Success Criteria

### Minimum (Must-Have)

- ✅ Overall coverage ≥85%
- ✅ All critical paths tested
- ✅ CI/CD pipeline works
- ✅ No failing tests
- ✅ `fail_under` reflects actual coverage

### Desired (Should-Have)

- ✅ Coverage ≥90%
- ✅ Integration tests present
- ✅ Edge cases covered
- ✅ Test documentation complete

### Stretch (Nice-to-Have)

- ✅ Coverage ≥95%
- ✅ Property-based testing
- ✅ Mutation testing
- ✅ Performance benchmarks

---

## ⚠️ Risks & Challenges

### High Complexity

- **login.py:** OAuth2 flow with CAPTCHA & 2FA
- **Mitigation:** Extensive mocking, realistic target 70%

### Async Testing

- **client.py:** Sync and async clients
- **Mitigation:** pytest-asyncio, separate test classes

### Encryption

- **aescipher.py:** Cryptography tests
- **Mitigation:** Focus on functionality, not security audit

### Interactive Components

- **login.py:** Browser, user input
- **Mitigation:** Mock instead of real browser integration

---

## 🔑 Language Requirements

### All Code and Documentation

- ✅ Plans in **English**
- ✅ Test code in **English**
- ✅ Docstrings in **English**
- ✅ Comments in **English**
- ✅ Variable names in **English**
- ✅ Commit messages in **English**

**Example:**

```python
def test_client_handles_expired_token_with_auto_refresh():
    """Test that client automatically refreshes expired access tokens.

    Scenario:
        Given a client with an expired access token
        When making an API request
        Then the token should be automatically refreshed
        And the request should succeed
    """
    # Arrange
    mock_auth = create_mock_authenticator(token_expired=True)
    client = Client(auth=mock_auth)

    # Act
    response = client.get("library")

    # Assert
    assert response.status_code == 200
    assert mock_auth.refresh_called
```

---

## 🚀 Next Steps

### Immediately

1. ✅ Review plan documents
2. ✅ Create feature branch: `git checkout -b feat/coverage-improvement`
3. ✅ Set up test infrastructure
4. ✅ Start with Phase 1

### This Week

1. ⏳ Complete Phase 1 (tests merged; wrap-up tasks still open)
2. ✅ Raise overall coverage to ≥46% (currently 50%)
3. ✅ Update `fail_under` to 50 following Phase 1 completion
4. ⬜ Document lessons learned after closing Phase 1

### Next Week

1. ⬜ Start Phase 2 (Core modules)
2. ⬜ Implement client and auth test suites
3. ⬜ Lift coverage toward ~71%
4. ⬜ Update `fail_under` to 71 following Phase 2

### Week After

1. ⬜ Start Phase 3 (Complex modules)
2. ⬜ Finish login flow tests
3. ⬜ Push final coverage to ≥85%
4. ⬜ Update `fail_under` to 85
5. ⬜ Prepare PR for review

---

## 📚 Documentation

### For Details See:

- **`MASTER_PLAN.md`** - Complete project plan
- **`PHASE_1_QUICK_WINS.md`** - Detailed Phase 1 guide
- **`PHASE_2_CORE.md`** - Detailed Phase 2 guide
- **`PHASE_3_COMPLEX.md`** - Detailed Phase 3 guide
- **`README.md`** - How to use these plans

---

## 💡 Key Takeaways

1. **Systematic Approach:** 3 phases from simple to complex
2. **Realistic Goals:** 85-90% instead of 100% (due to interactive components)
3. **Quick Wins First:** Motivation through fast results
4. **Detailed Instructions:** Copy-paste-ready test code examples
5. **Pragmatic Strategy:** Focus on critical paths
6. **Dynamic Thresholds:** `fail_under` grows with actual coverage
7. **English Throughout:** All code, docs, and commits in English

---

**Status:** 🚧 Phase 1 in progress — 50% coverage after quick-win tests
**Created:** October 25, 2025
**Version:** 2.2 (English)
**Branch:** `feat/coverage-improvement`
