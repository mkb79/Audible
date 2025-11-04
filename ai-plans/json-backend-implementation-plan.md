# JSON Backend Implementation Plan

**Feature**: Optional High-Performance JSON Backends (orjson/ujson/rapidjson)

**Goal**: Add pluggable JSON provider system following same clean architecture as crypto providers, providing 2-5x performance improvements for JSON operations.

**Status**: 🟡 In Progress

---

## Architecture Overview

### Provider Priority (Auto-Detection)
1. **orjson** - Rust-accelerated, fastest (4-5x), with smart fallback
2. **ujson** - C-based, very fast (2-3x), native indent=4 support
3. **rapidjson** - C++, very fast (2-3x), alternative to ujson
4. **stdlib** - Pure Python, always available

### Smart Fallback Strategy (Option A: Conservative)
- **Compact JSON** → orjson natively (maximum performance)
- **indent=2** → orjson natively (maximum performance)
- **indent=4** → orjson → ujson/rapidjson fallback (2-3x faster)
- **separators** → stdlib fallback (rare edge case)

### Module Structure
```
src/audible/json/
├── __init__.py                  # Public API
├── protocols.py                 # JSONProvider Protocol
├── registry.py                  # Auto-detection & selection
├── stdlib_provider.py           # Baseline (always available)
├── ujson_provider.py            # C-based provider
├── rapidjson_provider.py        # C++ provider
└── orjson_provider.py           # Rust provider with smart fallback
```

---

## Implementation Phases

### PHASE 1: Module Structure & Base Implementation ⏳

#### Step 1.1: Create Directory Structure
- [ ] Create `src/audible/json/` directory
- [ ] Create all module files

**Checkpoint**: Directory structure exists

---

#### Step 1.2: Implement protocols.py
- [ ] Define `JSONProvider` Protocol
- [ ] Include `dumps()`, `loads()`, `provider_name` methods
- [ ] Add comprehensive docstrings
- [ ] Test: Import works

**Checkpoint**: `from audible.json.protocols import JSONProvider` works

---

#### Step 1.3: Implement stdlib_provider.py
- [ ] Implement `StdlibProvider` class
- [ ] Support all parameters: indent, separators, ensure_ascii
- [ ] Add comprehensive docstrings
- [ ] Test: Standalone functionality

**Test Command**:
```bash
python -c "from audible.json.stdlib_provider import StdlibProvider; p = StdlibProvider(); print(p.dumps({'test': 'data'}, indent=4))"
```

**Checkpoint**: StdlibProvider works completely

---

#### Step 1.4: Implement ujson_provider.py
- [ ] Implement `UjsonProvider` class
- [ ] Add stdlib fallback for separators
- [ ] Handle UJSON_AVAILABLE flag
- [ ] Add comprehensive docstrings
- [ ] Test: With and without ujson installed

**Test Command**:
```bash
pip install ujson
python -c "from audible.json.ujson_provider import UjsonProvider; p = UjsonProvider(); print(p.dumps({'test': 'data'}, indent=4))"
```

**Checkpoint**: UjsonProvider with separators fallback works

---

#### Step 1.5: Implement rapidjson_provider.py
- [ ] Implement `RapidjsonProvider` class
- [ ] Add stdlib fallback for separators
- [ ] Handle RAPIDJSON_AVAILABLE flag
- [ ] Add comprehensive docstrings
- [ ] Test: With and without python-rapidjson installed

**Test Command**:
```bash
pip install python-rapidjson
python -c "from audible.json.rapidjson_provider import RapidjsonProvider; p = RapidjsonProvider(); print(p.dumps({'test': 'data'}, indent=4))"
```

**Checkpoint**: RapidjsonProvider works

---

#### Step 1.6: Implement orjson_provider.py
- [ ] Implement `OrjsonProvider` class
- [ ] **CRITICAL**: Implement smart fallback logic
- [ ] Lazy-load fallback provider chain (ujson → rapidjson → stdlib)
- [ ] Handle indent=4 fallback
- [ ] Handle separators fallback to stdlib
- [ ] Add comprehensive docstrings
- [ ] Test: All fallback scenarios

**Test Command**:
```bash
pip install orjson ujson
python -c "
from audible.json.orjson_provider import OrjsonProvider
p = OrjsonProvider()
print('Compact:', p.dumps({'test': 'data'}))
print('Indent=2:', p.dumps({'test': 'data'}, indent=2))
print('Indent=4:', p.dumps({'test': 'data'}, indent=4))
print('Separators:', p.dumps({'test': 'data'}, separators=(',', ':')))
"
```

**Checkpoint**: OrjsonProvider with complete fallback logic works

---

#### Step 1.7: Implement registry.py
- [ ] Implement `_validate_provider()`
- [ ] Implement `_auto_detect_provider_class()`
- [ ] Implement `_coerce_provider()`
- [ ] Implement `get_json_provider()`
- [ ] Implement `set_default_json_provider()`
- [ ] Test: Auto-detection with various installed libraries

