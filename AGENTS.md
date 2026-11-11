AGENTS.md: C++ and Python Coding Standards
🎯 Primary Directives

Prioritize Modern Language Features: Target at least C++20 for C++ code and Python 3.10+ for Python code. Use modern idioms (smart pointers, std::optional, std::variant, range-based loops in C++; type hints, match statements, dataclasses, pathlib, union types in Python) to write cleaner, safer, more expressive code.
Concise and Intentional Comments: Write comments only when they add real value. The code itself should be the primary documentation.
Code Clarity over Comments: If a section of code is difficult to comment clearly, it likely needs refactoring for simplicity. Good comments do not excuse unclear code.

📝 Commenting Guidelines
These rules apply to both languages. Language-specific syntax is noted where it matters.

Avoid Redundancy: Do not comment on trivial or obvious code (e.g., i++; // increment i or i += 1  # increment i). The code's intent should be clear from its structure and naming.
Explain "Why," Not "What": Focus comments on the rationale, design decisions, or the why behind the code, not a transcription of what the code is doing.
Clarify Complexity: Use comments to explain complex algorithms, unidiomatic code, or workarounds for external issues (e.g., API or library bugs).
Use Doc Comments Only for Public APIs:

C++: Use triple-slash Doxygen comments (///) only for public API documentation that tools will consume. For internal code, prefer // comments.
Python: Use triple-quoted docstrings ("""...""") for modules, classes, and public functions/methods that tools (Sphinx, IDEs, help()) will consume. Follow a consistent style (Google, NumPy, or reStructuredText). For internal logic, prefer inline # comments.


Every Class Gets a Docstring: Every class declaration should have at least a one-line docstring stating its purpose — even internal or trivial subclasses. Public classes deserve richer docs per the rule above; this is the minimum floor.
Imperative Mood, No Trailing Period: Write comments in imperative mood (e.g., // Fill buffer with pixel data or # Fill buffer with pixel data) not present tense with "s" (e.g., // Fills buffer with pixel data). Do not end single-line comments with a full stop. Python docstrings describing functions should still use imperative mood ("Return the sum" not "Returns the sum").
Don't Reformat Existing Comments: Only apply these guidelines to new or changed comments. Do not rewrite or remove existing comments just to match style.
Keep Comments Up-to-Date: Outdated or misleading comments are worse than no comments. Always update comments and docstrings when the corresponding code changes.
Use File/Module Headers (Optional for Agent): For professional projects, each file or module should start with a brief summary of its purpose, not details about the author.

✨ C++ Best Practices

Prefer const and constexpr: Make const your default choice for variables and functions wherever possible to ensure immutability and enable compile-time checks.
Use RAII and Smart Pointers: Employ the Resource Acquisition Is Initialization (RAII) idiom and prefer smart pointers (std::unique_ptr, std::shared_ptr) to manage resources and prevent memory leaks. Avoid raw new and delete.
Avoid Macros: Use modern C++ features (e.g., inline functions, enum class, constexpr) instead of preprocessor macros.
Minimal and Focused Functions/Classes: Keep functions short and focused on a single, cohesive responsibility. Avoid deep nesting.
Use Standard Library Components: Prefer standard library containers (std::vector by default), algorithms, and utilities over custom or C-style solutions.
Minimize Global State: Avoid global variables and shared data where possible to reduce coupling and improve maintainability.
Prioritize Type Safety: Use C++-style casts (static_cast, dynamic_cast, const_cast, reinterpret_cast) instead of dangerous C-style casts.

✨ Python Best Practices

Use Type Hints Everywhere: Annotate function signatures, class attributes, and non-obvious variables. Run mypy or pyright in strict mode to catch errors at analysis time rather than runtime.
Prefer Immutability: Use tuple, frozenset, typing.Final, and frozen @dataclass(frozen=True) where appropriate. Treat function arguments as immutable; avoid mutating input collections.
Use Context Managers for Resources: Employ with statements (and contextlib) for files, locks, connections, and other resources. Never rely on __del__ or manual close() calls for cleanup.
Follow PEP 8 and PEP 257: Adhere to standard style and docstring conventions. Use ruff or black for formatting and ruff/flake8 for linting — do not hand-format.
Minimal and Focused Functions/Classes: Keep functions short and focused on a single, cohesive responsibility. Avoid deep nesting; prefer early returns and guard clauses.
Use Standard Library and Idiomatic Constructs: Prefer collections, itertools, functools, pathlib, and comprehensions over hand-rolled loops or C-style patterns. Reach for dataclasses or pydantic models instead of dict-as-struct.
Minimize Global State: Avoid module-level mutable globals. Pass dependencies explicitly; use dependency injection over singletons where possible.
Prioritize Explicitness: Prefer explicit conversions (int(x), str(x)) and keyword arguments for clarity. Avoid *args/**kwargs unless genuinely needed for forwarding.
Handle Exceptions Narrowly: Catch specific exception types, not bare except: or except Exception:. Let unexpected errors propagate rather than silently swallowing them.

❌ Anti-Patterns to Avoid (Both Languages)

Magic Numbers and Strings: Use named constants, enum class (C++), or enum.Enum / enum.StrEnum (Python) instead of raw, unexplained literals.
Cryptic Abbreviations: Avoid 2–3 letter identifiers whose meaning isn't obvious in isolation (e.g., `hw`, `cb`, `fn`, `mgr`, `kw`, `kws`). Universal loop/index vars (`i`, `x`, `n`) and common acronyms (`id`, `url`, `rpc`, `db`) are fine; project-specific terms should be spelled out (`hardware`, `callback`, `keyword`, `all_keywords`). If a reader has to hunt for the definition, the name is too short.
Uninitialized or Unsafe Defaults:

C++: Always initialize variables upon definition to avoid undefined behavior.
Python: Never use mutable default arguments (def f(x=[]):) — use None as the sentinel and create the mutable inside the function.


Deep Nesting/Long Functions: Refactor complex logic into smaller, clearly named functions. Prefer flat over nested.
Stating the Obvious in Comments: Focus on intent, not transcription.
Outdated/Commented-Out Code: Use version control (Git) to manage history; do not leave old code commented out in the source files.
Wildcard or Broad Imports (Python): Avoid from module import * — it pollutes the namespace and obscures origins.
Overusing Inheritance: Prefer composition, protocols (typing.Protocol in Python), and duck typing over deep inheritance hierarchies. In C++, prefer composition over inheritance and use interfaces/abstract base classes sparingly.

Plan new endevours before implementing when possible and keep those plans high level and concise without code examples.
