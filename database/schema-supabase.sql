-- ════════════════════════════════════════════════════════════════════════════════
-- Smart e-Print Database Schema for Supabase PostgreSQL
-- Run this in Supabase SQL Editor to set up the database
-- ════════════════════════════════════════════════════════════════════════════════

-- Drop existing tables (if any) to start fresh
DROP TABLE IF EXISTS print_orders CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ════════════════════════════════════════════════════════════════════════════════
-- USERS TABLE
-- Stores both Customer and Owner accounts
-- ════════════════════════════════════════════════════════════════════════════════
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('customer', 'owner')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on email for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ════════════════════════════════════════════════════════════════════════════════
-- PRINT ORDERS TABLE
-- Stores customer print orders and upload metadata
-- ════════════════════════════════════════════════════════════════════════════════
CREATE TABLE print_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- File Information
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_type VARCHAR(20) NOT NULL CHECK (file_type IN ('pdf', 'png', 'jpg', 'jpeg')),
    mime_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    
    -- Print Configuration
    print_mode VARCHAR(20) NOT NULL CHECK (print_mode IN ('bw', 'color')),
    copies INTEGER NOT NULL DEFAULT 1,
    page_range VARCHAR(100) NOT NULL,
    paper_size VARCHAR(20) DEFAULT 'A4' CHECK (paper_size IN ('A3', 'A4', 'Letter')),
    
    -- Pricing Calculation
    printed_pages INTEGER NOT NULL,
    unit_rate FLOAT NOT NULL,
    multiplier FLOAT NOT NULL,
    total_price FLOAT NOT NULL,
    
    -- Order Status
    status VARCHAR(30) NOT NULL DEFAULT 'Submitted' CHECK (status IN ('Submitted', 'Accepted', 'Rejected', 'Printing', 'Completed')),
    rejection_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_print_orders_user_id ON print_orders(user_id);
CREATE INDEX idx_print_orders_status ON print_orders(status);
CREATE INDEX idx_print_orders_created_at ON print_orders(created_at);

-- ════════════════════════════════════════════════════════════════════════════════
-- Enable Row Level Security (RLS) for Multi-Tenant Support
-- ════════════════════════════════════════════════════════════════════════════════

-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE print_orders ENABLE ROW LEVEL SECURITY;

-- Users can only view their own data
CREATE POLICY "Users can view their own profile"
    ON users
    FOR SELECT
    USING (auth.uid()::text = id::text OR role = 'owner');

-- Users can only view their own orders
CREATE POLICY "Users can view their own orders"
    ON print_orders
    FOR SELECT
    USING (auth.uid()::text = user_id::text);

-- Users can only insert their own orders
CREATE POLICY "Users can create their own orders"
    ON print_orders
    FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

-- ════════════════════════════════════════════════════════════════════════════════
-- Sample Data (Optional - for testing)
-- ════════════════════════════════════════════════════════════════════════════════

-- Insert test user (customer)
-- INSERT INTO users (name, email, password_hash, role)
-- VALUES ('Test Customer', 'customer@test.com', 'hashed_password_here', 'customer');

-- Insert test user (owner)
-- INSERT INTO users (name, email, password_hash, role)
-- VALUES ('Shop Owner', 'owner@test.com', 'hashed_password_here', 'owner');