**Test Command**:
```bash
python -c "
from audible.json.registry import get_json_provider, set_default_json_provider
from audible.json.stdlib_provider import StdlibProvider
p = get_json_provider()
print(f'Auto-detected: {p.provider_name}')
set_default_json_provider(StdlibProvider)
p = get_json_provider()
print(f'Default set to: {p.provider_name}')
set_default_json_provider(None)
"
```

**Checkpoint**: Registry with all functions works correctly

---

#### Step 1.8: Implement __init__.py
- [ ] Export all providers
- [ ] Export registry functions
- [ ] Add module docstring
- [ ] Test: Public API

**Test Command**:
```bash
python -c "
from audible.json import (
    get_json_provider,
    set_default_json_provider,
    JSONProvider,
    OrjsonProvider,
    UjsonProvider,
    RapidjsonProvider,
    StdlibProvider,
)
print('All imports successful')
p = get_json_provider()
print(f'Provider: {p.provider_name}')
"
```

**Checkpoint**: Complete public API works

---

### PHASE 2: Comprehensive Tests ⏳

#### Step 2.1: Create Test Files
- [ ] Create `tests/test_json.py`
- [ ] Create `tests/test_json_integration.py`
- [ ] Create `tests/test_json_fallback.py`

**Checkpoint**: Test file structure created

---

#### Step 2.2: Implement test_json.py
- [ ] `TestStdlibProvider` class with all tests
- [ ] `TestUjsonProvider` class with skip conditions
- [ ] `TestRapidjsonProvider` class with skip conditions
- [ ] `TestOrjsonProvider` class with fallback tests
- [ ] `TestRegistry` class with auto-detection tests

**Test Command**:
```bash
uv run pytest tests/test_json.py -v
```

**Checkpoint**: All provider unit tests pass

---

#### Step 2.3: Implement test_json_integration.py
- [ ] `TestRealWorldUsage` class
- [ ] Test auth file format (indent=4)
- [ ] Test compact API responses
- [ ] Test metadata with separators
- [ ] Test library export (from audible-cli pattern)

**Test Command**:
```bash
uv run pytest tests/test_json_integration.py -v
```

**Checkpoint**: Integration tests pass

---

#### Step 2.4: Implement test_json_fallback.py
- [ ] `TestOrjsonFallback` class
- [ ] Test fallback chain for indent=4
- [ ] Test fallback preserves correctness
- [ ] Test separators fallback to stdlib

**Test Command**:
```bash
uv run pytest tests/test_json_fallback.py -v
```

**Checkpoint**: Fallback tests successful

---

#### Step 2.5: Run Complete Test Suite
- [ ] Run all JSON tests
- [ ] Check coverage (target >95%)
- [ ] Verify all scenarios work

**Test Command**:
```bash
uv run pytest tests/test_json*.py -v --cov=src/audible/json --cov-report=html
```

**Checkpoint**: Complete test suite passes with >95% coverage

---

### PHASE 3: Integration into Codebase ⏳

#### Step 3.1: Migrate auth.py
- [ ] Add import for `get_json_provider`
- [ ] Create module-level provider cache
- [ ] Replace Line 428: `json.loads()` → `_json_provider.loads()`
- [ ] Replace Line 719: `json.dumps()` → `_json_provider.dumps()`
- [ ] Run tests

**Test Command**:
```bash
uv run pytest tests/test_auth.py -v
```

**Checkpoint**: auth.py tests pass after migration

---

#### Step 3.2: Migrate aescipher.py
- [ ] Add import for `get_json_provider`
- [ ] Create module-level provider cache
- [ ] Replace Line 351: `json.dumps()`
- [ ] Replace Line 377: `json.loads()`
- [ ] Replace Line 402: `json.loads()`
- [ ] Replace Line 467: `json.loads()`
- [ ] Run tests

**Test Command**:
```bash
uv run pytest tests/test_aescipher.py -v
```

**Checkpoint**: aescipher.py tests pass

---

#### Step 3.3: Migrate login.py
- [ ] Add import for `get_json_provider`
- [ ] Create module-level provider cache
- [ ] Replace Line 315: `json.dumps()`
- [ ] Run tests

**Test Command**:
```bash
uv run pytest tests/test_login.py -v
```

**Checkpoint**: login.py tests pass

---

#### Step 3.4: Verify metadata.py (No Changes)
- [ ] Verify Line 369 remains: `json.dumps(meta_dict, separators=(",", ":"))`
- [ ] Document: This is the only separators use case, stays with stdlib
- [ ] Run tests

**Test Command**:
```bash
uv run pytest tests/test_metadata.py -v
```

**Checkpoint**: metadata.py unchanged and working

