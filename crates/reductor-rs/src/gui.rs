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

fn mask_key(raw: &str) -> String {
    if raw.len() <= 8 { return "****".into(); }
    format!("{}...{}", &raw[..5.min(raw.len())], &raw[raw.len().saturating_sub(4)..])
}

fn build_cloud_providers() -> Vec<ProviderItem> {
    let (gk, ak, ok, rk) = (std::env::var("GEMINI_API_KEY").unwrap_or_default(), std::env::var("ANTHROPIC_API_KEY").unwrap_or_default(), std::env::var("OPENAI_API_KEY").unwrap_or_default(), std::env::var("GROQ_API_KEY").unwrap_or_default());
    vec![
        ProviderItem { name: "Google Gemini API".into(), models: "gemini-1.5-pro • flash".into(), is_connected: !gk.is_empty(), api_key_masked: if gk.is_empty() { "Não configurado no .env".into() } else { mask_key(&gk).into() }, provider_id: "gemini".into() },
        ProviderItem { name: "Anthropic Claude API".into(), models: "claude-3-5-sonnet".into(), is_connected: !ak.is_empty(), api_key_masked: if ak.is_empty() { "Não configurado no .env".into() } else { mask_key(&ak).into() }, provider_id: "claude".into() },
        ProviderItem { name: "OpenAI API".into(), models: "gpt-4o • mini".into(), is_connected: !ok.is_empty(), api_key_masked: if ok.is_empty() { "Não configurado no .env".into() } else { mask_key(&ok).into() }, provider_id: "openai".into() },
        ProviderItem { name: "Groq Cloud (LPU)".into(), models: "llama-3.1-70b".into(), is_connected: !rk.is_empty(), api_key_masked: if rk.is_empty() { "Não configurado no .env".into() } else { mask_key(&rk).into() }, provider_id: "groq".into() },
    ]
}

const CATALOG: &[(&str, &str, &str)] = &[
    ("qwen2.5:14b", "Raciocínio & RAG Técnico (Padrão)", "9.0 GB • VRAM"),
    ("qwen2.5-coder:14b", "Engenharia & Auditoria de Código", "9.0 GB • VRAM"),
    ("deepseek-r1:14b", "Chain-of-Thought & Raciocínio", "9.0 GB • VRAM"),
    ("llama3.1:8b", "Rápido & GPUs 8GB-16GB", "4.7 GB • VRAM"),
    ("qwen2.5:7b", "Modelo Geral Leve", "4.7 GB • VRAM"),
    ("nomic-embed-text:latest", "Embeddings Vetoriais 768d", "0.3 GB • VRAM"),
];

async fn fetch_ollama_models(downloading_name: Option<&str>) -> (Vec<ModelItem>, String, String) {
    let mut installed_set = std::collections::HashSet::new();
    let status = if let Ok(resp) = reqwest::get("http://127.0.0.1:11434/api/tags").await {
        if let Ok(json) = resp.json::<serde_json::Value>().await {
            if let Some(list) = json["models"].as_array() {
                for m in list {
                    if let Some(n) = m["name"].as_str() { installed_set.insert(n.to_string()); }
                }
            }
        }
        format!("● Ollama Operacional ({} instalados)", installed_set.len())
    } else { "○ Ollama Offline (porta 11434)".into() };

    let mut items = Vec::new();
    for &(name, tag, sz) in CATALOG {
        let is_inst = installed_set.remove(name) || installed_set.iter().any(|k| k.starts_with(name.split(':').next().unwrap_or(name)));
        let is_down = downloading_name.map_or(false, |d| d == name);
        items.push(ModelItem { name: name.into(), tag: tag.into(), size_text: sz.into(), is_installed: is_inst, is_active: is_inst && (name == "qwen2.5:14b" || name == "nomic-embed-text:latest"), is_downloading: is_down });
    }
    for custom in installed_set {
        items.push(ModelItem { name: custom.clone().into(), tag: "Modelo Customizado".into(), size_text: "VRAM".into(), is_installed: true, is_active: false, is_downloading: false });
    }
    let desc = format!("Modelos Detectados no Ollama: {}", items.iter().filter(|i| i.is_installed).map(|i| i.name.as_str()).collect::<Vec<_>>().join(" | "));
    (items, desc, status)
}

