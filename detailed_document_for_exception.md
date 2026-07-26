# Exception Handling in Python — Complete Guide

A deep-dive reference covering Python's exception model, custom exceptions (with real code), production best practices, and an interview Q&A cheat sheet. Includes findings from external research (Real Python, Python's official PEPs, Programiz, and community write-ups) alongside a worked example from this project's own `app/exception.py`.

---

## 1. What Is an Exception?

An **exception** is an event, detected during execution, that disrupts the normal flow of a program's instructions. Python raises one whenever it hits an error it can't resolve on its own — dividing by zero, opening a missing file, indexing past the end of a list, etc.

Python distinguishes two categories of problems:

| Type | When it occurs | Example |
|---|---|---|
| **Syntax Error** | Parse time, before execution starts | `if x = 5:` (missing `==`) |
| **Exception** | Runtime, during execution | `1/0`, `int("abc")` |

Syntax errors must be fixed in the code itself; exceptions can be *anticipated and handled* at runtime with `try`/`except`.

---

## 2. The Exception Hierarchy

Every exception in Python inherits from `BaseException`. Knowing this tree is one of the most common interview checks.

```
BaseException
 ├── SystemExit
 ├── KeyboardInterrupt
 ├── GeneratorExit
 └── Exception
      ├── ArithmeticError
      │    ├── ZeroDivisionError
      │    ├── OverflowError
      │    └── FloatingPointError
      ├── LookupError
      │    ├── IndexError
      │    └── KeyError
      ├── ValueError
      ├── TypeError
      ├── AttributeError
      ├── NameError
      │    └── UnboundLocalError
      ├── OSError (aliases IOError, EnvironmentError)
      │    ├── FileNotFoundError
      │    ├── PermissionError
      │    └── ConnectionError
      ├── ImportError
      │    └── ModuleNotFoundError
      ├── StopIteration
      ├── RuntimeError
      │    ├── RecursionError
      │    └── NotImplementedError
      ├── UnicodeError
      └── ExceptionGroup   (Python 3.11+, see §9)
```

**Interview point:** Always catch `Exception`, never `BaseException`, in application code. `BaseException` includes `SystemExit` and `KeyboardInterrupt` — catching those silently breaks `Ctrl+C` and `sys.exit()`. This is confirmed by Real Python's exception-handling best-practices guide and is the #1 rule cited across every source consulted.

---

## 3. Basic try/except/else/finally

```python
def divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError as e:
        print(f"Cannot divide by zero: {e}")
        return None
    else:
        # runs ONLY if no exception was raised in try
        print("Division succeeded")
        return result
    finally:
        # ALWAYS runs — exception or not, return or not
        print("Cleanup: divide() is done")

divide(10, 2)
divide(10, 0)
```

### Execution order rules (frequently asked)

1. `try` block runs.
2. If an exception occurs → the matching `except` runs → then `finally`.
3. If no exception occurs → `else` runs → then `finally`.
4. `finally` **always** runs, even if `try`/`except` has a `return`, `break`, or `continue`.
5. If `finally` itself has a `return`, it **overrides** any pending return/exception from `try`/`except` — a classic interview gotcha:

```python
def weird():
    try:
        return 1
    finally:
        return 2   # this wins — weird() returns 2, the original return is discarded

print(weird())  # 2
```

---

## 4. Catching Multiple Exceptions

```python
try:
    val = int(input("Enter a number: "))
    result = 100 / val
except (ValueError, ZeroDivisionError) as e:
    print(f"Invalid input or division error: {e}")
```

Order matters — Python checks `except` clauses **top to bottom** and uses the first match. Since exceptions form a class hierarchy, a subclass must be listed **before** its parent:

```python
try:
    risky()
except FileNotFoundError:      # subclass — must come first
    print("File missing")
except OSError:                # parent — catches everything else OS-related
    print("Some other OS error")
```

Reversing the order makes the specific branch unreachable dead code — some linters and `mypy` flag this.

---

## 5. `raise` — Raising Exceptions Manually

```python
def set_age(age):
    if age < 0:
        raise ValueError("Age cannot be negative")
    return age
```

### Re-raising inside an except block

```python
try:
    process()
except ValueError as e:
    log.error("Failed to process")
    raise   # re-raises the SAME exception with the ORIGINAL traceback
```

