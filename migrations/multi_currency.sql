-- Migration: Multi-Currency Support
-- Purpose: PayTR USD/EUR support - Add currency preference
-- Date: 2025-10-28
-- Description: Add preferred_currency column to companies table

-- Add preferred_currency column to companies
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS preferred_currency VARCHAR(3) DEFAULT 'TRY';

-- Add check constraint for valid currencies
ALTER TABLE companies
ADD CONSTRAINT check_valid_currency
CHECK (preferred_currency IN ('TRY', 'USD', 'EUR'));

-- Create index for currency queries
CREATE INDEX IF NOT EXISTS idx_companies_preferred_currency
ON companies(preferred_currency);

-- Add comments
COMMENT ON COLUMN companies.preferred_currency IS 'User preferred payment currency: TRY, USD, or EUR';

-- Note: payments.currency column already exists from previous schema
-- No changes needed to payments table

-- Verification queries:
-- SELECT preferred_currency, COUNT(*) FROM companies GROUP BY preferred_currency;
-- SELECT currency, COUNT(*), SUM(amount) FROM payments GROUP BY currency;
