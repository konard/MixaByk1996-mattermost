use actix_web::{web, HttpResponse};
use sqlx::PgPool;

use crate::models::procurement::*;

/// GET /api/procurements/
pub async fn list_procurements(
    pool: web::Data<PgPool>,
    query: web::Query<ProcurementQuery>,
) -> HttpResponse {
    // Build query dynamically based on provided filters
    let mut conditions: Vec<String> = Vec::new();
    let mut bind_values: Vec<String> = Vec::new();
    let mut idx = 0;

    if let Some(ref status) = query.status {
        idx += 1;
        conditions.push(format!("status = ${}", idx));
        bind_values.push(status.clone());
    }
    if let Some(ref city) = query.city {
        idx += 1;
        conditions.push(format!("city = ${}", idx));
        bind_values.push(city.clone());
    }
    if let Some(category_id) = query.category_id {
        idx += 1;
        conditions.push(format!("category_id = ${}", idx));
        bind_values.push(category_id.to_string());
    }
    if let Some(organizer_id) = query.organizer_id {
        idx += 1;
        conditions.push(format!("organizer_id = ${}", idx));
        bind_values.push(organizer_id.to_string());
    }

    let where_clause = if conditions.is_empty() {
        String::new()
    } else {
        format!(" WHERE {}", conditions.join(" AND "))
    };

    let sql = format!(
        "SELECT * FROM procurements{} ORDER BY created_at DESC",
        where_clause
    );

    let mut q = sqlx::query_as::<_, Procurement>(&sql);
    for val in &bind_values {
        q = q.bind(val);
    }

    let procurements = q.fetch_all(pool.get_ref()).await;

    match procurements {
        Ok(procs) => {
            let mut responses = Vec::new();
            for p in procs {
                let count: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM participants WHERE procurement_id = $1 AND is_active = true",
                )
                .bind(p.id)
                .fetch_one(pool.get_ref())
                .await
                .unwrap_or(0);
                responses.push(p.to_response(count));
            }
            HttpResponse::Ok().json(serde_json::json!({"results": responses}))
        }
        Err(e) => {
            tracing::error!("Failed to fetch procurements: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// POST /api/procurements/
pub async fn create_procurement(
    pool: web::Data<PgPool>,
    body: web::Json<CreateProcurement>,
) -> HttpResponse {
    let data = body.into_inner();
    let delivery_address = data.delivery_address.unwrap_or_default();
    let unit = data.unit.unwrap_or_else(|| "units".to_string());
    let status = data.status.unwrap_or_else(|| "draft".to_string());
    let image_url = data.image_url.unwrap_or_default();

    match sqlx::query_as::<_, Procurement>(
        r#"INSERT INTO procurements (title, description, category_id, organizer_id, city, delivery_address,
            target_amount, stop_at_amount, unit, price_per_unit, status, deadline, payment_deadline, image_url)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
           RETURNING *"#,
    )
    .bind(&data.title)
    .bind(&data.description)
    .bind(data.category_id)
    .bind(data.organizer_id)
    .bind(&data.city)
    .bind(&delivery_address)
    .bind(data.target_amount)
    .bind(data.stop_at_amount)
    .bind(&unit)
    .bind(data.price_per_unit)
    .bind(&status)
    .bind(data.deadline)
    .bind(data.payment_deadline)
    .bind(&image_url)
    .fetch_one(pool.get_ref())
    .await
    {
        Ok(proc) => HttpResponse::Created().json(proc.to_response(0)),
        Err(e) => {
            tracing::error!("Failed to create procurement: {}", e);
            HttpResponse::BadRequest().json(serde_json::json!({"error": format!("{}", e)}))
        }
    }
}

/// GET /api/procurements/{id}/
pub async fn get_procurement(pool: web::Data<PgPool>, path: web::Path<i32>) -> HttpResponse {
    let proc_id = path.into_inner();
    match sqlx::query_as::<_, Procurement>("SELECT * FROM procurements WHERE id = $1")
        .bind(proc_id)
        .fetch_optional(pool.get_ref())
        .await
    {
        Ok(Some(proc)) => {
            let count: i64 = sqlx::query_scalar(
                "SELECT COUNT(*) FROM participants WHERE procurement_id = $1 AND is_active = true",
            )
            .bind(proc_id)
            .fetch_one(pool.get_ref())
            .await
            .unwrap_or(0);
            HttpResponse::Ok().json(proc.to_response(count))
        }
        Ok(None) => HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."})),
        Err(e) => {
            tracing::error!("Failed to fetch procurement: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// POST /api/procurements/{id}/join/
pub async fn join_procurement(
    pool: web::Data<PgPool>,
    path: web::Path<i32>,
    body: web::Json<JoinProcurement>,
) -> HttpResponse {
    let proc_id = path.into_inner();
    let data = body.into_inner();
    let quantity = data.quantity.unwrap_or(rust_decimal::Decimal::ONE);
    let notes = data.notes.unwrap_or_default();

    let user_id = match data.user_id {
        Some(id) => id,
        None => {
            return HttpResponse::BadRequest()
                .json(serde_json::json!({"error": "user_id is required"}))
        }
    };

    // Check procurement can be joined
    let proc = match sqlx::query_as::<_, Procurement>("SELECT * FROM procurements WHERE id = $1")
        .bind(proc_id)
        .fetch_optional(pool.get_ref())
        .await
    {
        Ok(Some(p)) => p,
        Ok(None) => {
            return HttpResponse::NotFound().json(serde_json::json!({"detail": "Not found."}))
        }
        Err(e) => {
            tracing::error!("Failed to fetch procurement: {}", e);
            return HttpResponse::InternalServerError()
                .json(serde_json::json!({"error": "Database error"}));
        }
    };

    if proc.status != "active" {
        return HttpResponse::BadRequest()
            .json(serde_json::json!({"error": "Procurement is not active"}));
    }

    match sqlx::query_as::<_, Participant>(
        r#"INSERT INTO participants (procurement_id, user_id, quantity, amount, notes)
           VALUES ($1, $2, $3, $4, $5)
           RETURNING *"#,
    )
    .bind(proc_id)
    .bind(user_id)
    .bind(quantity)
    .bind(data.amount)
    .bind(&notes)
    .fetch_one(pool.get_ref())
    .await
    {
        Ok(participant) => {
            // Update procurement current amount
            let _ = sqlx::query(
                "UPDATE procurements SET current_amount = (SELECT COALESCE(SUM(amount), 0) FROM participants WHERE procurement_id = $1 AND is_active = true), updated_at = NOW() WHERE id = $1",
            )
            .bind(proc_id)
            .execute(pool.get_ref())
            .await;

            HttpResponse::Created().json(participant)
        }
        Err(e) => {
            tracing::error!("Failed to join procurement: {}", e);
            if e.to_string().contains("unique") || e.to_string().contains("duplicate") {
                HttpResponse::BadRequest()
                    .json(serde_json::json!({"error": "Already joined this procurement"}))
            } else {
                HttpResponse::BadRequest()
                    .json(serde_json::json!({"error": format!("{}", e)}))
            }
        }
    }
}

/// POST /api/procurements/{id}/leave/
pub async fn leave_procurement(
    pool: web::Data<PgPool>,
    path: web::Path<i32>,
    body: web::Json<serde_json::Value>,
) -> HttpResponse {
    let proc_id = path.into_inner();
    let user_id = body.get("user_id").and_then(|v| v.as_i64()).unwrap_or(0);

    if user_id == 0 {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "user_id is required"}));
    }

    match sqlx::query(
        "UPDATE participants SET is_active = false, updated_at = NOW() WHERE procurement_id = $1 AND user_id = $2",
    )
    .bind(proc_id)
    .bind(user_id as i32)
    .execute(pool.get_ref())
    .await
    {
        Ok(result) => {
            if result.rows_affected() > 0 {
                // Update procurement current amount
                let _ = sqlx::query(
                    "UPDATE procurements SET current_amount = (SELECT COALESCE(SUM(amount), 0) FROM participants WHERE procurement_id = $1 AND is_active = true), updated_at = NOW() WHERE id = $1",
                )
                .bind(proc_id)
                .execute(pool.get_ref())
                .await;

                HttpResponse::Ok().json(serde_json::json!({"message": "Left procurement", "procurement_id": proc_id}))
            } else {
                HttpResponse::NotFound().json(serde_json::json!({"error": "Not a participant of this procurement"}))
            }
        }
        Err(e) => {
            tracing::error!("Failed to leave procurement: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// GET /api/procurements/user/{user_id}/
pub async fn get_user_procurements(
    pool: web::Data<PgPool>,
    path: web::Path<i32>,
) -> HttpResponse {
    let user_id = path.into_inner();

    let organized = sqlx::query_as::<_, Procurement>(
        "SELECT * FROM procurements WHERE organizer_id = $1 ORDER BY created_at DESC",
    )
    .bind(user_id)
    .fetch_all(pool.get_ref())
    .await;

    let participating_ids: Vec<i32> = sqlx::query_scalar(
        "SELECT procurement_id FROM participants WHERE user_id = $1 AND is_active = true",
    )
    .bind(user_id)
    .fetch_all(pool.get_ref())
    .await
    .unwrap_or_default();

    let participating = if participating_ids.is_empty() {
        Ok(vec![])
    } else {
        sqlx::query_as::<_, Procurement>(
            "SELECT * FROM procurements WHERE id = ANY($1) ORDER BY created_at DESC",
        )
        .bind(&participating_ids)
        .fetch_all(pool.get_ref())
        .await
    };

    match (organized, participating) {
        (Ok(org), Ok(part)) => {
            let org_responses: Vec<_> = org
                .into_iter()
                .map(|p| p.to_response(0))
                .collect();
            let part_responses: Vec<_> = part
                .into_iter()
                .map(|p| p.to_response(0))
                .collect();
            HttpResponse::Ok().json(serde_json::json!({
                "organized": org_responses,
                "participating": part_responses
            }))
        }
        (Err(e), _) | (_, Err(e)) => {
            tracing::error!("Failed to fetch user procurements: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}

/// POST /api/procurements/{id}/check_access/
pub async fn check_procurement_access(
    pool: web::Data<PgPool>,
    path: web::Path<i32>,
    body: web::Json<serde_json::Value>,
) -> HttpResponse {
    let proc_id = path.into_inner();
    let user_id = body.get("user_id").and_then(|v| v.as_i64()).unwrap_or(0);

    if user_id == 0 {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "user_id is required"}));
    }

    // Check if user is organizer or active participant
    let is_organizer: bool = sqlx::query_scalar(
        "SELECT EXISTS(SELECT 1 FROM procurements WHERE id = $1 AND organizer_id = $2)",
    )
    .bind(proc_id)
    .bind(user_id as i32)
    .fetch_one(pool.get_ref())
    .await
    .unwrap_or(false);

    let is_participant: bool = sqlx::query_scalar(
        "SELECT EXISTS(SELECT 1 FROM participants WHERE procurement_id = $1 AND user_id = $2 AND is_active = true)",
    )
    .bind(proc_id)
    .bind(user_id as i32)
    .fetch_one(pool.get_ref())
    .await
    .unwrap_or(false);

    if is_organizer || is_participant {
        HttpResponse::Ok().json(serde_json::json!({"access": true}))
    } else {
        HttpResponse::Forbidden().json(serde_json::json!({"access": false}))
    }
}

/// GET /api/procurements/categories/
pub async fn list_categories(pool: web::Data<PgPool>) -> HttpResponse {
    match sqlx::query_as::<_, Category>(
        "SELECT * FROM categories WHERE is_active = true ORDER BY name",
    )
    .fetch_all(pool.get_ref())
    .await
    {
        Ok(categories) => HttpResponse::Ok().json(categories),
        Err(e) => {
            tracing::error!("Failed to fetch categories: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Database error"}))
        }
    }
}
