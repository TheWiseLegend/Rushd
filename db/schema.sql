CREATE TABLE profiles (
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

CREATE TABLE profile_ratings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id     INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    dimension_key  TEXT NOT NULL,                 -- stable machine key, e.g. "emotional_hunger_risk"
    dimension_label TEXT NOT NULL,                -- human-readable, e.g. "Emotional Hunger Risk"
    rating         TEXT NOT NULL CHECK (rating IN ('High', 'Medium', 'Low')),
    UNIQUE (profile_id, dimension_key)
);
