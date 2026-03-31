use sqlx::postgres::PgPoolOptions;
use sqlx::PgPool;

pub async fn create_pool(database_url: &str) -> Result<PgPool, sqlx::Error> {
    PgPoolOptions::new()
        .max_connections(10)
        .connect(database_url)
        .await
}

pub async fn run_migrations(pool: &PgPool) -> Result<(), sqlx::Error> {
    let migration_001 = include_str!("../../migrations/001_initial.sql");
    sqlx::raw_sql(migration_001).execute(pool).await?;

    // Migration 002: add UNIQUE constraint on user_sessions.user_id (idempotent)
    let migration_002 = r#"
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'user_sessions_user_id_unique'
            ) THEN
                ALTER TABLE user_sessions ADD CONSTRAINT user_sessions_user_id_unique UNIQUE (user_id);
            END IF;
        END $$;
    "#;
    sqlx::raw_sql(migration_002).execute(pool).await?;

    tracing::info!("Database migrations applied successfully");
    Ok(())
}
