use std::path::PathBuf;
use std::sync::Arc;
use slint::{ModelRc, VecModel};
use walkdir::WalkDir;

use crate::config::Settings;
use crate::domain::{Book, ConfidentialityLevel, DocumentFormat};
use crate::embeddings::OllamaEmbeddingClient;
use crate::extractors::DocumentExtractor;
use crate::gui::{AppWindow, DocItem};
use crate::vector_store::EmbeddedVectorStore;

pub fn set_ui_status(weak: &slint::Weak<AppWindow>, file: Option<&str>, step: &str, prog: f32, log: &str) {
    let weak_ui = weak.clone();
    let file_opt = file.map(|s| s.to_string());
    let step_str = step.to_string();
    let log_str = log.to_string();
    let _ = slint::invoke_from_event_loop(move || {
        if let Some(ui) = weak_ui.upgrade() {
            if let Some(f) = file_opt { ui.set_ingest_filename(f.into()); }
            ui.set_ingest_step(step_str.into());
            ui.set_ingest_progress(prog);
            ui.set_ingest_log(log_str.into());
        }
    });
}

pub async fn execute_ingest_pipeline(
    raw_paths: Vec<PathBuf>,
    weak: slint::Weak<AppWindow>,
    vector_store: Arc<EmbeddedVectorStore>,
    embedding_client: Arc<OllamaEmbeddingClient>,
    settings: Settings,
) {
    // 1. Expansão recursiva de pastas e validação de formatos
    let mut valid_files: Vec<PathBuf> = Vec::new();
    let mut ignored_count = 0usize;

    for path in raw_paths {
        if path.is_dir() {
            for entry in WalkDir::new(&path).into_iter().filter_map(|e| e.ok()) {
                let p = entry.path();
                if p.is_file() {
                    let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
                    if matches!(ext.as_str(), "pdf" | "epub" | "md" | "txt" | "markdown") {
                        valid_files.push(p.to_path_buf());
                    } else {
                        ignored_count += 1;
                    }
                }
            }
        } else if path.is_file() {
            let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
            if matches!(ext.as_str(), "pdf" | "epub" | "md" | "txt" | "markdown") {
                valid_files.push(path);
            } else {
                ignored_count += 1;
            }
        }
    }

    if valid_files.is_empty() {
        let msg = if ignored_count > 0 {
            format!("⚠️ {} arquivo(s) ignorados (apenas .PDF, .EPUB, .MD, .TXT são aceitos).", ignored_count)
        } else {
            "⚠️ Nenhum documento válido selecionado.".to_string()
        };
        set_ui_status(&weak, Some("Incompatível"), "Formato Inválido", 1.0, &msg);
        let _ = slint::invoke_from_event_loop({
            let weak = weak.clone();
            move || {
                if let Some(ui) = weak.upgrade() {
                    ui.set_ingest_finished(true);
                }
            }
        });
        return;
    }

    let target_dir = settings.database_dir.clone();
    let _ = std::fs::create_dir_all(&target_dir);
    let total = valid_files.len() as f32;

    for (i, src) in valid_files.iter().enumerate() {
        let name = src.file_name().and_then(|s| s.to_str()).unwrap_or("documento");
        let dest = target_dir.join(name);
        let (base, step) = ((i as f32) / total, 1.0 / total);

        if src != &dest {
            if let Err(e) = std::fs::copy(src, &dest) {
                set_ui_status(&weak, Some(name), "Erro de Cópia", base, &format!("❌ Falha ao copiar: {}", e));
                continue;
            }
        }

        set_ui_status(&weak, Some(name), "Calculando SHA-256...", base + step * 0.20, "Verificando integridade e deduplicação...");
        let hash = match DocumentExtractor::compute_sha256(&dest) {
            Ok(h) => h,
            Err(e) => { set_ui_status(&weak, None, "Erro", base, &format!("❌ Falha no hash: {}", e)); continue; }
        };

        // Deduplicação
        if let Some(existing) = vector_store.find_book_by_hash(&hash).await {
            set_ui_status(&weak, Some(name), "Já Indexado", base + step * 0.90, &format!("⏩ Livro '{}' já existe no banco.", existing.title));
            continue;
        }

        set_ui_status(&weak, None, "Extraindo texto...", base + step * 0.40, "Extraindo páginas e estrutura...");
        let pages = match DocumentExtractor::extract_text(&dest) {
            Ok(p) => p,
            Err(e) => { set_ui_status(&weak, None, "Erro na Extração", base, &format!("❌ Documento ilegível: {}", e)); continue; }
        };

        let ext = dest.extension().and_then(|e| e.to_str()).unwrap_or("");
        let book = Book {
            id: format!("book_{}", &hash[..12]),
            title: dest.file_stem().and_then(|s| s.to_str()).unwrap_or("unknown").to_string(),
            file_path: dest.to_string_lossy().to_string(),
            file_hash: hash,
            format: DocumentFormat::from_extension(ext),
            confidentiality: ConfidentialityLevel::Public,
            total_chunks: 0,
            total_tokens: 0,
        };

        let mut chunks = DocumentExtractor::chunk_document(&book, &pages, settings.chunk_size, settings.chunk_overlap);
        if chunks.is_empty() {
            set_ui_status(&weak, None, "Sem Conteúdo", base + step * 0.90, "⚠️ Documento sem texto extraível.");
            continue;
        }

        set_ui_status(&weak, None, "Gerando embeddings...", base + step * 0.70, &format!("Gerando vetores para {} chunks (Ollama)...", chunks.len()));
        let chunk_texts: Vec<&str> = chunks.iter().map(|c| c.content.as_str()).collect();
        if let Ok(embeddings) = embedding_client.embed_batch(&chunk_texts).await {
            for (c, e) in chunks.iter_mut().zip(embeddings) { c.embedding = Some(e); }
        }

        set_ui_status(&weak, None, "Gravando índices...", base + step * 0.95, "Indexando no banco vetorial...");
        let tokens_count: usize = chunks.iter().map(|c| c.token_count).sum();
        let mut updated_book = book;
        updated_book.total_chunks = chunks.len();
        updated_book.total_tokens = tokens_count;
        let _ = vector_store.add_book_with_chunks(updated_book, chunks).await;
    }

    // Recarrega lista
    let books = vector_store.list_books().await;
    let total_c: usize = books.iter().map(|b| b.total_chunks).sum();
    let docs_vec: Vec<DocItem> = books.iter().map(|b| DocItem {
        id: b.id.clone().into(), title: b.title.clone().into(), format_type: b.format.badge_label().into(),
        author: format!("{} Chunks • {} Tokens", b.total_chunks, b.total_tokens).into(), chunks_count: format!("{} Chunks", b.total_chunks).into(),
        meta: format!("{} • {} Chunks • SHA-256: {}", b.title, b.total_chunks, &b.file_hash[..12.min(b.file_hash.len())]).into(),
        preview: format!("Documento: {}\nHash: {}\nTotal Chunks: {}", b.title, b.file_hash, b.total_chunks).into(),
    }).collect();

    let _ = slint::invoke_from_event_loop({
        let weak = weak.clone();
        move || {
            if let Some(ui) = weak.upgrade() {
                ui.set_docs_data(ModelRc::new(VecModel::from(docs_vec)));
                ui.set_total_chunks_counter(format!("{} Chunks", total_c).into());
                ui.set_ingest_progress(1.0);
                ui.set_ingest_finished(true);
                ui.set_ingest_step("Indexação concluída!".into());
                ui.set_ingest_log(format!("{} documento(s) processado(s) com sucesso.", valid_files.len()).into());
            }
        }
    });
}
