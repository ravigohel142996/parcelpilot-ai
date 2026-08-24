import contextvars
from contextlib import contextmanager

class UserContext:
    """
    Represents the active user authentication and authorization context.
    
    Attributes:
      user_id (str): Unique user identifier.
      role (str): Role designation (e.g., 'SUPPORT_OPERATIONS', 'CUSTOMER_SUPPORT').
      authorised_accounts (list): List of account IDs the user is authorized to access,
                                   or ['*'] for unrestricted access.
    """
    def __init__(self, user_id: str, role: str, authorised_accounts: list):
        self.user_id = user_id
        self.role = role
        self.authorised_accounts = authorised_accounts

# Thread-safe and async-safe ContextVar to store the current user context
_current_user = contextvars.ContextVar("current_user", default=None)

@contextmanager
def active_user(user: UserContext):
    """
    Context manager to temporarily set the active user context.
    Usage:
        with active_user(demo_user):
            # perform operations
    """
    token = _current_user.set(user)
    try:
        yield
    finally:
        _current_user.reset(token)

def get_current_user() -> UserContext:
    """
    Retrieves the active user context.
    Raises PermissionError if no user context has been set.
    """
    user = _current_user.get()
    if user is None:
        raise PermissionError("Access Denied: No active user context set.")
    return user

def check_account_access(account_id: str):
    """
    Checks if the active user context has access to the specified account_id.
    Raises PermissionError if unauthorized.
    """
    if not account_id:
        raise PermissionError("Access Denied: Missing account identifier.")
        
    user = get_current_user()
    
    # Wildcard access check
    if "*" in user.authorised_accounts:
        return
        
    # Standard check
    if account_id not in user.authorised_accounts:
        raise PermissionError(
            f"Access Denied: User '{user.user_id}' with role '{user.role}' "
            f"is not authorized to access account '{account_id}'."
        )

# Demo User Context as requested
DEMO_USER_RAVI = UserContext(
    user_id="demo-ravi",
    role="SUPPORT_OPERATIONS",
    authorised_accounts=["*"]
)