`raise` alone (no argument) inside an `except` re-raises the currently-handled exception, preserving its original traceback — preferred over `raise e`, which resets the traceback to point at that line and hides where the error actually happened. Real Python's guide to `raise` calls this out explicitly as a common mistake.

### Exception chaining: `raise ... from ...`

```python
try:
    conn = connect_to_db()
except ConnectionError as e:
    raise RuntimeError("Service unavailable") from e
```

This sets `__cause__` and prints both tracebacks joined by:
```
The above exception was the direct cause of the following exception:
```

If you raise a new exception inside an `except` block **without** `from`, Python still implicitly chains it via `__context__`, printing:
```
During handling of the above exception, another exception occurred:
```

Use `raise NewError(...) from None` to **suppress** chaining entirely and show a single clean traceback — common in CLI tools where internal plumbing errors shouldn't leak to the end user.

---

## 6. Custom Exceptions — Deep Dive

### 6.1 Why create custom exceptions?

External research (Real Python, Programiz, and multiple engineering blogs) converges on the same reasoning:

- **Precision**: `except InsufficientFundsError` is far more debuggable than `except ValueError`.
- **Domain-specific data**: custom attributes (error codes, HTTP status, offending record ID) travel with the exception object instead of being buried in a string.
- **Layered architecture**: callers can distinguish *your* application's errors from library/builtin errors and react differently.
- **Consistent formatting/logging** across a codebase — exactly what this project's `app/exception.py` does.

> **Best practice (Real Python / Programiz):** Before writing a custom exception, check whether a built-in one already fits (`ValueError`, `TypeError`, `LookupError`, etc.). Custom exceptions are for genuinely domain-specific failure modes, not a replacement for built-ins.

> **Organization tip (Programiz / standard library convention):** For any non-trivial project, keep all custom exceptions in one dedicated module — `exceptions.py` or `errors.py` — the same way `requests`, `django`, and `boto3` do. This project already follows that convention with `app/exception.py`.

### 6.2 Minimal custom exception

```python
class InsufficientFundsError(Exception):
    """Raised when a withdrawal exceeds the available balance."""
    pass

def withdraw(balance, amount):
    if amount > balance:
        raise InsufficientFundsError(f"Cannot withdraw {amount}, balance is {balance}")
    return balance - amount

withdraw(100, 500)
```

```
InsufficientFundsError: Cannot withdraw 500, balance is 100
```

Always inherit from `Exception` (or a more specific built-in) — **never** from `BaseException` directly, for the `Ctrl+C`/`SystemExit` reason explained in §2.

### 6.3 Custom exception with extra attributes

```python
class InsufficientFundsError(Exception):
    def __init__(self, balance, amount):
        self.balance = balance
        self.amount = amount
        self.shortfall = amount - balance
        message = f"Attempted to withdraw {amount}, but balance is only {balance} (short by {self.shortfall})"
        super().__init__(message)   # sets self.args and str(exception)

try:
    withdraw_amount = 500
    if withdraw_amount > 100:
        raise InsufficientFundsError(balance=100, amount=withdraw_amount)
except InsufficientFundsError as e:
    print(e)                 # uses __str__ / message passed to super().__init__
    print(e.shortfall)       # 400 — structured data other code can act on
```

**Key mechanics:**
- `super().__init__(message)` populates `self.args = (message,)` and makes `str(e)` return `message` automatically — no need for a custom `__str__` unless you want different formatting.
- Custom attributes (`balance`, `amount`, `shortfall`) let calling code make *programmatic* decisions instead of parsing strings — e.g. `if e.shortfall > 1000: escalate()`.

### 6.4 Custom exception hierarchy (the pattern used by `requests`, `django`, `boto3`)

```python
class AppError(Exception):
    """Base class for all application-specific exceptions."""

class ValidationError(AppError):
    """Raised when input data fails validation."""

class DatabaseError(AppError):
    """Base class for database-related errors."""

class RecordNotFoundError(DatabaseError):
    """Raised when a requested record doesn't exist."""

class DuplicateRecordError(DatabaseError):
    """Raised when a unique constraint would be violated."""
```

This lets calling code handle errors at whatever granularity it needs:

```python
try:
    save_user(data)
except RecordNotFoundError:
    return 404
except DuplicateRecordError:
    return 409
except DatabaseError:
    return 500       # catches any other DB error not specifically handled
except AppError:
    return 400        # catch-all for any app-defined error
```

