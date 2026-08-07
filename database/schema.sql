-- =============================================================================
-- Smart e-Print — PostgreSQL Database Schema
-- Run this in your Supabase SQL Editor to initialize the database
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Table: users
-- Stores both Customer and Owner accounts
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id            UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(255)  UNIQUE NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    role          VARCHAR(20)   NOT NULL
                                CHECK (role IN ('customer', 'owner')),
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role  ON users (role);

-- =============================================================================
-- Future tables (added in subsequent phases):
--
-- print_orders  — customer print requests
-- shop_settings — owner-configured rates (B&W, Color, paper sizes)
-- payments      — payment records (Cash / Razorpay)
-- =============================================================================
