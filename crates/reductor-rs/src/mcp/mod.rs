use std::io::{self, BufRead, Write};
use std::sync::Arc;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use crate::algorithms::AdaptiveRRFEngine;
use crate::embeddings::OllamaEmbeddingClient;
use crate::llm::LLMService;
use crate::vector_store::EmbeddedVectorStore;

#[derive(Deserialize)]
#[allow(dead_code)]
struct JsonRpcRequest {
    jsonrpc: String,
    id: Option<Value>,
    method: String,
    params: Option<Value>,
}

#[derive(Serialize)]
struct JsonRpcResponse {
    jsonrpc: &'static str,
    id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<JsonRpcError>,
}

#[derive(Serialize)]
struct JsonRpcError {
    code: i32,
    message: String,
}

pub struct McpServer {
    vector_store: Arc<EmbeddedVectorStore>,
    embedding_client: Arc<OllamaEmbeddingClient>,
    llm_service: Arc<LLMService>,
}

impl McpServer {
    pub fn new(
        vector_store: Arc<EmbeddedVectorStore>,
        embedding_client: Arc<OllamaEmbeddingClient>,
        llm_service: Arc<LLMService>,
    ) -> Self {
        Self {
            vector_store,
            embedding_client,
            llm_service,
        }
    }

    /// Executa o loop principal de processamento do protocolo MCP via Stdio
    pub async fn run_stdio(&self) {
        let stdin = io::stdin();
        let mut stdout = io::stdout();

        for line in stdin.lock().lines() {
            let line = match line {
                Ok(l) => l,
                Err(_) => break,
            };

            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            if let Ok(req) = serde_json::from_str::<JsonRpcRequest>(trimmed) {
                let id = req.id.unwrap_or(Value::Null);
                let response = self.handle_rpc_method(&req.method, req.params, id).await;
                if let Ok(resp_json) = serde_json::to_string(&response) {
                    let _ = writeln!(stdout, "{}", resp_json);
                    let _ = stdout.flush();
                }
            }
        }
    }

    async fn handle_rpc_method(&self, method: &str, params: Option<Value>, id: Value) -> JsonRpcResponse {
        match method {
            "initialize" => JsonRpcResponse {
                jsonrpc: "2.0",
                id,
                result: Some(serde_json::json!({
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "reductor-rs",
                        "version": "0.1.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                })),
                error: None,
            },
            "tools/list" => JsonRpcResponse {
                jsonrpc: "2.0",
                id,
                result: Some(serde_json::json!({
                    "tools": [
                        {
                            "name": "search_books",
                            "description": "Consulta a biblioteca técnica com RAG semântico e corte adaptativo de tokens (>95% de economia).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": { "type": "string", "description": "A pergunta técnica" },
                                    "book_filter": { "type": "string", "description": "Filtro opcional por nome do livro" },
                                    "deep": { "type": "boolean", "description": "Ativa raciocínio profundo" }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "list_books",
                            "description": "Lista todos os livros técnicos indexados na base local.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                })),
                error: None,
            },
            "tools/call" => {
                let tool_name = params.as_ref()
                    .and_then(|p| p.get("name"))
                    .and_then(|n| n.as_str())
                    .unwrap_or("");

                let arguments = params.as_ref()
                    .and_then(|p| p.get("arguments"))
                    .cloned()
                    .unwrap_or(serde_json::json!({}));

                match tool_name {
                    "search_books" => {
                        let query = arguments.get("query").and_then(|q| q.as_str()).unwrap_or("");
                        let book_filter = arguments.get("book_filter").and_then(|b| b.as_str());
                        let deep = arguments.get("deep").and_then(|d| d.as_bool()).unwrap_or(false);

                        match self.embedding_client.embed_single(query).await {
                            Ok(query_vec) => {
                                let scored = self.vector_store.search_similar(&query_vec, 6, 0.25, book_filter).await;
                                let budget = AdaptiveRRFEngine::apply_elbow_and_budget(scored, 2500, 0.35, 0.22);
                                match self.llm_service.generate_rag_response(query, &budget.selected_chunks, deep).await {
                                    Ok(ans) => JsonRpcResponse {
                                        jsonrpc: "2.0",
                                        id,
                                        result: Some(serde_json::json!({
                                            "content": [{ "type": "text", "text": ans }],
                                            "tokens_used": budget.total_tokens_used,
                                            "tokens_saved": budget.total_tokens_saved,
                                            "reduction_percentage": budget.reduction_percentage
                                        })),
                                        error: None,
                                    },
                                    Err(e) => JsonRpcResponse {
                                        jsonrpc: "2.0",
                                        id,
                                        result: None,
                                        error: Some(JsonRpcError { code: -32603, message: e }),
                                    },
                                }
                            }
                            Err(e) => JsonRpcResponse {
                                jsonrpc: "2.0",
                                id,
                                result: None,
                                error: Some(JsonRpcError { code: -32603, message: e }),
                            },
                        }
                    }
                    "list_books" => {
                        let books = self.vector_store.list_books().await;
                        JsonRpcResponse {
                            jsonrpc: "2.0",
                            id,
                            result: Some(serde_json::json!({ "books": books })),
                            error: None,
                        }
                    }
                    _ => JsonRpcResponse {
                        jsonrpc: "2.0",
                        id,
                        result: None,
                        error: Some(JsonRpcError { code: -32601, message: format!("Ferramenta desconhecida: {}", tool_name) }),
                    },
                }
            }
            _ => JsonRpcResponse {
                jsonrpc: "2.0",
                id,
                result: None,
                error: Some(JsonRpcError { code: -32601, message: format!("Método não suportado: {}", method) }),
            },
        }
    }
}
