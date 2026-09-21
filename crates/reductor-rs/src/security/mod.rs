use regex::Regex;
use std::sync::LazyLock;
use crate::domain::{ConfidentialityLevel, ScoredChunk};

static API_KEY_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)(sk-[a-zA-Z0-9_-]{20,}|AIza[0-9A-Za-z-_]{35}|ghp_[0-9a-zA-Z]{36}|xox[baprs]-[0-9a-zA-Z]{10,48})"#).unwrap()
});

static BEARER_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)Bearer\s+([a-zA-Z0-9_\-\.]{20,})"#).unwrap()
});

static CONNECTION_STRING_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)(postgres|mysql|mongodb|redis)://([^:]+):([^@]+)@"#).unwrap()
});

static INTERNAL_IP_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"#).unwrap()
});

static EMAIL_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"#).unwrap()
});

pub struct SecuritySanitizer;

impl SecuritySanitizer {
    /// Sanitiza texto mascarando chaves, senhas, IPs internos e PII
    pub fn sanitize(text: &str) -> String {
        let mut sanitized = text.to_string();

        sanitized = API_KEY_REGEX.replace_all(&sanitized, "[REDACTED_API_KEY]").to_string();
        sanitized = BEARER_REGEX.replace_all(&sanitized, "Bearer [REDACTED_TOKEN]").to_string();
        sanitized = CONNECTION_STRING_REGEX.replace_all(&sanitized, "$1://$2:[REDACTED_PASSWORD]@").to_string();
        sanitized = INTERNAL_IP_REGEX.replace_all(&sanitized, "[INTERNAL_IP]").to_string();
        sanitized = EMAIL_REGEX.replace_all(&sanitized, "[REDACTED_EMAIL]").to_string();

        sanitized
    }
}

pub struct ConfidentialityGuard;

impl ConfidentialityGuard {
    /// Determina o nível mais restritivo entre os trechos recuperados
    pub fn determine_effective_level(chunks: &[ScoredChunk]) -> ConfidentialityLevel {
        let mut max_level = ConfidentialityLevel::Public;
        for sc in chunks {
            match sc.chunk.confidentiality {
                ConfidentialityLevel::Confidential => return ConfidentialityLevel::Confidential,
                ConfidentialityLevel::Internal => max_level = ConfidentialityLevel::Internal,
                ConfidentialityLevel::Public => {}
            }
        }
        max_level
    }

    /// Verifica se é permitido despachar o contexto para uma LLM em nuvem (ex: Gemini)
    pub fn is_cloud_allowed(level: &ConfidentialityLevel) -> bool {
        matches!(level, ConfidentialityLevel::Public)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitization_api_key_and_ip() {
        let raw = "Connect to redis://user:secret123@192.168.1.50:6379 using sk-abcdef123456789012345678";
        let sanitized = SecuritySanitizer::sanitize(raw);
        assert!(!sanitized.contains("secret123"));
        assert!(!sanitized.contains("sk-abcdef123456789012345678"));
        assert!(!sanitized.contains("192.168.1.50"));
        assert!(sanitized.contains("[REDACTED_PASSWORD]"));
        assert!(sanitized.contains("[REDACTED_API_KEY]"));
        assert!(sanitized.contains("[INTERNAL_IP]"));
    }

    #[test]
    fn test_confidentiality_cloud_check() {
        assert!(ConfidentialityGuard::is_cloud_allowed(&ConfidentialityLevel::Public));
        assert!(!ConfidentialityGuard::is_cloud_allowed(&ConfidentialityLevel::Internal));
        assert!(!ConfidentialityGuard::is_cloud_allowed(&ConfidentialityLevel::Confidential));
    }
}
