use wasm_bindgen::prelude::*;

/// Validate phone number format (Russian phone number)
#[wasm_bindgen]
pub fn validate_phone(phone: &str) -> bool {
    let cleaned: String = phone.chars().filter(|c| c.is_ascii_digit() || *c == '+').collect();
    if cleaned.is_empty() {
        return true; // phone is optional
    }
    let re_pattern = cleaned.starts_with('+') && cleaned.len() >= 11 && cleaned.len() <= 16;
    let digits_only = cleaned.trim_start_matches('+');
    re_pattern && digits_only.chars().all(|c| c.is_ascii_digit())
}

/// Validate email format
#[wasm_bindgen]
pub fn validate_email(email: &str) -> bool {
    if email.is_empty() {
        return true; // email is optional
    }
    let parts: Vec<&str> = email.split('@').collect();
    if parts.len() != 2 {
        return false;
    }
    let local = parts[0];
    let domain = parts[1];
    !local.is_empty() && domain.contains('.') && domain.len() > 2
}

/// Calculate procurement progress percentage
#[wasm_bindgen]
pub fn calculate_progress(current_amount: f64, target_amount: f64) -> i32 {
    if target_amount <= 0.0 {
        return 0;
    }
    let progress = (current_amount / target_amount * 100.0) as i32;
    progress.min(100).max(0)
}

/// Calculate days remaining until deadline
#[wasm_bindgen]
pub fn days_until(deadline_ms: f64) -> i32 {
    let now_ms = js_sys::Date::now();
    let diff_ms = deadline_ms - now_ms;
    let days = (diff_ms / 86_400_000.0) as i32;
    days.max(0)
}

/// Format currency amount (Russian rubles)
#[wasm_bindgen]
pub fn format_currency(amount: f64) -> String {
    let integer = amount.trunc() as i64;
    let fraction = ((amount.fract() * 100.0).round() as i64).abs();

    // Format with thousands separator
    let int_str = integer.to_string();
    let mut formatted = String::new();
    for (i, ch) in int_str.chars().rev().enumerate() {
        if i > 0 && i % 3 == 0 && ch != '-' {
            formatted.push(' ');
        }
        formatted.push(ch);
    }
    let formatted: String = formatted.chars().rev().collect();

    if fraction > 0 {
        format!("{},{:02} \u{20bd}", formatted, fraction)
    } else {
        format!("{} \u{20bd}", formatted)
    }
}

/// Format relative time in Russian
#[wasm_bindgen]
pub fn format_relative_time(timestamp_ms: f64) -> String {
    let now_ms = js_sys::Date::now();
    let diff_sec = ((now_ms - timestamp_ms) / 1000.0) as i64;

    if diff_sec < 60 {
        return "только что".to_string();
    }
    if diff_sec < 3600 {
        let mins = diff_sec / 60;
        return format!("{} мин. назад", mins);
    }
    if diff_sec < 86400 {
        let hours = diff_sec / 3600;
        return format!("{} ч. назад", hours);
    }
    let days = diff_sec / 86400;
    if days == 1 {
        return "вчера".to_string();
    }
    format!("{} дн. назад", days)
}

/// Validate procurement form data
/// Returns JSON string with validation errors (empty object if valid)
#[wasm_bindgen]
pub fn validate_procurement_form(title: &str, description: &str, city: &str, target_amount: f64, deadline_ms: f64) -> String {
    let mut errors: Vec<(&str, &str)> = Vec::new();

    if title.trim().is_empty() {
        errors.push(("title", "Название обязательно"));
    } else if title.len() > 200 {
        errors.push(("title", "Название не должно превышать 200 символов"));
    }

    if description.trim().is_empty() {
        errors.push(("description", "Описание обязательно"));
    }

    if city.trim().is_empty() {
        errors.push(("city", "Город обязателен"));
    }

    if target_amount <= 0.0 {
        errors.push(("target_amount", "Целевая сумма должна быть положительной"));
    }

    let now_ms = js_sys::Date::now();
    if deadline_ms <= now_ms {
        errors.push(("deadline", "Дедлайн должен быть в будущем"));
    }

    if errors.is_empty() {
        "{}".to_string()
    } else {
        let mut result = String::from("{");
        for (i, (key, msg)) in errors.iter().enumerate() {
            if i > 0 {
                result.push(',');
            }
            result.push_str(&format!("\"{}\":\"{}\"", key, msg));
        }
        result.push('}');
        result
    }
}

/// Generate unique platform user ID for websocket users
#[wasm_bindgen]
pub fn generate_platform_user_id() -> String {
    let timestamp = js_sys::Date::now() as u64;
    let random = (js_sys::Math::random() * 1_000_000_000.0) as u64;
    format!("web_{}_{}", timestamp, random)
}
