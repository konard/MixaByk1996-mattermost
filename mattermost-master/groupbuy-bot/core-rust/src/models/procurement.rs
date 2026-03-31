use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Category {
    pub id: i32,
    pub name: String,
    pub description: String,
    pub parent_id: Option<i32>,
    pub icon: String,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Procurement {
    pub id: i32,
    pub title: String,
    pub description: String,
    pub category_id: Option<i32>,
    pub organizer_id: i32,
    pub supplier_id: Option<i32>,
    pub city: String,
    pub delivery_address: String,
    pub target_amount: Decimal,
    pub current_amount: Decimal,
    pub stop_at_amount: Option<Decimal>,
    pub unit: String,
    pub price_per_unit: Option<Decimal>,
    pub status: String,
    pub deadline: DateTime<Utc>,
    pub payment_deadline: Option<DateTime<Utc>>,
    pub image_url: String,
    pub is_featured: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
pub struct ProcurementResponse {
    pub id: i32,
    pub title: String,
    pub description: String,
    pub category_id: Option<i32>,
    pub organizer_id: i32,
    pub supplier_id: Option<i32>,
    pub city: String,
    pub delivery_address: String,
    pub target_amount: Decimal,
    pub current_amount: Decimal,
    pub stop_at_amount: Option<Decimal>,
    pub unit: String,
    pub price_per_unit: Option<Decimal>,
    pub status: String,
    pub status_display: String,
    pub deadline: DateTime<Utc>,
    pub payment_deadline: Option<DateTime<Utc>>,
    pub image_url: String,
    pub is_featured: bool,
    pub progress: i32,
    pub participant_count: i64,
    pub days_left: i64,
    pub can_join: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Procurement {
    pub fn to_response(self, participant_count: i64) -> ProcurementResponse {
        let status_display = match self.status.as_str() {
            "draft" => "Draft",
            "active" => "Active",
            "stopped" => "Stopped",
            "payment" => "Payment in Progress",
            "completed" => "Completed",
            "cancelled" => "Cancelled",
            other => other,
        }
        .to_string();

        let progress = if self.target_amount.is_zero() {
            0
        } else {
            let pct = (self.current_amount / self.target_amount * Decimal::from(100))
                .to_string()
                .parse::<i32>()
                .unwrap_or(0);
            pct.min(100)
        };

        let days_left = (self.deadline - Utc::now()).num_days().max(0);

        let can_join = self.status == "active"
            && self.deadline > Utc::now()
            && self
                .stop_at_amount
                .map_or(true, |stop| self.current_amount < stop);

        ProcurementResponse {
            id: self.id,
            title: self.title,
            description: self.description,
            category_id: self.category_id,
            organizer_id: self.organizer_id,
            supplier_id: self.supplier_id,
            city: self.city,
            delivery_address: self.delivery_address,
            target_amount: self.target_amount,
            current_amount: self.current_amount,
            stop_at_amount: self.stop_at_amount,
            unit: self.unit,
            price_per_unit: self.price_per_unit,
            status: self.status,
            status_display,
            deadline: self.deadline,
            payment_deadline: self.payment_deadline,
            image_url: self.image_url,
            is_featured: self.is_featured,
            progress,
            participant_count,
            days_left,
            can_join,
            created_at: self.created_at,
            updated_at: self.updated_at,
        }
    }
}

#[derive(Debug, Deserialize)]
pub struct CreateProcurement {
    pub title: String,
    pub description: String,
    pub category_id: Option<i32>,
    pub organizer_id: i32,
    pub city: String,
    pub delivery_address: Option<String>,
    pub target_amount: Decimal,
    pub stop_at_amount: Option<Decimal>,
    pub unit: Option<String>,
    pub price_per_unit: Option<Decimal>,
    pub status: Option<String>,
    pub deadline: DateTime<Utc>,
    pub payment_deadline: Option<DateTime<Utc>>,
    pub image_url: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ProcurementQuery {
    pub status: Option<String>,
    pub city: Option<String>,
    pub category_id: Option<i32>,
    pub organizer_id: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Participant {
    pub id: i32,
    pub procurement_id: i32,
    pub user_id: i32,
    pub quantity: Decimal,
    pub amount: Decimal,
    pub status: String,
    pub notes: String,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct JoinProcurement {
    pub user_id: Option<i32>,
    pub amount: Decimal,
    pub quantity: Option<Decimal>,
    pub notes: Option<String>,
}