---

#### Step 3.5: Run Full Test Suite
- [ ] Run all tests with nox
- [ ] Run specific module tests
- [ ] Verify no regressions

**Test Command**:
```bash
uv run nox --session=tests
uv run pytest tests/test_auth.py tests/test_aescipher.py tests/test_login.py tests/test_metadata.py -v
```

**Checkpoint**: Complete test suite passes

---

### PHASE 4: Dependencies & Configuration ⏳

#### Step 4.1: Update pyproject.toml
- [ ] Add `[project.optional-dependencies]` for JSON backends
- [ ] Add individual providers: orjson, ujson, rapidjson
- [ ] Add `json-fast` (orjson only)
- [ ] Add `json-full` (orjson + ujson) - **RECOMMENDED**
- [ ] Add `recommended` (json + crypto)
- [ ] Update `all` extra

**Checkpoint**: pyproject.toml updated

---

#### Step 4.2: Test Installation Scenarios
- [ ] Test `pip install -e ".[json-full]"` → should detect orjson
- [ ] Test without ujson → should still use orjson
- [ ] Test without any extras → should use stdlib
- [ ] Verify auto-detection works in all scenarios

**Test Commands**:
```bash
pip install -e ".[json-full]"
python -c "from audible.json import get_json_provider; print(get_json_provider().provider_name)"

pip uninstall ujson -y
python -c "from audible.json import get_json_provider; print(get_json_provider().provider_name)"

pip uninstall orjson ujson python-rapidjson -y
python -c "from audible.json import get_json_provider; print(get_json_provider().provider_name)"
```

**Checkpoint**: All installation scenarios work

---

### PHASE 5: Examples & Documentation ⏳

#### Step 5.1: Create test_json_autodetect.py
- [ ] Create `examples/test_json_autodetect.py`
- [ ] Test auto-detection
- [ ] Test compact JSON output
- [ ] Test indent=4 output
- [ ] Test roundtrip
- [ ] Add usage instructions in docstring

**Test Command**:
```bash
uv run python examples/test_json_autodetect.py
uv run --with ujson python examples/test_json_autodetect.py
uv run --with orjson python examples/test_json_autodetect.py
```

**Checkpoint**: Auto-detect example works

---

#### Step 5.2: Create test_json_explicit.py
- [ ] Create `examples/test_json_explicit.py`
- [ ] Test each provider explicitly
- [ ] Show availability checking
- [ ] Show performance comparison
- [ ] Add usage instructions

**Test Command**:
```bash
uv run --with orjson --with ujson python examples/test_json_explicit.py
```

**Checkpoint**: Explicit selection example works

---

#### Step 5.3: Update README.md
- [ ] Add "Optional High-Performance JSON Backends" section
- [ ] Document installation options
- [ ] Explain json-full vs json-fast
- [ ] Add performance comparison table
- [ ] Add usage examples

**Checkpoint**: README.md contains JSON backend docs

---

#### Step 5.4: Update CLAUDE.md
- [ ] Add "JSON Backend Architecture" section
- [ ] Document architecture components
- [ ] Explain smart fallback logic
- [ ] Document auto-detection priority
- [ ] Add usage patterns

**Checkpoint**: CLAUDE.md contains architecture docs

---

#### Step 5.5: Update CHANGELOG.md
- [ ] Add new "Added" section for JSON backends
- [ ] Document performance improvements
- [ ] List all providers
- [ ] Note backward compatibility
- [ ] Add installation instructions

**Checkpoint**: CHANGELOG.md updated

---

### PHASE 6: Final Testing & Validation ⏳

#### Step 6.1: Complete Test Suite
- [ ] Run `uv run nox --session=tests`
- [ ] Run `uv run nox --session=mypy`
- [ ] Run `uv run nox --session=pre-commit`
- [ ] Verify all checks pass

**Checkpoint**: All tests and checks pass

---

#### Step 6.2: Performance Benchmarks (Optional)
- [ ] Create benchmark script
- [ ] Compare stdlib vs orjson vs ujson
- [ ] Test compact JSON performance
- [ ] Test indent=4 performance
- [ ] Document results

**Checkpoint**: Benchmarks show expected improvements

---

#### Step 6.3: Documentation Review
- [ ] Review README.md completeness
- [ ] Review CLAUDE.md completeness
- [ ] Review CHANGELOG.md completeness
- [ ] Check all docstrings
- [ ] Verify examples work

**Checkpoint**: Documentation complete

---

### PHASE 7: Git Commit & Push ⏳

#### Step 7.1: Stage Files
- [ ] Stage `src/audible/json/`
- [ ] Stage test files
- [ ] Stage example files
- [ ] Stage `pyproject.toml`
- [ ] Stage documentation files

