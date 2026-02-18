-- Run this in Supabase SQL Editor

CREATE TABLE questions (
  id TEXT PRIMARY KEY,
  section TEXT NOT NULL,
  subsection TEXT,
  question_number INTEGER,
  system TEXT,
  question_stem TEXT NOT NULL,
  choices JSONB NOT NULL,
  correct_answer TEXT NOT NULL,
  correct_explanation TEXT,
  incorrect_explanation TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

-- Allow public read access (authenticated and anon)
CREATE POLICY "Public read access" ON questions
  FOR SELECT USING (true);
