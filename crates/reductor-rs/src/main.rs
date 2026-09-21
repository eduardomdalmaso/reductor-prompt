use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;
use clap::{Parser, Subcommand};
use colored::*;
use indicatif::{ProgressBar, ProgressStyle};
use walkdir::WalkDir;

mod config;
mod domain;
mod security;
mod extractors;
mod vector_store;
mod embeddings;
mod algorithms;
mod llm;
mod mcp;
mod api;

use config::Settings;
use domain::{Book, ConfidentialityLevel, DocumentFormat};
use extractors::DocumentExtractor;
use vector_store::EmbeddedVectorStore;
use embeddings::OllamaEmbeddingClient;
use algorithms::AdaptiveRRFEngine;
use llm::LLMService;
use mcp::McpServer;
use api::{create_router, AppState};

#[derive(Parser)]
#[command(name = "reductor")]
#[command(about = "ReductorPrompt - High Performance Native Prompt Optimization Engine in Rust", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// Consulta rápida direta (atalho para o subcomando 'ask')
    query: Option<String>,
}

#[derive(Subcommand)]
enum Commands {
    /// Ingestão e indexação inteligente de livros e documentos
    Ingest {
        /// Força a reindexação de todos os arquivos
        #[arg(short, long)]
        force: bool,
        /// Diretório customizado de documentos
        #[arg(short, long)]
        path: Option<PathBuf>,
    },
    /// Consulta à biblioteca técnica com RAG semântico e corte adaptativo
    Ask {
        /// A pergunta técnica
        query: String,
        /// Ativa modo de raciocínio profundo (Chain-of-Thought)
        #[arg(short, long)]
        deep: bool,
        /// Filtro por título do livro
        #[arg(short, long)]
        book: Option<String>,
        /// Retorna apenas o contexto reduzido sem acionar a LLM
        #[arg(long)]
        only_context: bool,
    },
    /// Lista todos os livros indexados na base vetorial
    List,
    /// Inicia o servidor MCP (Model Context Protocol) via Stdio
    Mcp,
    /// Inicia o servidor de API REST de alta performance
    Serve {
        /// Porta HTTP para escuta (default: 8000)
        #[arg(short, long, default_value = "8000")]
        port: u16,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let settings = Settings::load();
    let vector_store = Arc::new(EmbeddedVectorStore::new(&settings.storage_dir));
    let embedding_client = Arc::new(OllamaEmbeddingClient::new(
        settings.ollama_base_url.clone(),
        settings.ollama_embed_model.clone(),
    ));
    let llm_service = Arc::new(LLMService::new(settings.clone()));

    let cli = Cli::parse();

    // Se nenhum subcomando foi passado, mas foi passada uma query como argumento posicional:
    let command = match cli.command {
        Some(cmd) => cmd,
        None => {
            if let Some(q) = cli.query {
                Commands::Ask {
                    query: q,
                    deep: false,
                    book: None,
                    only_context: false,
                }
            } else {
                println!("{}", "💡 Use 'reductor --help' para ver os comandos disponíveis.".yellow());
                return Ok(());
            }
        }
    };

    match command {
        Commands::Ingest { force, path } => {
            let target_dir = path.unwrap_or_else(|| settings.database_dir.clone());
            println!("{}", format!("📚 ReductorPrompt Rust - Ingestão Paralela em '{}'", target_dir.display()).cyan().bold());

            let mut files_to_process = Vec::new();
            for entry in WalkDir::new(&target_dir).into_iter().filter_map(|e| e.ok()) {
                let path = entry.path();
                if path.is_file() {
                    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
                    if ["pdf", "md", "txt", "markdown"].contains(&ext.as_str()) {
                        files_to_process.push(path.to_path_buf());
                    }
                }
            }

            if files_to_process.is_empty() {
                println!("{}", "⚠️ Nenhum documento compatível encontrado para indexação.".yellow());
                return Ok(());
            }

            let start_total = Instant::now();
            let pb = ProgressBar::new(files_to_process.len() as u64);
            pb.set_style(ProgressStyle::default_bar()
                .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta}) {msg}")
                .unwrap());

            let mut total_indexed_chunks = 0;
            let mut total_indexed_tokens = 0;

            for file_path in files_to_process {
                let file_name = file_path.file_stem().and_then(|s| s.to_str()).unwrap_or("unknown");
                pb.set_message(format!("Processando {}", file_name));

                let hash = match DocumentExtractor::compute_sha256(&file_path) {
                    Ok(h) => h,
                    Err(e) => {
                        pb.println(format!("❌ {}", e));
                        pb.inc(1);
                        continue;
                    }
                };

                // Verifica deduplicação
                if !force {
                    if let Some(_existing) = vector_store.find_book_by_hash(&hash).await {
                        pb.println(format!("⏩ {} (já indexado, pulando)", file_name.dimmed()));
                        pb.inc(1);
                        continue;
                    }
                }

                // Extrai texto
                let pages = match DocumentExtractor::extract_text(&file_path) {
                    Ok(p) => p,
                    Err(e) => {
                        pb.println(format!("❌ Erro na extração de {}: {}", file_name, e));
                        pb.inc(1);
                        continue;
                    }
                };

                let ext = file_path.extension().and_then(|e| e.to_str()).unwrap_or("");
                let book = Book {
                    id: format!("book_{}", &hash[..12]),
                    title: file_name.to_string(),
                    file_path: file_path.to_string_lossy().to_string(),
                    file_hash: hash,
                    format: DocumentFormat::from_extension(ext),
                    confidentiality: ConfidentialityLevel::Public,
                    total_chunks: 0,
                    total_tokens: 0,
                };

                let mut chunks = DocumentExtractor::chunk_document(
                    &book,
                    &pages,
                    settings.chunk_size,
                    settings.chunk_overlap,
                );

                if chunks.is_empty() {
                    pb.inc(1);
                    continue;
                }

                // Gera Embeddings em lote
                let chunk_texts: Vec<&str> = chunks.iter().map(|c| c.content.as_str()).collect();
                match embedding_client.embed_batch(&chunk_texts).await {
                    Ok(embeddings) => {
                        for (c, emb) in chunks.iter_mut().zip(embeddings) {
                            c.embedding = Some(emb);
                        }
                    }
                    Err(e) => {
                        pb.println(format!("❌ Erro ao gerar embeddings para {}: {}", file_name, e));
                        pb.inc(1);
                        continue;
                    }
                }

                let tokens_count: usize = chunks.iter().map(|c| c.token_count).sum();
                total_indexed_chunks += chunks.len();
                total_indexed_tokens += tokens_count;

                let mut updated_book = book;
                updated_book.total_chunks = chunks.len();
                updated_book.total_tokens = tokens_count;

                if let Err(e) = vector_store.add_book_with_chunks(updated_book, chunks).await {
                    pb.println(format!("❌ Erro ao salvar no índice vetorial: {}", e));
                }

                pb.inc(1);
            }

            pb.finish_with_message("Concluído!");
            println!("\n{}", "✨ Ingestão concluída com sucesso!".green().bold());
            println!("📊 Total de Chunks: {} | Tokens Indexados: {} | Tempo: {:.2}s",
                total_indexed_chunks.to_string().cyan(),
                total_indexed_tokens.to_string().cyan(),
                start_total.elapsed().as_secs_f32()
            );
        }