**Interview point:** This mirrors `requests.exceptions` (`RequestException` → `ConnectionError`, `Timeout`, `HTTPError`, ...). Interviewers frequently ask you to *design* such a hierarchy live for a hypothetical system (payments, ML pipeline, order processing) — practice sketching one on a whiteboard.

### 6.5 Worked example: this project's `CustomException` (`app/exception.py`)

```python
import sys

def error_message_detail(error, error_detail: sys) -> str:
    _, _, exc_tb = error_detail.exc_info()
    file_name = exc_tb.tb_frame.f_code.co_filename
    error_message = f"Error occurred in script: [{file_name}] line number: [{exc_tb.tb_lineno}] error message: [{str(error)}]"
    return error_message


class CustomException(Exception):
    def __init__(self, error_message, error_detail: sys):
        super().__init__(error_message)
        self.error_message = error_message_detail(error_message, error_detail=error_detail)

    def __str__(self):
        return self.error_message
```

This is the pattern popularized in many ML/DS project templates (Krish Naik-style end-to-end pipelines). Breakdown:

- `sys.exc_info()` returns a 3-tuple `(exc_type, exc_value, exc_traceback)` describing the exception currently being handled. Only the traceback (`exc_tb`) is used here.
- `exc_tb.tb_frame.f_code.co_filename` walks the traceback object to the source filename where the error occurred.
- `exc_tb.tb_lineno` gives the exact line number.
- `__str__` is overridden (instead of relying on `super().__init__(message)` alone) because the class wants `print(e)`/`str(e)` to show the *enriched* message (file + line + original error), not the raw message passed in.

**Typical usage:**

```python
import sys
from app.exception import CustomException

try:
    a = 1 / 0
except Exception as e:
    raise CustomException(e, sys) from e
```

**Things worth flagging (and likely interview probes):**

1. **The type hint `error_detail: sys` is technically imprecise** — `sys` is a module, not a type, so the annotation isn't enforceable and doesn't reflect the real type (`types.ModuleType`). Python doesn't check this at runtime, so the code works, but it's a common style looseness in these tutorial-derived templates.
2. **`str(e)` and `e.args[0]` diverge.** `super().__init__(error_message)` stores the *raw* exception object as `args[0]`, while `self.error_message` (returned by the overridden `__str__`) holds the *enriched* string. This is intentional here, but it's exactly the kind of subtlety interviewers ask you to spot: "what does `e.args` contain vs. what does `print(e)` show?"
3. **Passing the `sys` module itself** (rather than pre-calling `sys.exc_info()`) is a minor dependency-injection choice — it lets `error_message_detail` decide when to call `.exc_info()`, rather than the caller computing it early and risking a stale/empty result if called outside the `except` block.

### 6.6 Custom exceptions with error codes (production/API pattern)

```python
class AppError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code

class PaymentDeclinedError(AppError):
    def __init__(self, message="Payment was declined", code="PAY_001"):
        super().__init__(message, code)

try:
    raise PaymentDeclinedError()
except AppError as e:
    print(f"[{e.code}] {e}")   # [PAY_001] Payment was declined
```

Useful for API error responses, structured logging/monitoring dashboards, or mapping application errors to HTTP status codes.

---

## 7. Context Managers & Exceptions (`with`)

```python
class ManagedResource:
    def __enter__(self):
        print("Acquiring resource")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Releasing resource")
        if exc_type is ValueError:
            print("Suppressing ValueError")
            return True   # True suppresses the exception; False/None propagates it
        return False

with ManagedResource() as r:
    raise ValueError("boom")

print("Program continues")   # reached, because __exit__ suppressed it
```

**Interview point:** `__exit__` receiving `(None, None, None)` means no exception occurred. Returning `True` from `__exit__` swallows the exception — a common source of silent bugs when done unintentionally.

`contextlib` shortcuts:
```python
from contextlib import contextmanager, suppress

@contextmanager
def managed_resource():
    print("acquire")
    try:
        yield
    finally:
        print("release")

with suppress(FileNotFoundError):
    open("missing.txt")   # no exception raised, no crash
```

---

## 8. Logging Exceptions Properly

A point every production-focused source (Real Python, DEV Community best-practices write-ups) emphasizes: log the **full traceback**, not just `str(e)`.

