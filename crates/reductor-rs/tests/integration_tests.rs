use reductor_rs::algorithms::AdaptiveRRFEngine;
use reductor_rs::domain::{Book, BookChunk, ConfidentialityLevel, DocumentFormat, ScoredChunk};
use reductor_rs::extractors::DocumentExtractor;
use reductor_rs::security::{ConfidentialityGuard, SecuritySanitizer};
use reductor_rs::vector_store::{cosine_similarity, EmbeddedVectorStore};
use tempfile::tempdir;

#[test]
fn test_security_sanitization_rules() {
    let input = "System using apiKey=sk-abcdef0123456789abcdef0123456789 at 192.168.0.15 with postgres://admin:superSecretPassword123@10.0.0.1:5432/db";
    let sanitized = SecuritySanitizer::sanitize(input);

    assert!(!sanitized.contains("sk-abcdef0123456789abcdef0123456789"));
    assert!(!sanitized.contains("superSecretPassword123"));
    assert!(!sanitized.contains("192.168.0.15"));
    assert!(!sanitized.contains("10.0.0.1"));

    assert!(sanitized.contains("[REDACTED_API_KEY]"));
    assert!(sanitized.contains("[REDACTED_PASSWORD]"));
    assert!(sanitized.contains("[INTERNAL_IP]"));
}

#[test]
fn test_confidentiality_routing_rules() {
    assert!(ConfidentialityGuard::is_cloud_allowed(&ConfidentialityLevel::Public));
    assert!(!ConfidentialityGuard::is_cloud_allowed(&ConfidentialityLevel::Internal));
    assert!(!ConfidentialityGuard::is_cloud_allowed(&ConfidentialityLevel::Confidential));
}

#[test]
fn test_cosine_similarity_calculation() {
    let vec_a = vec![1.0, 0.0, 0.0];
    let vec_b = vec![1.0, 0.0, 0.0];
    let vec_c = vec![0.0, 1.0, 0.0];

    assert!((cosine_similarity(&vec_a, &vec_b) - 1.0).abs() < 1e-5);
    assert!((cosine_similarity(&vec_a, &vec_c) - 0.0).abs() < 1e-5);
}

#[tokio::test]
async fn test_embedded_vector_store_persistence_and_search() {
    let dir = tempdir().unwrap();
    let store = EmbeddedVectorStore::new(dir.path());

    let book = Book {
        id: "book_test_1".to_string(),
        title: "Test Book on Rust Concurrency".to_string(),
        file_path: "test.pdf".to_string(),
        file_hash: "abcd1234hash".to_string(),
        format: DocumentFormat::Pdf,
        confidentiality: ConfidentialityLevel::Public,
        total_chunks: 2,
        total_tokens: 300,
    };

    let chunks = vec![
        BookChunk {
            id: "book_test_1_c0".to_string(),
            book_id: "book_test_1".to_string(),
            book_title: "Test Book on Rust Concurrency".to_string(),
            content: "Atomics and locks in Rust provide memory safety.".to_string(),
            page_number: Some(10),
            chapter: Some("Chapter 1".to_string()),
            token_count: 150,
            confidentiality: ConfidentialityLevel::Public,
            embedding: Some(vec![0.9, 0.1, 0.0]),
        },
        BookChunk {
            id: "book_test_1_c1".to_string(),
            book_id: "book_test_1".to_string(),
            book_title: "Test Book on Rust Concurrency".to_string(),
            content: "Channels in Go pass messages between goroutines.".to_string(),
            page_number: Some(20),
            chapter: Some("Chapter 2".to_string()),
            token_count: 150,
            confidentiality: ConfidentialityLevel::Public,
            embedding: Some(vec![0.0, 0.1, 0.9]),
        },
    ];

    store.add_book_with_chunks(book, chunks).await.unwrap();

    // Busca por vetor similar a Rust atomics
    let query_vector = vec![0.85, 0.15, 0.0];
    let results = store.search_similar(&query_vector, 5, 0.5, None).await;

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].chunk.id, "book_test_1_c0");
    assert!(results[0].similarity_score > 0.9);
}

#[test]
fn test_adaptive_rrf_and_elbow_cutoff() {
    let dummy_chunk = |id: &str, title: &str, score: f32| ScoredChunk {
        chunk: BookChunk {
            id: id.to_string(),
            book_id: "b1".to_string(),
            book_title: title.to_string(),
            content: "Sample content".to_string(),
            page_number: Some(1),
            chapter: None,
            token_count: 200,
            confidentiality: ConfidentialityLevel::Public,
            embedding: None,
        },
        similarity_score: score,
        rank_position: 1,
    };

    let scored = vec![
        dummy_chunk("c1", "Book A", 0.98),
        dummy_chunk("c2", "Book A", 0.95),
        dummy_chunk("c3", "Book B", 0.92),
        dummy_chunk("c4", "Book C", 0.50), // Queda abrupta (>0.22)
        dummy_chunk("c5", "Book D", 0.40),
    ];

    let budget = AdaptiveRRFEngine::apply_elbow_and_budget(scored, 2500, 0.35, 0.22);
    // Deve ter cortado c4 e c5 devido à queda de relevância
    assert_eq!(budget.selected_chunks.len(), 3);
    assert!(budget.total_tokens_used <= 2500);
    assert!(budget.reduction_percentage > 90.0);
}

#[test]
fn test_document_chunking_with_overlap() {
    let book = Book {
        id: "book_test".to_string(),
        title: "Architecture Guide".to_string(),
        file_path: "arch.md".to_string(),
        file_hash: "hash123".to_string(),
        format: DocumentFormat::Markdown,
        confidentiality: ConfidentialityLevel::Public,
        total_chunks: 0,
        total_tokens: 0,
    };

    let text = (1..=100).map(|i| format!("word{}", i)).collect::<Vec<_>>().join(" ");
    let pages = vec![(Some(1), text)];

    let chunks = DocumentExtractor::chunk_document(&book, &pages, 30, 10);
    assert!(chunks.len() >= 4);
    assert_eq!(chunks[0].book_id, "book_test");
    assert!(chunks[0].token_count > 0);
}
