-- Add UNIQUE constraint on user_sessions.user_id so ON CONFLICT (user_id) works in upsert
ALTER TABLE user_sessions ADD CONSTRAINT user_sessions_user_id_unique UNIQUE (user_id);
