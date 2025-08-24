-- SQL to manually create the missing DailyCashAwarded table
-- Run this on production database if migrations fail

CREATE TABLE IF NOT EXISTS results_dailycashawarded (
    id BIGSERIAL PRIMARY KEY,
    phone_number VARCHAR(15) NOT NULL,
    award_date DATE NOT NULL,
    cash_awarded DECIMAL(10,2) NOT NULL,
    ticket_number VARCHAR(50) NOT NULL,
    lottery_name VARCHAR(200) NOT NULL,
    awarded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS results_dailycashawarded_phone_number_idx ON results_dailycashawarded(phone_number);
CREATE INDEX IF NOT EXISTS results_dailycashawarded_award_date_idx ON results_dailycashawarded(award_date);

-- Create unique constraint
ALTER TABLE results_dailycashawarded 
ADD CONSTRAINT results_dailycashawarded_phone_number_award_date_uniq 
UNIQUE (phone_number, award_date);

-- Update Django migrations table to mark as applied
INSERT INTO django_migrations (app, name, applied) 
VALUES ('results', '0022_cashtransaction_dailycashawarded_dailycashpool_and_more', NOW())
ON CONFLICT (app, name) DO NOTHING;