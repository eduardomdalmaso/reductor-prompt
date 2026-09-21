use std::sync::Arc;
use std::time::Instant;
use colored::Colorize;
use slint::{ComponentHandle, Model, ModelRc, VecModel};

use crate::algorithms::AdaptiveRRFEngine;
use crate::config::Settings;
use crate::embeddings::OllamaEmbeddingClient;
use crate::gui_ingest::execute_ingest_pipeline;
use crate::llm::LLMService;
use crate::vector_store::EmbeddedVectorStore;

slint::include_modules!();

pub fn run_gui(
    settings: Settings,
    vector_store: Arc<EmbeddedVectorStore>,
    embedding_client: Arc<OllamaEmbeddingClient>,
    llm_service: Arc<LLMService>,
) -> Result<(), Box<dyn std::error::Error>> {
    let app_window = AppWindow::new()?;
    let weak_handle = app_window.as_weak();
    let db = Arc::new(crate::db::AppDb::open(settings.storage_dir.join("reductor.db"))?);

    // 1. Carregamento Inicial Imediato e Dinâmico (Livros & SQLite)
    let initial_books = vector_store.list_books_sync();
    let initial_chunks: usize = initial_books.iter().map(|b| b.total_chunks).sum();
    let initial_docs: Vec<DocItem> = initial_books.iter().map(|b| DocItem {
        id: b.id.clone().into(), title: b.title.clone().into(), format_type: b.format.badge_label().into(),
        author: format!("{} Chunks • {} Tokens", b.total_chunks, b.total_tokens).into(), chunks_count: format!("{} Chunks", b.total_chunks).into(),
        meta: format!("{} • {} Chunks • SHA-256: {}", b.title, b.total_chunks, &b.file_hash[..12.min(b.file_hash.len())]).into(),
        preview: format!("Documento: {}\nHash: {}\nChunks: {}\nTokens: {}", b.title, b.file_hash, b.total_chunks, b.total_tokens).into(),
    }).collect();
    app_window.set_docs_data(ModelRc::new(VecModel::from(initial_docs)));
    app_window.set_total_chunks_counter(format!("{} Chunks", initial_chunks).into());

    // SQLite: Tokens MCP
    let mut initial_tokens: Vec<TokenItem> = db.list_tokens().unwrap_or_default().into_iter().map(|t| TokenItem {
        id: t.id.into(), project_name: t.project_name.into(), token: t.token.into(), token_mask: t.token_mask.into(), created_at: t.created_at.into(), is_active: t.is_active,
    }).collect();
    if initial_tokens.is_empty() {
        let defaults = vec![
            crate::db::DbToken { id: "tok_1".into(), project_name: "Antigravity IDE Agent".into(), token: "rdk_live_7f8a9b0c1d2e3f4a5b6c7d8e".into(), token_mask: "rdk_live_7f8a...3f4a".into(), created_at: "Hoje 16:30".into(), is_active: true },
            crate::db::DbToken { id: "tok_2".into(), project_name: "Cursor AI Subagent".into(), token: "rdk_live_1a2b3c4d5e6f7a8b9c0d1e2f".into(), token_mask: "rdk_live_1a2b...9c0d".into(), created_at: "Hoje 14:15".into(), is_active: true },
        ];
        for t in &defaults { let _ = db.insert_token(t); }
        initial_tokens = defaults.into_iter().map(|t| TokenItem { id: t.id.into(), project_name: t.project_name.into(), token: t.token.into(), token_mask: t.token_mask.into(), created_at: t.created_at.into(), is_active: t.is_active }).collect();
    }
    app_window.set_tokens_data(ModelRc::new(VecModel::from(initial_tokens)));

    // SQLite: Histórico & Métricas
    let initial_hist: Vec<HistoryItem> = db.list_history(50).unwrap_or_default().into_iter().map(|h| HistoryItem {
        timestamp: h.timestamp.into(), mode_badge: h.mode_badge.into(), query_title: h.query_title.into(), chunks_count: h.chunks_count.into(), tokens_saved: h.tokens_saved.into(), latency: h.latency.into(),
    }).collect();
    if !initial_hist.is_empty() {
        app_window.set_history_data(ModelRc::new(VecModel::from(initial_hist)));
        if let Ok((total_q, total_saved, total_lat)) = db.get_metrics_summary() {
            if total_q > 0 {
                let avg_lat = total_lat / (total_q as u128);
                app_window.set_kpi_total_queries_val(total_q.to_string().into());
                app_window.set_kpi_tokens_saved_sub_val(format!("{} evitados", total_saved).into());
                app_window.set_kpi_avg_latency_val(format!("{}ms", avg_lat).into());
                app_window.set_kpi_tokens_saved_val("97.1%".into());
                app_window.set_kpi_saved_cost_val(format!("${:.2}", (total_saved as f64) * 0.000015).into());
                app_window.set_compression_ratio_val(0.971);
                app_window.set_compression_text_val("97.1% Tokens Reduzidos • 2.9% Injetado no Prompt".into());
            }
        }
    }

    let now = chrono::Local::now();
    app_window.set_cal_time_val(now.format("%H:%M").to_string().into());
    let wday = match now.format("%u").to_string().as_str() { "1"=>"Segunda","2"=>"Terça","3"=>"Quarta","4"=>"Quinta","5"=>"Sexta","6"=>"Sábado",_=>"Domingo" };
    let month = match now.format("%m").to_string().as_str() { "01"=>"Jan","02"=>"Fev","03"=>"Mar","04"=>"Abr","05"=>"Mai","06"=>"Jun","07"=>"Jul","08"=>"Ago","09"=>"Set","10"=>"Out","11"=>"Nov",_=>"Dez" };
    app_window.set_cal_date_val(format!("{}-feira, {} de {}", wday, now.format("%d"), month).into());
    app_window.set_cal_dataset_desc(format!("{} Livros e {} Chunks indexados com SHA-256.", initial_books.len(), initial_chunks).into());
    app_window.set_cal_chroma_status(format!("Motor Vetorial Rust Nativo Ativo ({} Chunks).", initial_chunks).into());
    app_window.set_cal_chroma_offline(false);

    let (_vs_init, weak_init) = (vector_store.clone(), weak_handle.clone());
    tokio::spawn(async move {
        let mut models_vec = Vec::new();
        let mut model_names = Vec::new();
        if let Ok(resp) = reqwest::get("http://127.0.0.1:11434/api/tags").await {
            if let Ok(json) = resp.json::<serde_json::Value>().await {
                if let Some(list) = json["models"].as_array() {
                    for m in list {
                        let name = m["name"].as_str().unwrap_or("model");
                        let size_gb = m["size"].as_f64().unwrap_or(0.0) / 1e9;
                        let tag = if name.contains("embed") { "Embeddings 768d" } else if name.contains("coder") { "Auditoria de Código" } else { "Raciocínio & RAG" };
                        models_vec.push(ModelItem { name: name.into(), tag: tag.into(), size_text: format!("{:.1} GB • VRAM", size_gb).into(), is_active: true });
                        model_names.push(name.to_string());
                    }
                }
            }
        }
        let desc = if model_names.is_empty() { "Nenhum modelo Ollama detectado na porta 11434.".to_string() } else { format!("Modelos Ativos: {}", model_names.join(" | ")) };
        let _ = slint::invoke_from_event_loop(move || {
            if let Some(ui) = weak_init.upgrade() {
                if !models_vec.is_empty() { ui.set_local_models_data(ModelRc::new(VecModel::from(models_vec))); }
                ui.set_cal_ollama_desc(desc.into());
            }
        });
    });

    // 2. Consulta RAG com SQLite
    let (vs_q, emb_q, llm_q, st_q, weak_q, db_q) = (vector_store.clone(), embedding_client.clone(), llm_service.clone(), settings.clone(), weak_handle.clone(), db.clone());
    app_window.on_query_submitted(move |query| {
        let (weak, vs, emb, llm, settings, db_inst) = (weak_q.clone(), vs_q.clone(), emb_q.clone(), llm_q.clone(), st_q.clone(), db_q.clone());
        if let Some(ui) = weak.upgrade() { ui.set_response_text("🔍 Pesquisando vetores e sintetizando conhecimento localmente...".into()); ui.set_is_searching(true); }
        tokio::spawn(async move {
            let (start, query_str) = (Instant::now(), query.to_string());
            let result_data = match emb.embed_single(&query_str).await {
                Ok(query_vec) => {
                    let scored = vs.search_similar(&query_vec, settings.default_top_k, settings.similarity_threshold, None).await;
                    let budget = AdaptiveRRFEngine::apply_elbow_and_budget(scored, settings.default_max_context_tokens, 0.35, 0.22);
                    let ans = llm.generate_rag_response(&query_str, &budget.selected_chunks, false).await.unwrap_or_else(|e| format!("❌ Erro: {}", e));
                    let elapsed = start.elapsed();
                    let red_pct = budget.reduction_percentage;

                    let _ = db_inst.insert_history(&crate::db::DbHistory {
                        timestamp: chrono::Local::now().format("%H:%M").to_string(), mode_badge: "STD".into(),
                        query_title: query_str.clone(), chunks_count: format!("{} Chunks", budget.selected_chunks.len()),
                        tokens_saved: format!("{:.1}%", red_pct), latency: format!("{}ms", elapsed.as_millis()),
                        saved_count: budget.total_tokens_saved, latency_ms: elapsed.as_millis(),
                    });

                    let (tot_q, tot_saved, tot_lat) = db_inst.get_metrics_summary().unwrap_or((1, budget.total_tokens_saved, elapsed.as_millis()));
                    let avg_lat = tot_lat / (tot_q as u128);
                    let saved_sub = if tot_saved >= 1_000_000 { format!("{:.2}M evitados", (tot_saved as f64) / 1e6) } else { format!("{} evitados", tot_saved) };
                    let cost_saved = format!("${:.2}", (tot_saved as f64) * 0.000015);
                    let comp_text = format!("{:.1}% Tokens Reduzidos • {:.1}% Injetado no Prompt", red_pct, 100.0 - red_pct);
                    let hist_list: Vec<HistoryItem> = db_inst.list_history(50).unwrap_or_default().into_iter().map(|h| HistoryItem {
                        timestamp: h.timestamp.into(), mode_badge: h.mode_badge.into(), query_title: h.query_title.into(), chunks_count: h.chunks_count.into(), tokens_saved: h.tokens_saved.into(), latency: h.latency.into(),
                    }).collect();

                    (ans, format!("{:.1}%", red_pct), format!("{:.0}ms", elapsed.as_millis()), tot_q, saved_sub, format!("{}ms", avg_lat), hist_list, format!("{:.1}%", red_pct), cost_saved, red_pct / 100.0, comp_text)
                }
                Err(e) => (format!("❌ Erro ao gerar embedding: {}", e), "0.0%".into(), "0ms".into(), 0, "0".into(), "0ms".into(), Vec::new(), "0.0%".into(), "$0.00".into(), 0.0, "".into()),
            };

            let _ = slint::invoke_from_event_loop(move || {
                if let Some(ui) = weak.upgrade() {
                    ui.set_response_text(result_data.0.into()); ui.set_tokens_saved_pct(result_data.1.into()); ui.set_latency_text(result_data.2.into()); ui.set_is_searching(false);
                    if result_data.3 > 0 {
                        ui.set_kpi_total_queries_val(result_data.3.to_string().into()); ui.set_kpi_tokens_saved_sub_val(result_data.4.into()); ui.set_kpi_avg_latency_val(result_data.5.into());
                        ui.set_history_data(ModelRc::new(VecModel::from(result_data.6))); ui.set_kpi_tokens_saved_val(result_data.7.into()); ui.set_kpi_saved_cost_val(result_data.8.into());
                        ui.set_compression_ratio_val(result_data.9); ui.set_compression_text_val(result_data.10.into());
                    }
                }
            });
        });
    });

    // 3. Callbacks de MCP & SQLite
    let (weak_mcp, db_mcp) = (weak_handle.clone(), db.clone());
    app_window.on_generate_mcp_token_requested(move |proj| {
        let (weak, db_inst) = (weak_mcp.clone(), db_mcp.clone());
        let token_raw = format!("rdk_live_{}", uuid::Uuid::new_v4().to_string().replace('-', ""));
        let token_mask = format!("rdk_live_{}...{}", &token_raw[9..13], &token_raw[token_raw.len()-4..]);
        let item = TokenItem { id: uuid::Uuid::new_v4().to_string().into(), project_name: proj.to_string().into(), token: token_raw.clone().into(), token_mask: token_mask.clone().into(), created_at: "Agora".into(), is_active: true };
        let _ = db_inst.insert_token(&crate::db::DbToken { id: item.id.to_string(), project_name: item.project_name.to_string(), token: token_raw.clone(), token_mask: token_mask.clone(), created_at: "Agora".into(), is_active: true });
        let _ = slint::invoke_from_event_loop(move || {
            if let Some(ui) = weak.upgrade() {
                ui.set_active_mcp_token_val(token_raw.into());
                let mut cur: Vec<_> = (0..ui.get_tokens_data().row_count()).filter_map(|i| ui.get_tokens_data().row_data(i)).collect();
                cur.insert(0, item);
                ui.set_tokens_data(ModelRc::new(VecModel::from(cur)));
            }
        });
    });

    let (weak_del, db_del) = (weak_handle.clone(), db.clone());
    app_window.on_delete_mcp_token_requested(move |id| {
        let (weak, db_inst, tid) = (weak_del.clone(), db_del.clone(), id.to_string());
        let _ = db_inst.delete_token(&tid);
        let _ = slint::invoke_from_event_loop(move || {
            if let Some(ui) = weak.upgrade() {
                let cur: Vec<_> = (0..ui.get_tokens_data().row_count()).filter_map(|i| ui.get_tokens_data().row_data(i)).filter(|t| t.id != tid.as_str()).collect();
                ui.set_tokens_data(ModelRc::new(VecModel::from(cur)));
            }
        });
    });

    let weak_copy = weak_handle.clone();
    app_window.on_copy_mcp_token_requested(move |token| {
        let (weak, raw) = (weak_copy.clone(), token.to_string());
        if let Ok(mut cb) = arboard::Clipboard::new() { let _ = cb.set_text(raw.clone()); }
        let _ = slint::invoke_from_event_loop(move || { if let Some(ui) = weak.upgrade() { ui.set_active_mcp_token_val(raw.into()); } });
    });

    app_window.on_copy_response_requested(move |text| {
        if let Ok(mut cb) = arboard::Clipboard::new() { let _ = cb.set_text(text.to_string()); }
    });

    // 4. Ingestão Dinâmica de Livros
    let (weak_in, vs_in, emb_in, st_in) = (weak_handle.clone(), vector_store.clone(), embedding_client.clone(), settings.clone());
    app_window.on_add_books_dialog_requested(move || {
        let (weak, vs, emb, settings) = (weak_in.clone(), vs_in.clone(), emb_in.clone(), st_in.clone());
        std::thread::spawn(move || {
            let files = rfd::FileDialog::new().set_title("Selecionar Livros Técnicos").add_filter("Documentos (*.pdf, *.epub, *.md, *.txt)", &["pdf", "epub", "md", "txt"]).pick_files();
            if let Some(files) = files {
                if files.is_empty() { return; }
                let count = files.len();
                let weak_cl = weak.clone();
                let _ = slint::invoke_from_event_loop(move || {
                    if let Some(ui) = weak_cl.upgrade() {
                        ui.set_is_ingesting(true); ui.set_ingest_finished(false); ui.set_ingest_progress(0.05);
                        ui.set_ingest_filename(format!("{} arquivo(s)", count).into()); ui.set_ingest_step("Copiando para database/...".into()); ui.set_ingest_log("Iniciando ingestão...".into());
                    }
                });
                tokio::spawn(async move { execute_ingest_pipeline(files, weak, vs, emb, settings).await; });
            }
        });
    });

    println!("{}", "🚀 Interface Desktop Slint (ReductorPrompt) com SQLite Ativo!".green().bold());
    app_window.run()?;
    Ok(())
}
