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


def _get_call_name(call_node):
    """Get the function/class name from an ast.Call node."""
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id
    if isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr
    return None


def _extract_self_methods(node):
    """Extract all self.method attribute names from an AST subtree."""
    methods = []
    for child in ast.walk(node):
        if (isinstance(child, ast.Attribute)
                and isinstance(child.value, ast.Name)
                and child.value.id == "self"):
            methods.append(child.attr)
    return methods


def _extract_entry_point_methods(class_node):
    """Extract method names used as handler entry points in get_handler().

    Entry points are:
    - Callback methods in standalone CommandHandler calls
    - Callback methods in ConversationHandler entry_points lists
    """
    get_handler = None
    for node in class_node.body:
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "get_handler"):
            get_handler = node
            break
    if not get_handler:
        return []

    # Find the return statement
    return_node = None
    for node in ast.walk(get_handler):
        if isinstance(node, ast.Return) and node.value is not None:
            return_node = node
            break
    if not return_node or not isinstance(return_node.value, ast.List):
        return []

    methods = []
    for elt in return_node.value.elts:
        if not isinstance(elt, ast.Call):
            continue

        func_name = _get_call_name(elt)

        if func_name == "ConversationHandler":
            # Extract self.method references from entry_points keyword
            for kw in elt.keywords:
                if kw.arg == "entry_points":
                    methods.extend(_extract_self_methods(kw.value))
        elif func_name == "CommandHandler":
            # The callback is the 2nd positional arg: CommandHandler(cmd, self.method)
            if len(elt.args) >= 2:
                arg = elt.args[1]
                if (isinstance(arg, ast.Attribute)
                        and isinstance(arg.value, ast.Name)
                        and arg.value.id == "self"):
                    methods.append(arg.attr)

    return methods


def _method_has_decorator(class_node, method_name, decorator_name):
    """Check if a method in a class has a specific decorator."""
    for node in class_node.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != method_name:
            continue
        # Found the method — check its decorators
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id == decorator_name:
                return True
            if isinstance(dec, ast.Attribute) and dec.attr == decorator_name:
                return True
            # Handle @decorator(args) form
            if isinstance(dec, ast.Call):
                if (isinstance(dec.func, ast.Name)
                        and dec.func.id == decorator_name):
                    return True
                if (isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == decorator_name):
                    return True
        # Method found but decorator not present
        return False
    # Method not found in class
    return False


# Handler entry points that intentionally skip @require_auth.
# Each entry documents why the exemption is safe.
AUTH_ALLOWLIST = {
    # AuthHandler IS the auth flow — requiring auth to authenticate is circular
    "AuthHandler.start_auth",
    # TransmissionHandler uses is_enabled() check instead
    "TransmissionHandler.transmission_command",
    # Triggered from StartHandler menu which already enforces auth
    "MediaHandler.handle_menu_callback",
}


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


def test_handler_entry_points_have_require_auth():
    """Handler entry points must use @require_auth unless allowlisted.

    Entry points are methods wired as callbacks in CommandHandler or
    in ConversationHandler entry_points. Missing @require_auth means
    unauthenticated users can access the command.
    """
    missing = []
    for filepath in _get_python_files(HANDLERS_DIR):
        for cls in _get_classes_in_file(filepath):
            if not cls.name.endswith("Handler"):
                continue
            entry_methods = _extract_entry_point_methods(cls)
            for method_name in entry_methods:
                qualified = f"{cls.name}.{method_name}"
                if qualified in AUTH_ALLOWLIST:
                    continue
                if not _method_has_decorator(cls, method_name, "require_auth"):
                    missing.append(qualified)

    assert not missing, (
        "Handler entry points missing @require_auth "
        "(add to AUTH_ALLOWLIST if intentional):\n"
        + "\n".join(f"  {m}" for m in missing)
    )


def _extract_reset_classes(filepath):
    """Extract class names that have ._instance = None in reset_singletons.

    Parses the conftest.py AST to find the reset_singletons function,
    then collects all class names from ClassName._instance = None assignments.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    # Find the reset_singletons function
    func_node = None
    for node in ast.iter_child_nodes(tree):
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "reset_singletons"):
            func_node = node
            break
    if not func_node:
        return set()

    classes = set()
    for node in ast.walk(func_node):
        # Match: ClassName._instance = None
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (isinstance(target, ast.Attribute)
                    and target.attr == "_instance"
                    and isinstance(target.value, ast.Name)):
                classes.add(target.value.id)
    return classes


def test_singleton_reset_coverage():
    """Every SINGLETON_CLASSES entry must be reset in reset_singletons fixture.

    SINGLETON_CLASSES (convention test) and reset_singletons (conftest fixture)
    are manually kept in sync. Adding a service to one but forgetting the other
    means either the convention test misses it or tests leak state.
    """
    conftest_path = os.path.join(PROJECT_ROOT, "tests", "conftest.py")
    reset_classes = _extract_reset_classes(conftest_path)

    # Check SINGLETON_CLASSES are all reset
    not_reset = SINGLETON_CLASSES - reset_classes
    assert not not_reset, (
        "SINGLETON_CLASSES entries missing from reset_singletons fixture: "
        + ", ".join(sorted(not_reset))
    )

    not_in_set = reset_classes - SINGLETON_CLASSES
    # AuthHandler is reset but is not in SINGLETON_CLASSES (it's a handler)
    expected_extra = {"AuthHandler"}
    unexpected = not_in_set - expected_extra
    assert not unexpected, (
        "Classes reset in fixture but missing from SINGLETON_CLASSES: "
        + ", ".join(sorted(unexpected))
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
