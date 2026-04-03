-- Canonical email uniqueness and helpful indexes

CREATE UNIQUE INDEX users_email_lower_unique ON users (LOWER(TRIM(email)));

CREATE INDEX idx_users_role_id ON users (role_id);
CREATE INDEX idx_users_is_active ON users (is_active);

CREATE INDEX idx_access_rules_role ON access_role_rules (role_id);
CREATE INDEX idx_access_rules_be ON access_role_rules (business_element_id);

CREATE INDEX idx_auth_sessions_user ON auth_sessions (user_id);
CREATE INDEX idx_auth_sessions_expires ON auth_sessions (expires_at);

CREATE INDEX idx_refresh_tokens_session ON refresh_tokens (session_id);

CREATE INDEX idx_mock_documents_owner ON mock_documents (owner_id);
CREATE INDEX idx_mock_reports_owner ON mock_reports (owner_id);

ALTER TABLE auth_sessions
    ADD CONSTRAINT chk_revocation_reason
    CHECK (revocation_reason IS NULL OR revocation_reason IN (
        'logout', 'soft_delete', 'refresh_reuse', 'expired', 'admin_action'
    ));

ALTER TABLE access_rule_audit
    ADD CONSTRAINT chk_change_type
    CHECK (change_type IN ('create', 'update'));