        Commands::Ask { query, deep, book, only_context } => {
            println!("{}", format!("🔍 Pergunta: {}", query).cyan().bold());
            let start = Instant::now();

            let query_vec = match embedding_client.embed_single(&query).await {
                Ok(v) => v,
                Err(e) => {
                    eprintln!("{}", format!("❌ Falha ao gerar embedding da pergunta: {}", e).red());
                    return Ok(());
                }
            };

            let scored = vector_store.search_similar(
                &query_vec,
                settings.default_top_k,
                settings.similarity_threshold,
                book.as_deref(),
            ).await;

            let budget = AdaptiveRRFEngine::apply_elbow_and_budget(
                scored,
                settings.default_max_context_tokens,
                0.35,
                0.22,
            );

            if only_context {
                println!("\n{}", "📄 Contexto Reduzido Extraído dos Livros:".yellow().bold());
                for (i, sc) in budget.selected_chunks.iter().enumerate() {
                    println!("\n[Trecho {}] {} (Pág {:?} | Relevância: {:.2}):\n{}",
                        i + 1,
                        sc.chunk.book_title.cyan(),
                        sc.chunk.page_number,
                        sc.similarity_score,
                        sc.chunk.content
                    );
                }
            } else {
                let ans = match llm_service.generate_rag_response(&query, &budget.selected_chunks, deep).await {
                    Ok(a) => a,
                    Err(e) => format!("❌ Erro na geração de resposta: {}", e),
                };

                println!("\n{}", "💡 Resposta:".green().bold());
                println!("{}", ans);
            }

            println!("\n{}", "─".repeat(60).dimmed());
            println!("📊 Tokens Utilizados: {} | Economizados: {} | Redução: {:.2}% ({:.2}s)",
                budget.total_tokens_used.to_string().cyan(),
                budget.total_tokens_saved.to_string().green(),
                budget.reduction_percentage,
                start.elapsed().as_secs_f32()
            );

            println!("\n📖 Fontes Consultadas:");
            for sc in &budget.selected_chunks {
                println!(" • {} (Pág {:?}) - Similaridade: {:.3}",
                    sc.chunk.book_title.yellow(),
                    sc.chunk.page_number,
                    sc.similarity_score
                );
            }
        }

        Commands::List => {
            let books = vector_store.list_books().await;
            println!("{}", format!("📚 Acervo Técnico Indexado ({} livros):", books.len()).cyan().bold());
            println!("{:<45} {:<12} {:<15} {:<15}", "Título", "Formato", "Chunks", "Tokens");
            println!("{}", "─".repeat(90).dimmed());
            for b in books {
                println!("{:<45} {:<12?} {:<15} {:<15}",
                    b.title,
                    b.format,
                    b.total_chunks,
                    b.total_tokens
                );
            }
        }

        Commands::Mcp => {
            let mcp = McpServer::new(vector_store, embedding_client, llm_service);
            mcp.run_stdio().await;
        }

        Commands::Serve { port } => {
            let app_state = AppState {
                vector_store,
                embedding_client,
                llm_service,
            };
            let router = create_router(app_state);
            let addr = format!("127.0.0.1:{}", port);
            println!("{}", format!("🚀 Servidor REST Axum rodando em http://{}", addr).green().bold());
            let listener = tokio::net::TcpListener::bind(&addr).await?;
            axum::serve(listener, router).await?;
        }
    }

    Ok(())
}