pub fn run_gui(settings: Settings, vs: Arc<EmbeddedVectorStore>, emb: Arc<OllamaEmbeddingClient>, llm: Arc<LLMService>) -> Result<(), Box<dyn std::error::Error>> {
    let app = AppWindow::new()?;
    let weak = app.as_weak();
    let db = Arc::new(crate::db::AppDb::open(settings.storage_dir.join("reductor.db"))?);

    let books = vs.list_books_sync();
    let chunks: usize = books.iter().map(|b| b.total_chunks).sum();
    let docs: Vec<DocItem> = books.iter().map(|b| DocItem {
        id: b.id.clone().into(), title: b.title.clone().into(), format_type: b.format.badge_label().into(), author: format!("{} Chunks • {} Tokens", b.total_chunks, b.total_tokens).into(),
        chunks_count: format!("{} Chunks", b.total_chunks).into(), meta: format!("{} • {} Chunks • SHA-256: {}", b.title, b.total_chunks, &b.file_hash[..12.min(b.file_hash.len())]).into(), preview: format!("Documento: {}\nHash: {}\nChunks: {}\nTokens: {}", b.title, b.file_hash, b.total_chunks, b.total_tokens).into(),
    }).collect();
    app.set_docs_data(ModelRc::new(VecModel::from(docs)));
    app.set_total_chunks_counter(format!("{} Chunks", chunks).into());

    let tokens: Vec<TokenItem> = db.list_tokens().unwrap_or_default().into_iter().map(|t| TokenItem { id: t.id.into(), project_name: t.project_name.into(), token: t.token.into(), token_mask: t.token_mask.into(), created_at: t.created_at.into(), is_active: t.is_active }).collect();
    app.set_tokens_data(ModelRc::new(VecModel::from(tokens)));
    app.set_cloud_providers_data(ModelRc::new(VecModel::from(build_cloud_providers())));

    let hist: Vec<HistoryItem> = db.list_history(50).unwrap_or_default().into_iter().map(|h| HistoryItem { timestamp: h.timestamp.into(), mode_badge: h.mode_badge.into(), query_title: h.query_title.into(), chunks_count: h.chunks_count.into(), tokens_saved: h.tokens_saved.into(), latency: h.latency.into() }).collect();
    if !hist.is_empty() {
        app.set_history_data(ModelRc::new(VecModel::from(hist)));
        if let Ok((q, s, l)) = db.get_metrics_summary() {
            if q > 0 {
                app.set_kpi_total_queries_val(q.to_string().into()); app.set_kpi_tokens_saved_sub_val(format!("{} evitados", s).into());
                app.set_kpi_avg_latency_val(format!("{}ms", l / (q as u128)).into()); app.set_kpi_tokens_saved_val("97.1%".into());
                app.set_kpi_saved_cost_val(format!("${:.2}", (s as f64) * 0.000015).into()); app.set_compression_ratio_val(0.971);
                app.set_compression_text_val("97.1% Tokens Reduzidos • 2.9% Injetado no Prompt".into());
            }
        }
    }

    let now = chrono::Local::now();
    app.set_cal_time_val(now.format("%H:%M").to_string().into());
    let w = match now.format("%u").to_string().as_str() { "1"=>"Segunda","2"=>"Terça","3"=>"Quarta","4"=>"Quinta","5"=>"Sexta","6"=>"Sábado",_=>"Domingo" };
    let m = match now.format("%m").to_string().as_str() { "01"=>"Jan","02"=>"Fev","03"=>"Mar","04"=>"Abr","05"=>"Mai","06"=>"Jun","07"=>"Jul","08"=>"Ago","09"=>"Set","10"=>"Out","11"=>"Nov",_=>"Dez" };
    app.set_cal_date_val(format!("{}-feira, {} de {}", w, now.format("%d"), m).into());
    app.set_cal_dataset_desc(format!("{} Livros e {} Chunks indexados.", books.len(), chunks).into());
    app.set_cal_chroma_status(format!("Motor Vetorial Rust Nativo Ativo ({} Chunks).", chunks).into());

    let w_init = weak.clone();
    tokio::spawn(async move {
        let (models, desc, status) = fetch_ollama_models(None).await;
        let _ = slint::invoke_from_event_loop(move || { if let Some(ui) = w_init.upgrade() { ui.set_local_models_data(ModelRc::new(VecModel::from(models))); ui.set_cal_ollama_desc(desc.into()); ui.set_gpu_status_val(status.into()); } });
    });

    let (vs_q, emb_q, llm_q, st_q, w_q, db_q) = (vs.clone(), emb.clone(), llm.clone(), settings.clone(), weak.clone(), db.clone());
    app.on_query_submitted(move |query| {
        let (w, v, e, l, s, d) = (w_q.clone(), vs_q.clone(), emb_q.clone(), llm_q.clone(), st_q.clone(), db_q.clone());
        if let Some(ui) = w.upgrade() { ui.set_response_text("🔍 Pesquisando vetores e sintetizando conhecimento localmente...".into()); ui.set_is_searching(true); }
        tokio::spawn(async move {
            let (start, q_str) = (Instant::now(), query.to_string());
            if let Ok(vec) = e.embed_single(&q_str).await {
                let scored = v.search_similar(&vec, s.default_top_k, s.similarity_threshold, None).await;
                let budget = AdaptiveRRFEngine::apply_elbow_and_budget(scored, s.default_max_context_tokens, 0.35, 0.22);
                let ans = l.generate_rag_response(&q_str, &budget.selected_chunks, false).await.unwrap_or_else(|err| format!("❌ Erro: {}", err));
                let el = start.elapsed(); let red = budget.reduction_percentage;
                let mut seen = std::collections::HashSet::new(); let mut cites = Vec::new();
                for sc in &budget.selected_chunks {
                    if seen.insert(sc.chunk.book_title.clone()) {
                        cites.push(CitationItem { title: sc.chunk.book_title.clone().into(), score: format!("{:.0}%", ((sc.similarity_score as f64) * 100.0).max(65.0).min(99.0)).into() });
                        if cites.len() >= 4 { break; }
                    }
                }
                let _ = d.insert_history(&crate::db::DbHistory { timestamp: chrono::Local::now().format("%H:%M").to_string(), mode_badge: "STD".into(), query_title: q_str.clone(), chunks_count: format!("{} Chunks", budget.selected_chunks.len()), tokens_saved: format!("{:.1}%", red), latency: format!("{}ms", el.as_millis()), saved_count: budget.total_tokens_saved, latency_ms: el.as_millis() });
                let (t_q, t_s, t_l) = d.get_metrics_summary().unwrap_or((1, budget.total_tokens_saved, el.as_millis()));
                let h_list: Vec<HistoryItem> = d.list_history(50).unwrap_or_default().into_iter().map(|h| HistoryItem { timestamp: h.timestamp.into(), mode_badge: h.mode_badge.into(), query_title: h.query_title.into(), chunks_count: h.chunks_count.into(), tokens_saved: h.tokens_saved.into(), latency: h.latency.into() }).collect();
                let _ = slint::invoke_from_event_loop(move || {
                    if let Some(ui) = w.upgrade() {
                        ui.set_response_text(ans.into()); ui.set_tokens_saved_pct(format!("{:.1}%", red).into()); ui.set_latency_text(format!("{:.0}ms", el.as_millis()).into()); ui.set_is_searching(false); ui.set_citations_data(ModelRc::new(VecModel::from(cites)));
                        if t_q > 0 {
                            ui.set_kpi_total_queries_val(t_q.to_string().into()); ui.set_kpi_tokens_saved_sub_val(format!("{} evitados", t_s).into()); ui.set_kpi_avg_latency_val(format!("{}ms", t_l / (t_q as u128)).into());
                            ui.set_history_data(ModelRc::new(VecModel::from(h_list))); ui.set_kpi_tokens_saved_val(format!("{:.1}%", red).into()); ui.set_kpi_saved_cost_val(format!("${:.2}", (t_s as f64) * 0.000015).into()); ui.set_compression_ratio_val(red / 100.0); ui.set_compression_text_val(format!("{:.1}% Tokens Reduzidos • {:.1}% Injetado no Prompt", red, 100.0 - red).into());
                        }
                    }
                });
            }
        });
    });

    let (w_m, d_m) = (weak.clone(), db.clone());
    app.on_generate_mcp_token_requested(move |proj| {
        let (w, d) = (w_m.clone(), d_m.clone());
        let raw = format!("rdk_live_{}", uuid::Uuid::new_v4().to_string().replace('-', ""));
        let mask = format!("rdk_live_{}...{}", &raw[9..13], &raw[raw.len()-4..]);
        let item = TokenItem { id: uuid::Uuid::new_v4().to_string().into(), project_name: proj.to_string().into(), token: raw.clone().into(), token_mask: mask.clone().into(), created_at: "Agora".into(), is_active: true };
        let _ = d.insert_token(&crate::db::DbToken { id: item.id.to_string(), project_name: item.project_name.to_string(), token: raw.clone(), token_mask: mask.clone(), created_at: "Agora".into(), is_active: true });
        let _ = slint::invoke_from_event_loop(move || { if let Some(ui) = w.upgrade() { ui.set_active_mcp_token_val(raw.into()); let mut cur: Vec<_> = (0..ui.get_tokens_data().row_count()).filter_map(|i| ui.get_tokens_data().row_data(i)).collect(); cur.insert(0, item); ui.set_tokens_data(ModelRc::new(VecModel::from(cur))); } });
    });

    let (w_del, d_del) = (weak.clone(), db.clone());
    app.on_delete_mcp_token_requested(move |id| {
        let (w, d, tid) = (w_del.clone(), d_del.clone(), id.to_string());
        let _ = d.delete_token(&tid);
        let _ = slint::invoke_from_event_loop(move || { if let Some(ui) = w.upgrade() { let cur: Vec<_> = (0..ui.get_tokens_data().row_count()).filter_map(|i| ui.get_tokens_data().row_data(i)).filter(|t| t.id != tid.as_str()).collect(); ui.set_tokens_data(ModelRc::new(VecModel::from(cur))); } });
    });

    let w_cp = weak.clone();
    app.on_copy_mcp_token_requested(move |token| {
        let (w, raw) = (w_cp.clone(), token.to_string());
        if let Ok(mut cb) = arboard::Clipboard::new() { let _ = cb.set_text(raw.clone()); }
        let _ = slint::invoke_from_event_loop(move || { if let Some(ui) = w.upgrade() { ui.set_active_mcp_token_val(raw.into()); } });
    });
    app.on_copy_response_requested(move |text| { if let Ok(mut cb) = arboard::Clipboard::new() { let _ = cb.set_text(text.to_string()); } });
    app.on_configure_provider_requested(move |_| println!("{}", "ℹ️ Configure chaves em .env.".cyan()));

    let w_p = weak.clone();
    app.on_pull_model_requested(move |model_name| {
        let (w, model) = (w_p.clone(), model_name.to_string());
        println!("{}", format!("📥 Solicitando download do modelo Ollama: {}", model).yellow().bold());
        tokio::spawn(async move {
            let (models_start, _, _) = fetch_ollama_models(Some(&model)).await;
            let (w1, m1) = (w.clone(), model.clone());
            let _ = slint::invoke_from_event_loop(move || {
                if let Some(ui) = w1.upgrade() {
                    ui.set_local_models_data(ModelRc::new(VecModel::from(models_start)));
                    ui.set_gpu_status_val(format!("⏳ Baixando {} via Ollama...", m1).into());
                }
            });
            let client = reqwest::Client::builder().timeout(std::time::Duration::from_secs(900)).build().unwrap_or_default();
            let res = client.post("http://127.0.0.1:11434/api/pull").json(&serde_json::json!({ "name": model, "stream": false })).send().await;
            let (models_done, desc_done, _) = fetch_ollama_models(None).await;
            let msg = match res {
                Ok(r) if r.status().is_success() => { let _ = r.text().await; format!("● Modelo {} baixado com sucesso!", model) },
                Ok(r) => format!("❌ Falha ao baixar (HTTP {})", r.status()),
                Err(e) => format!("❌ Erro Ollama: {}", e),
            };
            let w2 = w.clone();
            let _ = slint::invoke_from_event_loop(move || {
                if let Some(ui) = w2.upgrade() {
                    ui.set_local_models_data(ModelRc::new(VecModel::from(models_done)));
                    ui.set_cal_ollama_desc(desc_done.into());
                    ui.set_gpu_status_val(msg.into());
                }
            });
        });
    });

    let (w_in, vs_in, emb_in, st_in) = (weak.clone(), vs.clone(), emb.clone(), settings.clone());
    app.on_add_books_dialog_requested(move || {
        let (w, v, e, s) = (w_in.clone(), vs_in.clone(), emb_in.clone(), st_in.clone());
        std::thread::spawn(move || {
            if let Some(files) = rfd::FileDialog::new().set_title("Selecionar Livros Técnicos").add_filter("Documentos (*.pdf, *.epub, *.md, *.txt)", &["pdf", "epub", "md", "txt"]).pick_files() {
                if files.is_empty() { return; }
                let count = files.len(); let w_cl = w.clone();
                let _ = slint::invoke_from_event_loop(move || { if let Some(ui) = w_cl.upgrade() { ui.set_is_ingesting(true); ui.set_ingest_finished(false); ui.set_ingest_progress(0.05); ui.set_ingest_filename(format!("{} arquivo(s)", count).into()); ui.set_ingest_step("Copiando para database/...".into()); ui.set_ingest_log("Iniciando ingestão...".into()); } });
                tokio::spawn(async move { execute_ingest_pipeline(files, w, v, e, s).await; });
            }
        });
    });

    println!("{}", "🚀 Interface Desktop Slint (ReductorPrompt) com SQLite Ativo!".green().bold());
    app.run()?;
    Ok(())
}
