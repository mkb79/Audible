# Master Plan: Achieving 100% Code Coverage

**Project Goal:** Increase code coverage from 21% to near 100%

**Created:** October 25, 2025
**Status:** Phase 1 in progress — combined coverage at 50%
**Branch:** `feat/coverage-improvement` ✅

---

## 🎯 Quick Reference

### Current Branch

```bash
git branch
# * feat/coverage-improvement  ← You are here!
```

### Coverage Target Progression

```
50% (Current) → 71% (Phase 2) → 85-90% (Phase 3)
```

### Dynamic Threshold Updates

After each phase, automatically update `pyproject.toml`:

```bash
# Run this after completing a phase:
python ai-plans/scripts/update_coverage_threshold.py

# Then commit:
git commit -m "chore: update fail_under to XX% after Phase Y"
```

---

## 📊 Current Status

| Module                | Current              | Target | Priority    |
| --------------------- | -------------------- | ------ | ----------- |
| `__init__.py`         | 100% ✅              | 100%   | -           |
| `_types.py`           | 100% ✅              | 100%   | -           |
| `exceptions.py`       | 100% ✅ (↑ from 46%) | 100%   | **PHASE 1** |
| `localization.py`     | 99% ✅ (↑ from 23%)  | 95%    | **PHASE 1** |
| `_logging.py`         | 100% ✅ (↑ from 41%) | 90%    | **PHASE 1** |
| `utils.py`            | 88% (partial)        | 90%    | **PHASE 2** |
| `client.py`           | 42% (partial)        | 85%    | **PHASE 2** |
| `auth.py`             | 21%                  | 80%    | **PHASE 2** |
| `aescipher.py`        | 19%                  | 85%    | **PHASE 3** |
| `metadata.py`         | 20%                  | 80%    | **PHASE 3** |
| `activation_bytes.py` | 21%                  | 75%    | **PHASE 3** |
| `register.py`         | 13%                  | 75%    | **PHASE 3** |
| `login.py`            | 12%                  | 70%    | **PHASE 3** |

**Overall Target: 85-90% Code Coverage**

### Progress Update (October 25, 2025)

- Quick-win test suites for exceptions, localization, and logging are implemented and now pass
  on Python 3.10–3.13.
- Targeted helpers in `audible.utils` and `audible.client` received tests to lift combined
  coverage to 50%.
- `fail_under` in `pyproject.toml` is now set to 50%.
- Upcoming tasks: commit the new test suites, and prepare for Phase 2
  planning.

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

### Branch Strategy ✅

- **Base Branch:** `master`
- **Feature Branch:** `feat/coverage-improvement` ← **Currently active**
- **All commits** happen in feature branch
- **Merge to master** after Phase 3 completion

**IMPORTANT:** All work is done in the `feat/coverage-improvement` branch that was created from `master`.

### Commit Strategy

```bash
# Phase 1 commits
git commit -m "test: add comprehensive tests for exceptions module (100% coverage)"
git commit -m "test: add tests for localization module (95% coverage)"
git commit -m "test: add tests for logging module (90% coverage)"
git commit -m "chore: update fail_under to 50% after Phase 1"

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

## 📈 Dynamic Coverage Threshold Updates ⚡

### Why Dynamic Thresholds?

The `fail_under` value in `pyproject.toml` ensures CI/CD fails if coverage drops. By updating it after each phase, we prevent coverage regression.

### Current Configuration

```toml
[tool.coverage.report]
fail_under = 10  # Current threshold
```

### Update Strategy

**After Phase 1 (Target: ≥46%):**

```toml
fail_under = 50  # Increased from 10 (actual Phase 1 coverage)
```

**After Phase 2 (Target: ~71%):**

```toml
fail_under = 71  # Increased from 46
```

**After Phase 3 (Target: ~85%):**

```toml
fail_under = 85  # Increased from 71
```

### Automation Script 🤖

**Location:** `ai-plans/scripts/update_coverage_threshold.py`

**How it works:**

1. Reads current coverage from coverage report
2. Rounds down to nearest integer
3. Updates `fail_under` in `pyproject.toml`
4. Prints confirmation

**Usage after each phase:**

```bash
# Step 1: Run tests and generate coverage
uv run nox --session=coverage

# Step 2: Update threshold automatically
python ai-plans/scripts/update_coverage_threshold.py

