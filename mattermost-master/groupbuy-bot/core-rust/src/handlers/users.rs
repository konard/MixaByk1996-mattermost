use actix_web::{web, HttpResponse};
use rust_decimal::Decimal;
use sqlx::PgPool;

use crate::models::user::*;

/// GET /api/users/
pub async fn list_users(pool: web::Data<PgPool>) -> HttpResponse {
    match sqlx::query_as::<_, User>("SELECT * FROM users ORDER BY created_at DESC")
        .fetch_all(pool.get_ref())
        .await
    {
        Ok(users) => {
            let responses: Vec<UserResponse> = users.into_iter().map(UserResponse::from).collect();
            HttpResponse::Ok().json(responses)
        }
        Err(e) => {
            tracing::error!("Failed to fetch users: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// POST /api/users/
pub async fn create_user(pool: web::Data<PgPool>, body: web::Json<CreateUser>) -> HttpResponse {
    let data = body.into_inner();

    if data.platform_user_id.is_empty() {
        return HttpResponse::BadRequest()
            .json(serde_json::json!({"platform_user_id": ["Обязательное поле."]}));
    }

    let platform = data.platform.unwrap_or_else(|| "telegram".to_string());
    let username = data.username.unwrap_or_default();
    let last_name = data.last_name.unwrap_or_default();
    let phone = data.phone.unwrap_or_default();
    let email = data.email.unwrap_or_default();
    let role = data.role.unwrap_or_else(|| "buyer".to_string());
    let language_code = data.language_code.unwrap_or_else(|| "ru".to_string());

    // Normalize phone
    let phone = if !phone.is_empty() && !phone.starts_with('+') {
        format!("+{}", phone)
    } else {
        phone
    };

    match sqlx::query_as::<_, User>(
        r#"INSERT INTO users (platform, platform_user_id, username, first_name, last_name, phone, email, role, language_code)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
           RETURNING *"#,
    )
    .bind(&platform)
    .bind(&data.platform_user_id)
    .bind(&username)
    .bind(&data.first_name)
    .bind(&last_name)
    .bind(&phone)
    .bind(&email)
    .bind(&role)
    .bind(&language_code)
    .fetch_one(pool.get_ref())
    .await
    {
        Ok(user) => HttpResponse::Created().json(UserResponse::from(user)),
        Err(e) => {
            tracing::error!("Failed to create user: {}", e);
            if e.to_string().contains("unique") || e.to_string().contains("duplicate") {
                HttpResponse::BadRequest()
                    .json(serde_json::json!({"error": "User with this platform and platform_user_id already exists"}))
            } else {
                HttpResponse::BadRequest()
                    .json(serde_json::json!({"error": format!("{}", e)}))
            }
        }
    }
}

/// GET /api/users/{id}/
pub async fn get_user(pool: web::Data<PgPool>, path: web::Path<i32>) -> HttpResponse {
    let user_id = path.into_inner();
    match sqlx::query_as::<_, User>("SELECT * FROM users WHERE id = $1")
        .bind(user_id)
        .fetch_optional(pool.get_ref())
        .await
    {
        Ok(Some(user)) => HttpResponse::Ok().json(UserResponse::from(user)),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."})),
        Err(e) => {
            tracing::error!("Failed to fetch user: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// PATCH /api/users/{id}/
pub async fn update_user(
    pool: web::Data<PgPool>,
    path: web::Path<i32>,
    body: web::Json<UpdateUser>,
) -> HttpResponse {
    let user_id = path.into_inner();
    let data = body.into_inner();

    // Build dynamic update query
    let mut updates = Vec::new();
    let mut param_idx = 1;

    if data.first_name.is_some() {
        param_idx += 1;
        updates.push(format!("first_name = ${}", param_idx));
    }
    if data.last_name.is_some() {
        param_idx += 1;
        updates.push(format!("last_name = ${}", param_idx));
    }
    if data.phone.is_some() {
        param_idx += 1;
        updates.push(format!("phone = ${}", param_idx));
    }
    if data.email.is_some() {
        param_idx += 1;
        updates.push(format!("email = ${}", param_idx));
    }
    if data.role.is_some() {
        param_idx += 1;
        updates.push(format!("role = ${}", param_idx));
    }

    if updates.is_empty() {
        return match sqlx::query_as::<_, User>("SELECT * FROM users WHERE id = $1")
            .bind(user_id)
            .fetch_optional(pool.get_ref())
            .await
        {
            Ok(Some(user)) => HttpResponse::Ok().json(UserResponse::from(user)),
            Ok(None) => {
                HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."}))
            }
            Err(e) => {
                tracing::error!("Failed to fetch user: {}", e);
                HttpResponse::InternalServerError()
                    .json(serde_json::json!({"error": "Database error"}))
            }
        };
    }

    updates.push("updated_at = NOW()".to_string());
    let query = format!(
        "UPDATE users SET {} WHERE id = $1 RETURNING *",
        updates.join(", ")
    );

    let mut q = sqlx::query_as::<_, User>(&query).bind(user_id);

    if let Some(ref v) = data.first_name {
        q = q.bind(v);
    }
    if let Some(ref v) = data.last_name {
        q = q.bind(v);
    }
    if let Some(ref v) = data.phone {
        q = q.bind(v);
    }
    if let Some(ref v) = data.email {
        q = q.bind(v);
    }
    if let Some(ref v) = data.role {
        q = q.bind(v);
    }

    match q.fetch_optional(pool.get_ref()).await {
        Ok(Some(user)) => HttpResponse::Ok().json(UserResponse::from(user)),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."})),
        Err(e) => {
            tracing::error!("Failed to update user: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// DELETE /api/users/{id}/
pub async fn delete_user(pool: web::Data<PgPool>, path: web::Path<i32>) -> HttpResponse {
    let user_id = path.into_inner();
    match sqlx::query("DELETE FROM users WHERE id = $1")
        .bind(user_id)
        .execute(pool.get_ref())
        .await
    {
        Ok(result) => {
            if result.rows_affected() > 0 {
                HttpResponse::NoContent().finish()
            } else {
                HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."}))
            }
        }
        Err(e) => {
            tracing::error!("Failed to delete user: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// GET /api/users/by_platform/?platform=...&platform_user_id=...
pub async fn get_user_by_platform(
    pool: web::Data<PgPool>,
    query: web::Query<PlatformQuery>,
) -> HttpResponse {
    let platform = query.platform.clone().unwrap_or_else(|| "telegram".to_string());
    let platform_user_id = match &query.platform_user_id {
        Some(id) => id.clone(),
        None => {
            return HttpResponse::BadRequest()
                .json(serde_json::json!({"error": "platform_user_id is required"}))
        }
    };

    match sqlx::query_as::<_, User>(
        "SELECT * FROM users WHERE platform = $1 AND platform_user_id = $2",
    )
    .bind(&platform)
    .bind(&platform_user_id)
    .fetch_optional(pool.get_ref())
    .await
    {
        Ok(Some(user)) => HttpResponse::Ok().json(UserResponse::from(user)),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."})),
        Err(e) => {
            tracing::error!("Failed to fetch user by platform: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// GET /api/users/check_exists/?platform=...&platform_user_id=...
pub async fn check_user_exists(
    pool: web::Data<PgPool>,
    query: web::Query<PlatformQuery>,
) -> HttpResponse {
    let platform = query.platform.clone().unwrap_or_else(|| "telegram".to_string());
    let platform_user_id = match &query.platform_user_id {
        Some(id) => id.clone(),
        None => {
            return HttpResponse::BadRequest()
                .json(serde_json::json!({"error": "platform_user_id is required"}))
        }
    };

    match sqlx::query_scalar::<_, bool>(
        "SELECT EXISTS(SELECT 1 FROM users WHERE platform = $1 AND platform_user_id = $2)",
    )
    .bind(&platform)
    .bind(&platform_user_id)
    .fetch_one(pool.get_ref())
    .await
    {
        Ok(exists) => HttpResponse::Ok().json(serde_json::json!({"exists": exists})),
        Err(e) => {
            tracing::error!("Failed to check user exists: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// GET /api/users/{id}/balance/
pub async fn get_user_balance(pool: web::Data<PgPool>, path: web::Path<i32>) -> HttpResponse {
    let user_id = path.into_inner();
    match sqlx::query_as::<_, User>("SELECT * FROM users WHERE id = $1")
        .bind(user_id)
        .fetch_optional(pool.get_ref())
        .await
    {
        Ok(Some(user)) => {
            // Calculate totals from transactions
            let deposited: Decimal = sqlx::query_scalar(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND transaction_type = 'deposit'",
            )
            .bind(user_id)
            .fetch_one(pool.get_ref())
            .await
            .unwrap_or(Decimal::ZERO);

            let spent: Decimal = sqlx::query_scalar(
                "SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions WHERE user_id = $1 AND amount < 0",
            )
            .bind(user_id)
            .fetch_one(pool.get_ref())
            .await
            .unwrap_or(Decimal::ZERO);

            HttpResponse::Ok().json(UserBalanceResponse {
                balance: user.balance,
                total_deposited: deposited,
                total_spent: spent,
                available: user.balance,
            })
        }
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."})),
        Err(e) => {
            tracing::error!("Failed to fetch user balance: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// POST /api/users/{id}/update_balance/
pub async fn update_user_balance(
    pool: web::Data<PgPool>,
    path: web::Path<i32>,
    body: web::Json<UpdateBalanceRequest>,
) -> HttpResponse {
    let user_id = path.into_inner();
    let amount = Decimal::try_from(body.amount).unwrap_or(Decimal::ZERO);

    match sqlx::query_as::<_, User>(
        "UPDATE users SET balance = balance + $2, updated_at = NOW() WHERE id = $1 RETURNING *",
    )
    .bind(user_id)
    .bind(amount)
    .fetch_optional(pool.get_ref())
    .await
    {
        Ok(Some(user)) => HttpResponse::Ok().json(serde_json::json!({
            "balance": user.balance,
            "message": "Balance updated successfully"
        })),
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."})),
        Err(e) => {
            tracing::error!("Failed to update balance: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// GET /api/users/{id}/role/
pub async fn get_user_role(pool: web::Data<PgPool>, path: web::Path<i32>) -> HttpResponse {
    let user_id = path.into_inner();
    match sqlx::query_as::<_, User>("SELECT * FROM users WHERE id = $1")
        .bind(user_id)
        .fetch_optional(pool.get_ref())
        .await
    {
        Ok(Some(user)) => {
            let role_display = match user.role.as_str() {
                "buyer" => "Buyer",
                "organizer" => "Organizer",
                "supplier" => "Supplier",
                other => other,
            };
            HttpResponse::Ok().json(serde_json::json!({
                "role": user.role,
                "role_display": role_display
            }))
        }
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."})),
        Err(e) => {
            tracing::error!("Failed to fetch user role: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

// ---- Session handlers ----

/// POST /api/users/sessions/set_state/
pub async fn set_session_state(
    pool: web::Data<PgPool>,
    body: web::Json<SetSessionState>,
) -> HttpResponse {
    let data = body.into_inner();

    let dialog_type = data.dialog_type.unwrap_or_default();
    let dialog_state = data.dialog_state.unwrap_or_default();
    let dialog_data = data
        .dialog_data
        .unwrap_or_else(|| serde_json::json!({}));

    match sqlx::query_as::<_, UserSession>(
        r#"INSERT INTO user_sessions (user_id, dialog_type, dialog_state, dialog_data)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (user_id) DO UPDATE SET
             dialog_type = EXCLUDED.dialog_type,
             dialog_state = EXCLUDED.dialog_state,
             dialog_data = EXCLUDED.dialog_data,
             updated_at = NOW()
           RETURNING *"#,
    )
    .bind(data.user_id)
    .bind(&dialog_type)
    .bind(&dialog_state)
    .bind(&dialog_data)
    .fetch_one(pool.get_ref())
    .await
    {
        Ok(session) => HttpResponse::Ok().json(session),
        Err(e) => {
            tracing::error!("Failed to set session state: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// POST /api/users/sessions/clear_state/
pub async fn clear_session_state(
    pool: web::Data<PgPool>,
    body: web::Json<ClearSessionRequest>,
) -> HttpResponse {
    match sqlx::query("DELETE FROM user_sessions WHERE user_id = $1")
        .bind(body.user_id)
        .execute(pool.get_ref())
        .await
    {
        Ok(_) => HttpResponse::Ok().json(serde_json::json!({"message": "Session cleared"})),
        Err(e) => {
            tracing::error!("Failed to clear session: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}
