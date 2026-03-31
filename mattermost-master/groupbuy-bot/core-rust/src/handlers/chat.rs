use actix_web::{web, HttpResponse};
use sqlx::PgPool;

use crate::models::chat::*;

/// GET /api/chat/messages/?procurement=...&user=...
pub async fn list_messages(
    pool: web::Data<PgPool>,
    query: web::Query<MessageQuery>,
) -> HttpResponse {
    let messages = match (query.procurement, query.user) {
        (Some(procurement_id), Some(user_id)) => {
            sqlx::query_as::<_, Message>(
                "SELECT * FROM chat_messages WHERE procurement_id = $1 AND user_id = $2 AND is_deleted = false ORDER BY created_at ASC",
            )
            .bind(procurement_id)
            .bind(user_id)
            .fetch_all(pool.get_ref())
            .await
        }
        (Some(procurement_id), None) => {
            sqlx::query_as::<_, Message>(
                "SELECT * FROM chat_messages WHERE procurement_id = $1 AND is_deleted = false ORDER BY created_at ASC",
            )
            .bind(procurement_id)
            .fetch_all(pool.get_ref())
            .await
        }
        (None, Some(user_id)) => {
            sqlx::query_as::<_, Message>(
                "SELECT * FROM chat_messages WHERE user_id = $1 AND is_deleted = false ORDER BY created_at ASC LIMIT 100",
            )
            .bind(user_id)
            .fetch_all(pool.get_ref())
            .await
        }
        (None, None) => {
            sqlx::query_as::<_, Message>(
                "SELECT * FROM chat_messages WHERE is_deleted = false ORDER BY created_at ASC LIMIT 100",
            )
            .fetch_all(pool.get_ref())
            .await
        }
    };

    match messages {
        Ok(msgs) => HttpResponse::Ok().json(serde_json::json!({"results": msgs})),
        Err(e) => {
            tracing::error!("Failed to fetch messages: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// POST /api/chat/messages/
pub async fn create_message(
    pool: web::Data<PgPool>,
    body: web::Json<CreateMessage>,
) -> HttpResponse {
    let data = body.into_inner();
    let message_type = data.message_type.unwrap_or_else(|| "text".to_string());
    let attachment_url = data.attachment_url.unwrap_or_default();

    match sqlx::query_as::<_, Message>(
        r#"INSERT INTO chat_messages (procurement_id, user_id, message_type, text, attachment_url)
           VALUES ($1, $2, $3, $4, $5)
           RETURNING *"#,
    )
    .bind(data.procurement)
    .bind(data.user)
    .bind(&message_type)
    .bind(&data.text)
    .bind(&attachment_url)
    .fetch_one(pool.get_ref())
    .await
    {
        Ok(message) => HttpResponse::Created().json(message),
        Err(e) => {
            tracing::error!("Failed to create message: {}", e);
            HttpResponse::BadRequest().json(serde_json::json!({"error": format!("{}", e)}))
        }
    }
}

/// GET /api/chat/messages/unread_count/?user_id=...&procurement_id=...
pub async fn get_unread_count(
    pool: web::Data<PgPool>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> HttpResponse {
    let user_id: Option<i32> = query.get("user_id").and_then(|v| v.parse().ok());
    let procurement_id: Option<i32> = query.get("procurement_id").and_then(|v| v.parse().ok());

    match (user_id, procurement_id) {
        (Some(uid), Some(pid)) => {
            // Count messages after user's last read
            let count: i64 = sqlx::query_scalar(
                r#"SELECT COUNT(*) FROM chat_messages cm
                   WHERE cm.procurement_id = $1
                   AND cm.is_deleted = false
                   AND cm.user_id != $2
                   AND cm.created_at > COALESCE(
                       (SELECT last_read_at FROM message_reads WHERE user_id = $2 AND procurement_id = $1),
                       '1970-01-01'::timestamptz
                   )"#,
            )
            .bind(pid)
            .bind(uid)
            .fetch_one(pool.get_ref())
            .await
            .unwrap_or(0);

            HttpResponse::Ok().json(serde_json::json!({"unread_count": count}))
        }
        _ => HttpResponse::BadRequest()
            .json(serde_json::json!({"error": "user_id and procurement_id are required"})),
    }
}

/// GET /api/chat/notifications/?user=...
pub async fn list_notifications(
    pool: web::Data<PgPool>,
    query: web::Query<NotificationQuery>,
) -> HttpResponse {
    let notifications = if let Some(user_id) = query.user {
        sqlx::query_as::<_, Notification>(
            "SELECT * FROM notifications WHERE user_id = $1 ORDER BY created_at DESC",
        )
        .bind(user_id)
        .fetch_all(pool.get_ref())
        .await
    } else {
        sqlx::query_as::<_, Notification>(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 100",
        )
        .fetch_all(pool.get_ref())
        .await
    };

    match notifications {
        Ok(notifs) => HttpResponse::Ok().json(notifs),
        Err(e) => {
            tracing::error!("Failed to fetch notifications: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}
