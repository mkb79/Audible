# Test Coverage Plan - Executive Summary

**Project Goal:** Increase code coverage from 21% to 85-90%

---

## 📊 Current Situation

| Metric | Value |
|--------|-------|
| **Current Coverage** | 21% |
| **Target Coverage** | 85-90% |
| **Number of Modules** | 15 |
| **Fully Tested** | 2 (13%) |
| **Critical Modules Without Tests** | 5 |

**Problem:** Only one test exists (`test_main.py`) that merely checks if the Client class exists.

---

## 🎯 Solution: 3-Phase Plan

### Phase 1: Quick Wins (2-3 hours)
**Goal:** 21% → ~46% Coverage  
**Modules:** exceptions, localization, logging  
**Strategy:** Simple modules first for quick wins

### Phase 2: Core Functionality (5-7 hours)
**Goal:** ~46% → ~71% Coverage  
**Modules:** utils, client, auth  
**Strategy:** Secure business-critical components

### Phase 3: Complex Modules (8-12 hours)
**Goal:** ~71% → 85-90% Coverage  
**Modules:** aescipher, metadata, activation_bytes, register, login  
**Strategy:** Completeness with realistic targets

---

## 📈 Expected Results

### Coverage Progression
```
21% (Start) ──→ 46% (Phase 1) ──→ 71% (Phase 2) ──→ 85-90% (Phase 3)
     ↑             ↑                 ↑                    ↑
   Now        Quick Wins        Core Features     Completeness
```

### Module Coverage Targets

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `__init__.py` | 100% ✅ | 100% | - |
| `_types.py` | 100% ✅ | 100% | - |
| `exceptions.py` | 46% | **100%** | P1 |
| `localization.py` | 23% | **95%** | P1 |
| `_logging.py` | 41% | **90%** | P1 |
| `utils.py` | 20% | **90%** | P2 |
| `client.py` | 31% | **85%** | P2 |
| `auth.py` | 21% | **80%** | P2 |
| `aescipher.py` | 19% | **85%** | P3 |
| `metadata.py` | 20% | **80%** | P3 |
| `activation_bytes.py` | 21% | **75%** | P3 |
| `register.py` | 13% | **75%** | P3 |
| `login.py` | 12% | **70%** | P3 |

---

## ⏱️ Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Setup & Planning | 1h | 1h |
| **Phase 1** | 2-3h | 3-4h |
| **Phase 2** | 5-7h | 8-11h |
| **Phase 3** | 8-12h | 16-23h |
| Integration & Polish | 2-3h | 18-26h |
| **TOTAL** | **18-26h** | - |

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
fail_under = 46  # +36 points

# After Phase 2
fail_under = 71  # +25 points

# After Phase 3
fail_under = 85  # +14 points
```

### Automation Script
```bash
# Run after each phase
python scripts/update_coverage_threshold.py

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
1. ✅ Complete Phase 1 (Quick Wins)
2. ✅ Increase coverage to ~46%
3. ✅ Update `fail_under` to 46
4. ✅ Document lessons learned

### Next Week
1. ✅ Start Phase 2 (Core)
2. ✅ Client & Auth tests
3. ✅ Increase coverage to ~71%
4. ✅ Update `fail_under` to 71

### Week After
1. ✅ Start Phase 3 (Complex)
2. ✅ Login flow tests
3. ✅ Final coverage ≥85%
4. ✅ Update `fail_under` to 85
5. ✅ Create PR for review

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

**Status:** ✅ Planning Complete - Ready for Implementation  
**Created:** October 25, 2025  
**Version:** 2.0 (English)  
**Branch:** `feat/coverage-improvement`