```python
import logging
logger = logging.getLogger(__name__)

try:
    risky()
except Exception:
    logger.exception("risky() failed")   # automatically includes the full traceback
```

`logger.exception(...)` is equivalent to `logger.error(..., exc_info=True)` — always call it *inside* an `except` block so the active exception is captured. This project's own `app/logger.py` is the natural place to wire this in alongside `CustomException`.

---

## 9. Exception Groups & `except*` (Python 3.11+, PEP 654)

**PEP 654** ("Exception Groups and except*") was accepted by the Python Steering Council to solve a real gap: code that can raise *multiple, unrelated* exceptions concurrently (e.g. `asyncio.TaskGroup` running several tasks) previously had no clean way to propagate more than one at a time — you either picked one and discarded the rest, collected them manually as return values, or wrapped them awkwardly.

PEP 654 introduces:
- **`ExceptionGroup`** (and `BaseExceptionGroup`) — a built-in type that wraps a list of exceptions being propagated together, and can be nested.
- **`except*`** — new syntax that matches and unpacks specific exception types *out of* a group, potentially running more than once (once per matching subgroup), while any exceptions in the group that don't match remain and propagate onward.

```python
try:
    raise ExceptionGroup("multiple failures", [ValueError("bad value"), TypeError("bad type")])
except* ValueError as eg:
    print("Handled ValueErrors:", eg.exceptions)
except* TypeError as eg:
    print("Handled TypeErrors:", eg.exceptions)
```

Regular `except` (without the `*`) is unchanged and fully backward-compatible — existing code is unaffected until it opts into `except*`. For Python < 3.11, the `exceptiongroup` PyPI package backports `ExceptionGroup` and provides `exceptiongroup.catch()` as a stand-in for `except*`.

Worth mentioning if the role touches modern async/concurrent code — "what's new in Python's exception handling" is an increasingly common interview question as 3.11+ adoption grows.

---

## 10. Best Practices Checklist (cross-referenced from Real Python, Programiz, and community engineering guides)

1. **Never use a bare `except:`.** It catches `SystemExit`/`KeyboardInterrupt` too, and hides bugs silently.
   ```python
   # Bad
   try:
       risky()
   except:
       pass

   # Good
   try:
       risky()
   except Exception as e:
       logger.exception("risky() failed")
   ```

