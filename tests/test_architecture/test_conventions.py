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
    "RateLimitService",
    "JobScheduler",
    "WebhookService",
    "BazarrService",
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
    """Get all .py files in a directory tree, excluding __init__.py."""
    result = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            if f.endswith(".py") and f != "__init__.py":
                result.append(os.path.join(root, f))
    return result


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
        if filepath == excluded or filepath.startswith(excluded + os.sep):
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


def _extract_media_config_methods(filepath):
    """Extract method name strings from the MEDIA_CONFIG dict in dispatch.py.

    Walks the AST to find the MEDIA_CONFIG assignment, then extracts all
    string values that are NOT under the 'config_key' key (those are config
    section names, not MediaService method names).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    methods = []
    for node in ast.iter_child_nodes(tree):
        if not (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "MEDIA_CONFIG"
                        for t in node.targets)):
            continue
        # node.value is the outer dict
        if not isinstance(node.value, ast.Dict):
            continue
        for media_type_dict in node.value.values:
            if not isinstance(media_type_dict, ast.Dict):
                continue
            for key_node, val_node in zip(
                media_type_dict.keys, media_type_dict.values
            ):
                if (isinstance(key_node, ast.Constant)
                        and key_node.value == "config_key"):
                    continue
                if isinstance(val_node, ast.Constant) and isinstance(
                    val_node.value, str
                ):
                    methods.append(val_node.value)
    return methods


def test_media_config_dispatch_integrity():
    """Every method name in MEDIA_CONFIG must exist on MediaService.

    MEDIA_CONFIG maps media types to MediaService method name strings that
    are resolved via getattr() at runtime. A rename typo would only surface
    when a user triggers the command. This test catches the mismatch at CI.
    """
    from src.services.media import MediaService

    dispatch_path = os.path.join(
        HANDLERS_DIR, "media", "dispatch.py"
    )
    method_names = _extract_media_config_methods(dispatch_path)

    assert method_names, (
        "No method names extracted from MEDIA_CONFIG — "
        "is the dict structure still the same?"
    )

    missing = []
    for name in method_names:
        if not hasattr(MediaService, name):
            missing.append(name)

    assert not missing, (
        "MEDIA_CONFIG references methods not found on MediaService: "
        + ", ".join(missing)
    )


# Media state names that must be in sync between dispatch.py and States.
MEDIA_STATE_NAMES = [
    "SEARCHING", "SELECTING", "QUALITY_SELECT", "SEASON_SELECT", "ALBUM_SELECT",
]


def test_media_state_constants_in_sync():
    """Media state constants in dispatch.py must match States class values.

    States are duplicated in dispatch.py (module-level constants) and
    states.py (States class attributes). A drift would cause
    ConversationHandler state routing to silently break.
    """
    from src.bot.handlers.media import dispatch as dispatch_module
    from src.bot.states import States

    mismatches = []
    for name in MEDIA_STATE_NAMES:
        dispatch_val = getattr(dispatch_module, name, "<MISSING>")
        states_val = getattr(States, name, "<MISSING>")
        if dispatch_val != states_val:
            mismatches.append(
                f"{name}: dispatch.py={dispatch_val}, States={states_val}"
            )

    assert not mismatches, (
        "Media state constants out of sync:\n"
        + "\n".join(f"  {m}" for m in mismatches)
    )


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
