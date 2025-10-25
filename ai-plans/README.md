# AI Plans - Code Coverage Improvement

This folder contains detailed plans for increasing the Audible project's code coverage from 21% to near 100%.

## 📁 Plan Files Overview

### 🎯 [MASTER_PLAN.md](./MASTER_PLAN.md)
**The main project plan** with overview of all phases, strategy, and milestones.

**Contents:**
- Current coverage status of all modules
- Overall strategy (3 phases)
- Test infrastructure design
- Milestones and acceptance criteria
- Git workflow and branch strategy
- Dynamic `fail_under` threshold updates
- Risks and mitigation
- Quality assurance

**Target Audience:** Project managers, developers (overview)

---

### 🚀 [PHASE_1_QUICK_WINS.md](./PHASE_1_QUICK_WINS.md)
**Quick Wins** - Simple modules with fast results

**Modules:**
- ✅ `exceptions.py` (46% → 100%)
- ✅ `localization.py` (23% → 95%)
- ✅ `_logging.py` (41% → 90%)

**Time Estimate:** 2-3 hours  
**Coverage Gain:** +25% (21% → ~46%)

**Features:**
- Complete test code examples
- Step-by-step instructions
- No complex dependencies

**Target Audience:** Developers (implementation)

---

### 💪 [PHASE_2_CORE.md](./PHASE_2_CORE.md)
**Core Functionality** - Central components with mock integration

**Modules:**
- ✅ `utils.py` (20% → 90%)
- ✅ `client.py` (31% → 85%)
- ✅ `auth.py` (21% → 80%)

**Time Estimate:** 5-7 hours  
**Coverage Gain:** +25% (~46% → ~71%)

**Features:**
- HTTP client testing (sync & async)
- Authentication flow
- Token management
- Extensive mocking required

**Target Audience:** Developers (implementation)

---

### 🔥 [PHASE_3_COMPLEX.md](./PHASE_3_COMPLEX.md)
**Complex Modules** - API integration and encryption

**Modules:**
- ✅ `aescipher.py` (19% → 85%)
- ✅ `metadata.py` (20% → 80%)
- ✅ `activation_bytes.py` (21% → 75%)
- ✅ `register.py` (13% → 75%)
- ✅ `login.py` (12% → 70%)

**Time Estimate:** 8-12 hours  
**Coverage Gain:** +15-20% (~71% → 85-90%)

**Features:**
- OAuth2 flow (very complex)
- CAPTCHA & 2FA handling
- AES encryption/decryption
- File operations
- Known limitations documented

**Target Audience:** Senior developers (implementation)

---

## 🎯 Overall Summary

### Coverage Progression

| Phase | Modules | Start | Target | Time |
|-------|---------|-------|--------|------|
| **Phase 1** | 3 simple | 21% | ~46% | 2-3h |
| **Phase 2** | 3 core | ~46% | ~71% | 5-7h |
| **Phase 3** | 5 complex | ~71% | 85-90% | 8-12h |
| **TOTAL** | 11 modules | **21%** | **85-90%** | **15-22h** |

### Priorities

1. **Quick Wins (Phase 1)** → Motivation & foundation
2. **Core Features (Phase 2)** → Business-critical functionality
3. **Complexity (Phase 3)** → Completeness & edge cases

---

## 🔄 Git Workflow

### Branch Strategy
```bash
# Create feature branch from master
git checkout master
git pull origin master
git checkout -b feat/coverage-improvement

# Work on tests...

# Commit after each module
git commit -m "test: add tests for <module> (XX% coverage)"

# Update threshold after each phase
python scripts/update_coverage_threshold.py
git commit -m "chore: update fail_under to XX% after Phase Y"

# Push regularly
git push origin feat/coverage-improvement

# Create PR after Phase 3
```

### Dynamic Threshold Updates

After each phase, automatically update `pyproject.toml`:

```bash
# Run coverage
uv run nox --session=coverage

# Update fail_under automatically
python scripts/update_coverage_threshold.py

# Commit
git add pyproject.toml
git commit -m "chore: update fail_under to XX% after Phase Y"
```

This ensures the CI/CD threshold grows with actual coverage.

---

## 🛠️ How to Use These Plans

### For Project Managers:
1. ✅ Read `MASTER_PLAN.md` for overview
2. ✅ Review milestones and timelines
3. ✅ Track progress using coverage metrics
4. ✅ Monitor risks