2. **Catch specific exceptions, not `Exception`**, except at a genuine top-level boundary (a web framework's global error handler, or `main()`).

3. **Prefer EAFP over LBYL** — Python's own idiom ("Easier to Ask Forgiveness than Permission" vs. "Look Before You Leap"):
   ```python
   # LBYL
   if key in d:
       value = d[key]
   else:
       value = default

   # EAFP (more Pythonic)
   try:
       value = d[key]
   except KeyError:
       value = default
   ```

4. **Use built-ins before inventing custom exceptions**; reserve custom types for genuinely domain-specific failures.

5. **Keep custom exceptions in one module** (`exceptions.py`/`errors.py`), matching this project's `app/exception.py`.

6. **Write descriptive, explicit messages** on every exception raised — the #1 cited debugging aid across sources.

7. **Always clean up resources in `finally` or, better, use `with`** for anything implementing `__enter__`/`__exit__` (files, locks, DB connections, sessions).

8. **Log the full traceback**, never just `str(e)` (§8).

9. **Preserve or explicitly chain tracebacks** — bare `raise` to re-raise, `raise X from e` to chain intentionally, `raise X from None` to suppress noise deliberately.

10. **Don't over-widen `try` blocks.** Wrap only the lines that can actually raise the exception you're handling, so you don't accidentally swallow unrelated errors.

11. **Keep custom exception objects lightweight/serializable** — avoid storing unpicklable objects (open file handles, live DB connections) as attributes if the exception might cross process/thread boundaries (`multiprocessing`, Celery, etc.).

12. **Document what a function can raise** — a `Raises:` section in the docstring, since Python has no compiler-enforced `throws` declaration.

---

## 11. Interview Q&A Cheat Sheet

**Q: Difference between `Exception` and `BaseException`?**
`BaseException` is the root of everything, including `SystemExit`/`KeyboardInterrupt`/`GeneratorExit`. `Exception` is the subclass meant for "normal" application errors. Subclass and catch `Exception`, not `BaseException`.

**Q: Difference between `except Exception as e: raise` and `except Exception as e: raise e`?**
`raise` alone re-raises with the *original* traceback intact. `raise e` resets the traceback to point at that line, losing the original stack context — worse for debugging.

**Q: What's the difference between `raise X from Y` and just `raise X`?**
`from Y` explicitly sets `__cause__` for chained context ("the above exception was the direct cause..."). Without it, Python still auto-chains implicitly via `__context__` when you raise inside an `except` block ("during handling of the above exception, another exception occurred").

**Q: When does `finally` NOT run?**
It practically always runs — even on `return`/`break`/`continue` inside try/except. It's skipped only on a hard process kill (`os._exit()`, a segfault, power loss) — a graceful `sys.exit()` still triggers it.

**Q: Can you catch multiple exception types in one block?**
Yes: `except (ValueError, TypeError) as e:`.

**Q: What happens if you raise an exception inside an `except` block?**
Python chains it automatically — the new exception's `__context__` points to the original, and both tracebacks print.

**Q: How do you design your own exception hierarchy?**
Subclass `Exception` for a base app error, then subclass that for specific error types (§6.4). Callers can catch broadly or narrowly as needed.

**Q: Difference between `LookupError`, `IndexError`, and `KeyError`?**
`LookupError` is the common parent; `IndexError` is for sequences (list/tuple) with an out-of-range index, `KeyError` is for mappings (dict) with a missing key.

**Q: Is `try/except` expensive in Python?**
Entering a `try` block is essentially free on the happy path (no exception raised) — CPython's exception handling has near-zero setup cost. *Raising/catching* an exception does have real overhead (stack unwinding, traceback construction), so avoid using exceptions for high-frequency control flow in hot loops.

**Q: What is `__traceback__`?**
Every exception instance carries a `.__traceback__` attribute holding its traceback object once raised — used internally by `raise`, `sys.exc_info()`, and the `traceback` module.

**Q: What are Exception Groups / `except*`, and why were they added?**
Introduced in Python 3.11 via PEP 654 to let code (notably `asyncio.TaskGroup`) propagate *multiple, unrelated* exceptions together instead of losing all but one. `except*` unpacks matching exception types out of an `ExceptionGroup`; unmatched ones keep propagating.

**Q: What's the difference between checked and unchecked exceptions (common cross-language question, e.g. vs. Java)?**
Python has **no checked exceptions** — nothing is enforced at compile time (no `throws` clause requirement). Every exception is effectively "unchecked"; documentation and discipline fill the gap the compiler would otherwise cover.

**Q: How would you design custom exceptions for a real project (e.g. an ML pipeline)?**
- A base `AppException`/`CustomException` at the root (this project already has one in `app/exception.py`).
- Enrich it with contextual metadata (file, line, pipeline stage) — exactly what `error_message_detail` does.
- Optionally subclass per pipeline stage: `DataIngestionException`, `DataValidationException`, `ModelTrainingException`, all inheriting the base — so a top-level runner can catch broadly while stage-specific code catches narrowly.

---

## Sources

External research consulted while building this document:

- [Exception Handling — Python Best Practices, Real Python](https://realpython.com/ref/best-practices/exception-handling/)
- [Python's `raise`: Effectively Raising Exceptions in Your Code, Real Python](https://realpython.com/python-raise-exception/)
- [How to Define Custom Exceptions in Python? (With Examples), Programiz](https://www.programiz.com/python-programming/user-defined-exception)
- [How to Create Custom Exceptions in Python, OneUptime](https://oneuptime.com/blog/post/2026-01-22-create-custom-exceptions-python/view)
- [Python Custom Exceptions: How to Create and Organize Them, Jacob Padilla](https://jacobpadilla.com/writing/custom-python-exceptions)
- [Best Practices for Implementing Exception Handling in Python, DEV Community](https://dev.to/kyotanakada/best-practices-for-implementing-exception-handling-in-python-1ni1)
- [PEP 654 – Exception Groups and except*, peps.python.org](https://peps.python.org/pep-0654/)
- [Accepting PEP 654 (Exception Groups and except*), Python.org Discussions](https://discuss.python.org/t/accepting-pep-654-exception-groups-and-except/10813)
- [Backport of PEP 654 (exceptiongroup), PyPI/GitHub](https://github.com/agronholm/exceptiongroup)
