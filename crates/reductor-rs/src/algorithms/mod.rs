use std::collections::HashMap;
use crate::domain::{ScoredChunk, TokenBudgetResult};

pub struct AdaptiveRRFEngine;

impl AdaptiveRRFEngine {
    /// Fusão de múltiplos rankings de busca usando Reciprocal Rank Fusion (RRF)
    #[allow(dead_code)]
    pub fn fuse_rankings(rankings: Vec<Vec<ScoredChunk>>, rrf_k: f32) -> Vec<ScoredChunk> {
        if rankings.is_empty() {
            return Vec::new();
        }
        if rankings.len() == 1 {
            return rankings.into_iter().next().unwrap();
        }

        let mut rrf_scores: HashMap<String, f32> = HashMap::new();
        let mut chunk_map: HashMap<String, ScoredChunk> = HashMap::new();

        for rank_list in rankings {
            for (pos, item) in rank_list.into_iter().enumerate() {
                let rank = (pos + 1) as f32;
                let score = 1.0 / (rrf_k + rank);
                *rrf_scores.entry(item.chunk.id.clone()).or_insert(0.0) += score;
                chunk_map.entry(item.chunk.id.clone()).or_insert(item);
            }
        }

        let mut fused: Vec<ScoredChunk> = chunk_map
            .into_iter()
            .map(|(id, mut chunk)| {
                chunk.similarity_score = *rrf_scores.get(&id).unwrap_or(&0.0);
                chunk
            })
            .collect();

        fused.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap_or(std::cmp::Ordering::Equal));

        for (idx, item) in fused.iter_mut().enumerate() {
            item.rank_position = idx + 1;
        }

        fused
    }

    /// Aplica o corte por cotovelo (Elbow Method) e orçamento dinâmico de tokens
    pub fn apply_elbow_and_budget(
        scored_chunks: Vec<ScoredChunk>,
        max_tokens: usize,
        max_relative_drop: f32, // ex: 0.35 (35% de queda em relação ao pico)
        max_step_drop: f32,     // ex: 0.22 (22% de queda abrupta de um para o outro)
    ) -> TokenBudgetResult {
        if scored_chunks.is_empty() {
            return TokenBudgetResult {
                selected_chunks: Vec::new(),
                total_tokens_used: 0,
                total_tokens_saved: 0,
                reduction_percentage: 100.0,
            };
        }

        let peak_score = scored_chunks[0].similarity_score;
        let mut selected = Vec::new();
        let mut current_tokens = 0;
        let mut prev_score = peak_score;

        for sc in scored_chunks {
            // Verifica corte por degrau abrupto
            let step_drop = prev_score - sc.similarity_score;
            if prev_score > 0.0 && (step_drop / prev_score) > max_step_drop && !selected.is_empty() {
                break; // Corta cauda ruidosa
            }

            // Verifica corte relativo ao pico
            if peak_score > 0.0 && ((peak_score - sc.similarity_score) / peak_score) > max_relative_drop && !selected.is_empty() {
                break; // Relevância caiu muito em relação ao melhor resultado
            }

            // Verifica orçamento máximo de tokens
            if current_tokens + sc.chunk.token_count > max_tokens && !selected.is_empty() {
                break;
            }

            current_tokens += sc.chunk.token_count;
            prev_score = sc.similarity_score;
            selected.push(sc);
        }

        // Estimativa de tokens totais economizados (comparado à leitura de capítulos inteiros ~75.000 tokens)
        let baseline_tokens = 75_000;
        let tokens_saved = if baseline_tokens > current_tokens { baseline_tokens - current_tokens } else { 0 };
        let reduction_pct = if baseline_tokens > 0 {
            (tokens_saved as f32 / baseline_tokens as f32) * 100.0
        } else {
            0.0
        };

        TokenBudgetResult {
            selected_chunks: selected,
            total_tokens_used: current_tokens,
            total_tokens_saved: tokens_saved,
            reduction_percentage: reduction_pct,
        }
    }
}
