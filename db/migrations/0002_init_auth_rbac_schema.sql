-- Core auth / RBAC / mock tables

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    role_id UUID NOT NULL REFERENCES roles (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deactivated_at TIMESTAMPTZ
);

CREATE TABLE business_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(64) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE access_role_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    business_element_id UUID NOT NULL REFERENCES business_elements (id) ON DELETE CASCADE,
    read_permission BOOLEAN NOT NULL DEFAULT FALSE,
    read_all_permission BOOLEAN NOT NULL DEFAULT FALSE,
    create_permission BOOLEAN NOT NULL DEFAULT FALSE,
    update_permission BOOLEAN NOT NULL DEFAULT FALSE,
    update_all_permission BOOLEAN NOT NULL DEFAULT FALSE,
    delete_permission BOOLEAN NOT NULL DEFAULT FALSE,
    delete_all_permission BOOLEAN NOT NULL DEFAULT FALSE,
    version BIGINT NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (role_id, business_element_id)
);

CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revocation_reason VARCHAR(32)
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES auth_sessions (id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    rotated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    replaced_by_id UUID REFERENCES refresh_tokens (id)
);

CREATE TABLE access_rule_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    access_role_rule_id UUID NOT NULL REFERENCES access_role_rules (id) ON DELETE CASCADE,
    changed_by_user_id UUID NOT NULL REFERENCES users (id),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    change_type VARCHAR(16) NOT NULL,
    before_snapshot JSONB,
    after_snapshot JSONB NOT NULL
);

CREATE TABLE mock_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title VARCHAR(512) NOT NULL,
    status VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE mock_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title VARCHAR(512) NOT NULL,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
