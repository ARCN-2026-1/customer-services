class ApplicationError(Exception):
    """Base application-layer exception."""


class CustomerAlreadyExistsError(ApplicationError):
    """Raised when a customer email collides with an existing record."""


class CustomerNotFoundError(ApplicationError):
    """Raised when the requested customer does not exist."""


class AuthenticationFailedError(ApplicationError):
    """Raised when credentials or authentication context are invalid."""


class AuthorizationDeniedError(ApplicationError):
    """Raised when an authenticated actor lacks permission."""


class EventPublicationError(ApplicationError):
    """Raised when publishing an integration event fails."""
