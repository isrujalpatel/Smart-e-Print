-- =============================================================================
-- Smart e-Print — PostgreSQL Database Schema
-- Strict 3-Role System: customer, admin, super_admin
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role          VARCHAR(20) NOT NULL CHECK (role IN ('customer', 'admin', 'super_admin')),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMPTZ,
    login_count   INTEGER NOT NULL DEFAULT 0,
    google_id     VARCHAR(255),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role  ON users (role);

-- Table: print_orders
CREATE TABLE IF NOT EXISTS print_orders (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID REFERENCES users(id) ON DELETE SET NULL,
    customer_name    VARCHAR(100),
    customer_email   VARCHAR(255),
    file_name        VARCHAR(255) NOT NULL,
    file_path        VARCHAR(512) NOT NULL,
    file_type        VARCHAR(20) NOT NULL CHECK (file_type IN ('pdf', 'png', 'jpg', 'jpeg')),
    mime_type        VARCHAR(100) NOT NULL,
    file_size        INTEGER NOT NULL,
    page_count       INTEGER NOT NULL,
    print_mode       VARCHAR(20) NOT NULL CHECK (print_mode IN ('bw', 'color')),
    copies           INTEGER NOT NULL DEFAULT 1,
    page_range       VARCHAR(100) NOT NULL,
    paper_size       VARCHAR(20) DEFAULT 'A4' CHECK (paper_size IN ('A3', 'A4', 'Letter')),
    printed_pages    INTEGER NOT NULL,
    unit_rate        FLOAT NOT NULL,
    multiplier       FLOAT NOT NULL,
    total_price      FLOAT NOT NULL,
    status           VARCHAR(30) NOT NULL DEFAULT 'Submitted' CHECK (status IN ('Submitted', 'Accepted', 'Rejected', 'Printing', 'Completed')),
    rejection_reason TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table: audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    actor_role VARCHAR(30),
    action     VARCHAR(100) NOT NULL,
    details    TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
