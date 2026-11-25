"""Persistent user identity service.

Each browser session gets a UUID that is stored in ``st.session_state``
and persisted to the ``users`` table.  The same UUID will map to the
same DB row across page reruns within one browser session.

Usage (called once during app initialisation):

    from services.user_identity import get_or_create_user
    user_db_id = get_or_create_user()   # returns the integer PK
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import streamlit as st

from db.database import get_session
from db.models import User

_SESSION_KEY = "_user_uuid"
_SESSION_DB_ID = "_user_db_id"


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def get_or_create_user() -> int:
    """Return the integer DB primary key for the current browser session user.

    1. If ``st.session_state`` already holds a DB id, return it immediately.
    2. Otherwise look up (or create) the UUID in the ``users`` table and cache
       the integer id in session state so subsequent reruns are free.
    """
    if _SESSION_DB_ID in st.session_state:
        return st.session_state[_SESSION_DB_ID]

    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = _generate_uuid()

    user_uuid: str = st.session_state[_SESSION_KEY]

    with get_session() as session:
        user = session.query(User).filter_by(user_uuid=user_uuid).first()
        if user is None:
            user = User(user_uuid=user_uuid)
            session.add(user)
            session.flush()  # assigns id before commit

        user.last_active = datetime.now(timezone.utc)
        db_id: int = user.id

    st.session_state[_SESSION_DB_ID] = db_id
    return db_id


def get_current_user_uuid() -> str:
    """Return the UUID string for the current session (creates one if needed)."""
    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = _generate_uuid()
    return st.session_state[_SESSION_KEY]