**Command**:
```bash
git status
git add src/audible/json/
git add tests/test_json*.py
git add examples/test_json_*.py
git add pyproject.toml
git add README.md
git add CLAUDE.md
git add CHANGELOG.md
```

**Checkpoint**: All files staged

---

#### Step 7.2: Create Commit
- [ ] Create conventional commit message
- [ ] Include comprehensive description
- [ ] List all changes
- [ ] Note performance improvements

**Command**:
```bash
git commit -m "feat: add optional high-performance JSON backends

Add pluggable JSON provider system with automatic backend selection for
improved performance. Follows same clean architecture pattern as crypto
providers.

Providers (auto-detection priority):
- orjson: 4-5x faster (Rust), smart fallback for indent=4
- ujson: 2-3x faster (C), native indent=4 support
- rapidjson: 2-3x faster (C++), alternative to ujson
- stdlib: baseline (always available)

Smart fallback logic:
- orjson handles compact JSON natively (maximum performance)
- Falls back to ujson/rapidjson for indent=4 (still 2-3x faster)
- Falls back to stdlib only for separators (rare edge case)

Installation:
- Recommended: pip install audible[json-full]
- Fast compact: pip install audible[json-fast]

Performance impact:
- Login operations: 4-5x faster with orjson
- Auth files: 2-3x faster with ujson fallback
- API operations: 4-5x faster with orjson
- Library exports (CLI): 2-3x faster with ujson

Changes:
- Add src/audible/json/ module with all providers
- Add comprehensive tests with >95% coverage
- Add examples for auto-detection and explicit selection
- Update auth.py, aescipher.py, login.py to use providers
- metadata.py unchanged (separators edge case stays stdlib)
- Update pyproject.toml with new optional dependencies
- Update README.md and CLAUDE.md with architecture docs
- Update CHANGELOG.md with feature description

Fully backward compatible - stdlib json remains fallback."
```

**Checkpoint**: Commit created

---

#### Step 7.3: Push to Remote
- [ ] Push branch to remote
- [ ] Verify push successful

**Command**:
```bash
git push -u origin feat/json-backend-providers
```

**Checkpoint**: Changes pushed to remote

---

### PHASE 8: PR Creation (Optional) ⏳

#### Step 8.1: Create Pull Request
- [ ] Create PR with comprehensive description
- [ ] Include performance metrics
- [ ] Add test plan checklist
- [ ] Request review

**Command**:
```bash
gh pr create --title "feat: add optional high-performance JSON backends" --body "..."
```

**Checkpoint**: PR created

---

## Why json-full is Recommended

### json-full (Recommended #1)
**Components**: orjson + ujson (~2MB total)

**Benefits**:
1. ✅ Maximum performance in all scenarios
2. ✅ No stdlib fallbacks (except separators edge case)
3. ✅ Best user experience - everything optimized
4. ✅ Minimal size - only ~2MB total
5. ✅ Future-proof - all formats covered

**Performance Matrix**:
- Compact JSON (API): orjson (4-5x)
- indent=2: orjson (4-5x)
- indent=4 (Auth): ujson (2-3x)
- separators (Metadata): stdlib (baseline, rare)

### json-fast (Alternative #2)
**Components**: orjson only

**Benefits**:
1. ✅ Smallest dependencies
2. ✅ Maximum performance for compact JSON
3. ✅ Good for API-heavy workloads

**Trade-offs**:
1. ❌ indent=4 falls back to stdlib (no acceleration)
2. ❌ ~17% of use cases not optimized (auth files)

---

## Progress Tracking

**Overall Progress**: 0/8 Phases Complete

- [ ] Phase 1: Module Structure (0/8 steps)
- [ ] Phase 2: Tests (0/5 steps)
- [ ] Phase 3: Integration (0/5 steps)
- [ ] Phase 4: Dependencies (0/2 steps)
- [ ] Phase 5: Documentation (0/5 steps)
- [ ] Phase 6: Validation (0/3 steps)
- [ ] Phase 7: Git (0/3 steps)
- [ ] Phase 8: PR (0/1 steps)

---

## Notes & Decisions

### Key Design Decisions
1. **Smart Fallback**: orjson auto-falls back to ujson/stdlib for unsupported features
2. **Conservative Approach**: Prefer correctness over absolute peak performance
3. **Lazy Loading**: Fallback providers loaded only when needed
4. **No Breaking Changes**: Fully backward compatible with stdlib json

### Integration Points
- `auth.py`: 2 locations (loads, dumps)
- `aescipher.py`: 4 locations (loads, dumps)
- `login.py`: 1 location (dumps)
- `metadata.py`: 0 changes (separators edge case stays stdlib)

### Performance Expectations
- **audible package**: 2-5x faster JSON operations
- **audible-cli**: 2-5x faster exports and API operations
- **Overall**: Noticeable improvement with json-full installed

---

**Last Updated**: 2025-11-04
**Status**: Ready to start implementation