# Step 3: Commit the change
git add pyproject.toml
git commit -m "chore: update fail_under to XX% after Phase Y"
```

**Example output (Phase 1 actual numbers):**

```
📊 Current coverage: 50.02%
🎯 Setting fail_under to: 50%
✅ Updated fail_under to 50% in pyproject.toml

✨ Success! Don't forget to commit the change:
   git add pyproject.toml
   git commit -m "chore: update fail_under to 50%"
```

---

## 🛠️ Test Infrastructure

### Project Structure

```
ai-plans/                          # All plans and scripts
├── scripts/
│   └── update_coverage_threshold.py  # Threshold automation
├── MASTER_PLAN.md                 # This file
├── PHASE_1_QUICK_WINS.md
├── PHASE_2_CORE.md
├── PHASE_3_COMPLEX.md
├── README.md
└── EXECUTIVE_SUMMARY.md

tests/                             # Test directory (to be created)
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
└── fixtures/
    ├── sample_responses.json
    ├── test_credentials.json
    └── mock_data.py
```

### Required Tools & Dependencies

- ✅ pytest (already present)
- ✅ pytest-mock (already present)
- ✅ coverage (already present)
- ➕ pytest-httpx (for HTTP mocking)
- ➕ pytest-asyncio (for async tests)

---

## 📈 Milestones

### Milestone 1: Phase 1 Complete

- `exceptions.py`: 100% coverage
- `localization.py`: 95% coverage
- `_logging.py`: 90% coverage
- Overall coverage: ≥46% (currently 50%)
- `fail_under` updated to 50

### Milestone 2: Phase 2 Complete

- `utils.py`: 90% coverage
- `client.py`: 85% coverage
- `auth.py`: 80% coverage
- Overall coverage: ≥71%
- `fail_under` updated to 71

### Milestone 3: Phase 3 Complete

- All complex modules: ≥70% coverage
- Overall coverage: ≥85%
- `fail_under` updated to 85
- CI/CD pipeline green

### Milestone 4: Merge to Master

- Test documentation created
- CI/CD coverage reporting active
- Coverage badge in README
- PR reviewed and approved

---

## 🚀 Implementation Order

### Week 1: Quick Wins + Setup

1. ✅ Create feature branch `feat/coverage-improvement`
2. Set up test infrastructure (conftest.py)
3. Phase 1: Exceptions
4. Phase 1: Localization
5. Phase 1: Logging
6. Update `fail_under` to 50%
7. Add dependencies (pytest-asyncio)

### Week 2: Core Modules

8. Phase 2: Utils
9. Phase 2: Client (sync & async)
10. Phase 2: Auth
11. Update `fail_under` to 71%

### Week 3-4: Complex Modules

12. Phase 3: AESCipher
13. Phase 3: Metadata
14. Phase 3: Activation Bytes
15. Phase 3: Register
16. Phase 3: Login (OAuth flow)
17. Update `fail_under` to 85%

### Week 5: Integration & Polish

18. Integration tests
19. Cover edge cases
20. Configure CI/CD
21. Documentation
22. Code review & refactoring
23. Merge to master

---

## 📋 Acceptance Criteria

### Minimum Requirements (Must-Have)

- ✅ Overall coverage ≥85%
- ✅ All critical paths tested
- ✅ CI/CD pipeline works
- ✅ No failing tests
- ✅ `fail_under` reflects actual coverage
- ✅ All commits in `feat/coverage-improvement` branch

### Desired Goals (Should-Have)

- ✅ Coverage ≥90%
- ✅ Integration tests present
- ✅ Edge cases covered
- ✅ Test documentation complete

---

## 🔄 Language Requirements

### All Documentation & Code in English

- ✅ Plans written in **English**
- ✅ Test code in **English**
- ✅ Docstrings in **English**
- ✅ Comments in **English**
- ✅ Variable names in **English**
- ✅ Commit messages in **English**

---

## 📞 Next Steps

1. ✅ Branch created: `feat/coverage-improvement`
2. ✅ Plans documented
3. ✅ Automation script ready
4. **→ Ready to start Phase 1!**

Read `PHASE_1_QUICK_WINS.md` and begin implementation.

---

**Author:** Claude (AI Assistant)
**Project:** Audible Python Library
**Version:** 2.1 (Updated with correct paths and branch info)
**Branch:** `feat/coverage-improvement`
