CREATE TABLE IF NOT EXISTS profiles (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    person_label            TEXT NOT NULL,       -- who this profile belongs to (name/handle, not an account)
    self_awareness_summary  TEXT,
    strengths               TEXT,
    weaknesses              TEXT,
    what_to_look_for        TEXT,
    assessment_version      TEXT,                 -- which version of the assessment content produced this, for future comparability
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profile_ratings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id     INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    dimension_key  TEXT NOT NULL,                 -- stable machine key, e.g. "emotional_hunger_risk"
    dimension_label TEXT NOT NULL,                -- human-readable, e.g. "Emotional Hunger Risk"
    rating         TEXT NOT NULL CHECK (rating IN ('High', 'Medium', 'Low')),
    UNIQUE (profile_id, dimension_key)
);

CREATE TABLE IF NOT EXISTS invite_tokens (
    token         TEXT PRIMARY KEY,
    person_label  TEXT NOT NULL,       -- fixed identity for this link; never client-supplied after creation
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    last_used_at  TEXT                 -- tokens are reusable (a durable login, not single-use); NULL until first use
);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id       TEXT PRIMARY KEY,
    person_label     TEXT NOT NULL,   -- must equal invite_tokens.person_label for the authenticated session;
                                       -- every query filters on session_id AND person_label together, never session_id alone
    profile_language TEXT NOT NULL CHECK (profile_language IN ('ar', 'en')),
    messages_json    TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'done')),
    profile_id       INTEGER REFERENCES profiles(id),  -- set once status='done', so the result page can be re-rendered on refresh
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
