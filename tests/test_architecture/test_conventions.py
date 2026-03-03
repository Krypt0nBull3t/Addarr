"""
Structural convention tests using stdlib ast.

Verifies that handler, service, and API client classes follow
the project's established patterns: required methods, singleton
pattern, and config access conventions.
"""

import ast
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
HANDLERS_DIR = os.path.join(SRC_DIR, "bot", "handlers")
SERVICES_DIR = os.path.join(SRC_DIR, "services")
API_DIR = os.path.join(SRC_DIR, "api")

# Service classes that must implement the singleton pattern.
# Explicit set because JobScheduler doesn't follow *Service naming.
SINGLETON_CLASSES = {
    "MediaService",
    "HealthService",
    "TranslationService",
    "TransmissionService",
    "SABnzbdService",
    "PreferencesService",
    "NotificationService",
    "JobScheduler",
}

# Paths excluded from the config bracket access check.
# Setup code legitimately builds config interactively.
# base.py accesses self.config (pre-extracted service dict).
# settings.py defines __getitem__ on the Config class.
BRACKET_ACCESS_EXCLUDED = {
    os.path.join(SRC_DIR, "setup"),
    os.path.join(SRC_DIR, "api", "base.py"),
    os.path.join(SRC_DIR, "config", "settings.py"),
}


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _get_python_files(directory):
    """Get all .py files in a directory, excluding __init__.py."""
    return [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.endswith(".py") and f != "__init__.py"
    ]


def _get_classes_in_file(filepath):
    """Parse a file and return all top-level class definitions."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    return [node for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.ClassDef)]


def _class_has_method(class_node, method_name):
    """Check if a class AST node defines a method with the given name."""
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
        for node in class_node.body
    )


def _class_inherits_from(class_node, base_name):
    """Check if a class inherits from a given base class name."""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == base_name:
            return True
        if isinstance(base, ast.Attribute) and base.attr == base_name:
            return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_handlers_have_get_handler():
    """Every *Handler class in src/bot/handlers/ must expose get_handler().

    Handlers register themselves with the bot by returning ConversationHandler
    or CommandHandler instances from get_handler(). Missing this method means
    the handler can't be registered in AddarrBot._add_handlers().
    """
    missing = []
    for filepath in _get_python_files(HANDLERS_DIR):
        for cls in _get_classes_in_file(filepath):
            if cls.name.endswith("Handler"):
                if not _class_has_method(cls, "get_handler"):
                    filename = os.path.basename(filepath)
                    missing.append(f"{filename}:{cls.name}")

    assert not missing, (
        f"Handler classes missing get_handler(): {', '.join(missing)}"
    )


def test_all_services_implement_singleton():
    """Every service class must implement __new__() for singleton pattern.

    Services are singletons to maintain shared state (e.g., API client
    instances, cached translations). Missing __new__() means multiple
    instances could be created, causing state inconsistency.
    """
    missing = []
    for filepath in _get_python_files(SERVICES_DIR):
        for cls in _get_classes_in_file(filepath):
            if cls.name in SINGLETON_CLASSES:
                if not _class_has_method(cls, "__new__"):
                    filename = os.path.basename(filepath)
                    missing.append(f"{filename}:{cls.name}")

    assert not missing, (
        f"Service classes missing __new__() singleton: {', '.join(missing)}"
    )


def test_all_api_clients_implement_search():
    """Every BaseApiClient subclass must implement search().

    Media API clients (Radarr, Sonarr, Lidarr) inherit from BaseApiClient
    which declares search() as abstract. This test catches any new client
    that forgets to implement it.

    Download clients (Transmission, SABnzbd) don't inherit BaseApiClient
    and are intentionally excluded.
    """
    missing = []
    for filepath in _get_python_files(API_DIR):
        for cls in _get_classes_in_file(filepath):
            if _class_inherits_from(cls, "BaseApiClient"):
                if not _class_has_method(cls, "search"):
                    filename = os.path.basename(filepath)
                    missing.append(f"{filename}:{cls.name}")

    assert not missing, (
        f"BaseApiClient subclasses missing search(): {', '.join(missing)}"
    )


def _is_excluded_from_bracket_check(filepath):
    """Check if a filepath is excluded from the bracket access rule."""
    for excluded in BRACKET_ACCESS_EXCLUDED:
        if filepath.startswith(excluded):
            return True
    return False


def _find_config_bracket_access(filepath):
    """Find config["key"] or config['key'] patterns via AST.

    Detects ast.Subscript nodes where the value is a Name node
    with id "config" — i.e., module-level config["..."] access.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "config"
        ):
            violations.append(node.lineno)
    return violations


def test_no_config_bracket_access_in_business_logic():
    """Business logic must use config.get() instead of config["key"].

    Bracket access raises KeyError on missing keys with no fallback.
    Using config.get(key, default) provides graceful degradation.

    Excluded: src/setup/ (builds config interactively),
    src/api/base.py (accesses self.config service dict),
    src/config/settings.py (defines __getitem__).
    """
    violations = []
    for root, dirs, files in os.walk(SRC_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(root, filename)
            if _is_excluded_from_bracket_check(filepath):
                continue
            lines = _find_config_bracket_access(filepath)
            if lines:
                rel = os.path.relpath(filepath, PROJECT_ROOT)
                for line in lines:
                    violations.append(f"{rel}:{line}")

    assert not violations, (
        "Found config['key'] bracket access (use config.get() instead):\n"
        + "\n".join(f"  {v}" for v in violations)
    )
