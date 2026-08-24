import pytest
from utils.auth import DEMO_USER_RAVI, active_user
from db.setup_db import setup_database

@pytest.fixture(autouse=True)
def fresh_database_and_user_context():
    """
    Resets the SQLite database to a clean snapshot state before each test
    and automatically sets the active user context to demo-ravi.
    """
    setup_database()
    from agent.approval_state import cancel_escalation
    cancel_escalation() # clear any pending approval states from previous tests
    with active_user(DEMO_USER_RAVI):
        yield
