import uuid
from datetime import datetime

from schemas.token import TokenCreate


def test_token_create_schema():
    uid = uuid.uuid4()
    exp = datetime(2026, 1, 1, 12, 0, 0)
    tc = TokenCreate(token_value="abc123", user_id=uid, expires_at=exp)
    assert tc.token_value == "abc123"
    assert tc.user_id == uid
    assert tc.expires_at == exp