### For Developers:
1. ✅ Start with `PHASE_1_QUICK_WINS.md`
2. ✅ Follow implementation checklist
3. ✅ Copy-paste test code examples
4. ✅ Adapt to specific implementation
5. ✅ Run coverage after each phase
6. ✅ Update `fail_under` threshold
7. ✅ Move to next phase

### For Code Reviewers:
1. ✅ Check test quality against plan
2. ✅ Verify coverage targets reached
3. ✅ Review mock strategies
4. ✅ Validate edge cases

---

## 📊 Progress Tracking

### Checklist: Phase 1 ✅
- [ ] Test infrastructure set up
- [ ] `test_exceptions.py` implemented (100% coverage)
- [ ] `test_localization.py` implemented (95% coverage)
- [ ] `test_logging.py` implemented (90% coverage)
- [ ] Coverage report: ≥46%
- [ ] `fail_under` updated to 46

### Checklist: Phase 2 ⬜
- [ ] `test_utils.py` implemented (90% coverage)
- [ ] `test_client.py` implemented (85% coverage)
- [ ] `test_auth.py` implemented (80% coverage)
- [ ] pytest-asyncio configured
- [ ] Coverage report: ≥71%
- [ ] `fail_under` updated to 71

### Checklist: Phase 3 ⬜
- [ ] `test_aescipher.py` implemented (85% coverage)
- [ ] `test_metadata.py` implemented (80% coverage)
- [ ] `test_activation_bytes.py` implemented (75% coverage)
- [ ] `test_register.py` implemented (75% coverage)
- [ ] `test_login.py` implemented (70% coverage)
- [ ] Coverage report: ≥85%
- [ ] `fail_under` updated to 85

### Checklist: Finalization ⬜
- [ ] CI/CD configured
- [ ] Coverage badge added
- [ ] Test documentation created
- [ ] Code review completed
- [ ] Pre-commit hooks activated
- [ ] PR merged to master

---

## 🚀 Quick Start

```bash
# 1. Create feature branch
git checkout master
git checkout -b feat/coverage-improvement

# 2. Set up test infrastructure
mkdir -p tests/unit tests/integration tests/fixtures

# 3. Install dependencies (if needed)
uv add --group=tests pytest-asyncio

# 4. Start Phase 1
# Open PHASE_1_QUICK_WINS.md and begin with test_exceptions.py

# 5. Measure coverage after each phase
uv run nox --session=tests
uv run nox --session=coverage

# 6. Update threshold
python scripts/update_coverage_threshold.py

# 7. Commit changes
git add .
git commit -m "test: add tests for <module> (XX% coverage)"

# 8. Repeat for Phases 2 and 3
```

---

## 🔑 Language Requirements

### All Documentation and Code
- ✅ Plans written in **English**
- ✅ Code comments in **English**
- ✅ Test code in **English**
- ✅ Docstrings in **English**
- ✅ Variable names in **English**
- ✅ Commit messages in **English**

**Example:**
```python
def test_authenticator_refreshes_expired_tokens():
    """Test that authenticator automatically refreshes expired tokens.
    
    Given an authenticator with an expired access token,
    When making an API request,
    Then the token should be refreshed automatically.
    """
    # Arrange
    expired_auth = create_expired_authenticator()
    
    # Act
    result = expired_auth.make_request("library")
    
    # Assert
    assert result.status_code == 200
    assert expired_auth.token_refresh_count == 1
```

---

## 📞 Support & Questions

### If You Encounter Issues:
1. Check the relevant phase file for details
2. Review `MASTER_PLAN.md` for context
3. Consult `CLAUDE.md` in project root for setup info

### Coverage Not Reached?
- Review test quality checklist
- Check for missing edge cases
- Verify mocks are correct
- Run `uv run nox --session=coverage` for details

### Tests Failing?
- Check dependencies installed
- Verify fixtures correct
- Review mock strategies
- Debug individual tests: `uv run pytest tests/unit/test_xyz.py -v`

---

## 📚 Additional Resources

- **Project Docs:** `../CLAUDE.md`, `../CONTRIBUTING.md`
- **pytest Docs:** https://docs.pytest.org/
- **Coverage.py:** https://coverage.readthedocs.io/
- **pytest-mock:** https://pytest-mock.readthedocs.io/

---

**Version:** 2.0 (English)  
**Created:** October 25, 2025  
**Author:** Claude (AI Assistant)  
**Project:** Audible Python Library  
**Branch:** `feat/coverage-improvement`
