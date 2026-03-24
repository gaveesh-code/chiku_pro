-- ==========================================
-- CHIKU PRO - PERFECT DATABASE SCHEMA
-- ==========================================
-- Copy all of this and paste it into the Supabase SQL Editor, then click "Run"

-- 1. Create table for Long Term Memories (Facts the agent learns)
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL, -- e.g., 'preference', 'fact', 'contact'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Create table for Chat History (So the LLM remembers previous messages)
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create table for Tasks / Reminders
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable Row Level Security (RLS) policies so our API key has full access
-- We are keeping it simple: The service role and anon key can access these for the desktop app.
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations (since this is a personal desktop agent)
CREATE POLICY "Allow all operations for memories" ON memories FOR ALL USING (true);
CREATE POLICY "Allow all operations for chat_history" ON chat_history FOR ALL USING (true);
CREATE POLICY "Allow all operations for tasks" ON tasks FOR ALL USING (true);
