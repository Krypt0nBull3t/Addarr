"""
Layer boundary tests using PyTestArch.

Enforces the three-layer architecture: handlers -> services -> api.
Lower layers must not depend on higher layers. Utilities and config
must not depend on handlers or services.
"""

from pytestarch import Rule


def test_services_do_not_import_handlers(evaluable):
    """Services must not depend on the handler layer.

    The service layer provides business logic consumed by handlers.
    Reverse dependencies would create circular imports and violate
    the handlers -> services -> api layering.
    """
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.services")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.bot.handlers")
    )
    rule.assert_applies(evaluable)


def test_api_clients_do_not_import_handlers(evaluable):
    """API clients must not depend on the handler layer.

    API clients are the lowest layer — they talk to external services.
    They should have no knowledge of how handlers orchestrate them.
    """
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.api")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.bot.handlers")
    )
    rule.assert_applies(evaluable)


def test_api_clients_do_not_import_services(evaluable):
    """API clients must not depend on the service layer.

    Services aggregate API clients, not the other way around.
    An API client importing a service would invert the dependency.
    """
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.api")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.services")
    )
    rule.assert_applies(evaluable)


def test_utils_do_not_import_handlers(evaluable):
    """Utilities must not depend on the handler layer.

    Utils are shared infrastructure used across all layers.
    Depending on handlers would create circular dependencies.
    """
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.utils")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.bot.handlers")
    )
    rule.assert_applies(evaluable)


def test_utils_do_not_import_services(evaluable):
    """Utilities must not depend on the service layer.

    Utils are lower-level than services. Services may use utils,
    but not vice versa.
    """
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.utils")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.services")
    )
    rule.assert_applies(evaluable)


def test_config_does_not_import_handlers_or_services(evaluable):
    """Config must not depend on handlers or services.

    Config is foundational — nearly everything depends on it.
    It must not create upward dependencies into business logic.
    """
    no_handlers = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.config")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.bot.handlers")
    )
    no_services = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.config")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.services")
    )
    no_handlers.assert_applies(evaluable)
    no_services.assert_applies(evaluable)


def test_handlers_do_not_import_api_clients_directly(evaluable):
    """Handlers must not import API clients directly.

    Handlers should access API clients through the service layer.
    Direct imports bypass business logic and create tight coupling.
    """
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("src.bot.handlers")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("src.api")
    )
    rule.assert_applies(evaluable)
