-- Migration 002: Add metadata fields to bindings table
-- Adds: notes, notify_text, notify_emoji for enhanced binding features

ALTER TABLE bindings ADD COLUMN notes TEXT DEFAULT '';
ALTER TABLE bindings ADD COLUMN notify_text TEXT DEFAULT '';
ALTER TABLE bindings ADD COLUMN notify_emoji TEXT DEFAULT '';
