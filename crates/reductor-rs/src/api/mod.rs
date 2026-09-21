use std::sync::Arc;
use axum::{
    extract::State,
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use tower_http::cors::{Any, CorsLayer};

use crate::algorithms::AdaptiveRRFEngine;
use crate::embeddings::OllamaEmbeddingClient;
use crate::llm::LLMService;
use crate::vector_store::EmbeddedVectorStore;

#[derive(Clone)]
pub struct AppState {
    pub vector_store: Arc<EmbeddedVectorStore>,
    pub embedding_client: Arc<OllamaEmbeddingClient>,
    pub llm_service: Arc<LLMService>,
}

#[derive(Deserialize)]
pub struct QueryApiRequest {
    pub query: String,
    pub book_filter: Option<String>,
    pub deep: Option<bool>,
    pub only_context: Option<bool>,
    pub max_tokens: Option<usize>,
}

#[derive(Serialize)]
pub struct QueryApiResponse {
    pub query: String,
    pub response: String,
    pub tokens_used: usize,
    pub tokens_saved: usize,
    pub reduction_percentage: f32,
    pub sources: Vec<QuerySourceItem>,
}

#[derive(Serialize)]
pub struct QuerySourceItem {
    pub book_title: String,
    pub page: Option<usize>,
    pub similarity: f32,
}

pub fn create_router(state: AppState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .route("/health", get(health_check))
        .route("/api/v1/books", get(list_books))
        .route("/api/v1/query", post(query_handler))
        .layer(cors)
        .with_state(state)
}

async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "ok",
        "service": "ReductorPrompt-Rust",
        "version": "0.1.0"
    }))
}

async fn list_books(State(state): State<AppState>) -> impl IntoResponse {
    let books = state.vector_store.list_books().await;
    Json(serde_json::json!({
        "books": books,
        "total": books.len()
    }))
}

async fn query_handler(
    State(state): State<AppState>,
    Json(payload): Json<QueryApiRequest>,
) -> Result<Json<QueryApiResponse>, (StatusCode, String)> {
    let query_vec = state.embedding_client.embed_single(&payload.query).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e))?;

    let scored = state.vector_store.search_similar(
        &query_vec,
        6,
        0.25,
        payload.book_filter.as_deref(),
    ).await;

    let budget = AdaptiveRRFEngine::apply_elbow_and_budget(
        scored,
        payload.max_tokens.unwrap_or(2500),
        0.35,
        0.22,
    );

    let sources: Vec<QuerySourceItem> = budget.selected_chunks.iter().map(|sc| QuerySourceItem {
        book_title: sc.chunk.book_title.clone(),
        page: sc.chunk.page_number,
        similarity: sc.similarity_score,
    }).collect();

    let response_text = if payload.only_context.unwrap_or(false) {
        let mut ctx = String::new();
        for (i, sc) in budget.selected_chunks.iter().enumerate() {
            ctx.push_str(&format!("[{}] {} (Pág {:?}): {}\n\n", i + 1, sc.chunk.book_title, sc.chunk.page_number, sc.chunk.content));
        }
        ctx
    } else {
        state.llm_service.generate_rag_response(
            &payload.query,
            &budget.selected_chunks,
            payload.deep.unwrap_or(false),
        ).await.map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e))?
    };

    Ok(Json(QueryApiResponse {
        query: payload.query,
        response: response_text,
        tokens_used: budget.total_tokens_used,
        tokens_saved: budget.total_tokens_saved,
        reduction_percentage: budget.reduction_percentage,
        sources,
    }))
}
