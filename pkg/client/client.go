package client

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// ReductorClient encapsula a comunicação HTTP/SSE com o backend ReductorPrompt
type ReductorClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

// NewClient cria uma nova instância do cliente
func NewClient(baseURL string) *ReductorClient {
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8000"
	}
	return &ReductorClient{
		BaseURL: strings.TrimRight(baseURL, "/"),
		HTTPClient: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

// HealthCheck verifica se o backend Python está ativo
func (c *ReductorClient) HealthCheck(ctx context.Context) bool {
	req, err := http.NewRequestWithContext(ctx, "GET", c.BaseURL+"/api/v1/health", nil)
	if err != nil {
		return false
	}
	client := &http.Client{Timeout: 800 * time.Millisecond}
	resp, err := client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

// Ask executa uma consulta síncrona retornando a resposta completa
func (c *ReductorClient) Ask(ctx context.Context, reqPayload QueryRequest) (*QueryResponse, error) {
	data, err := json.Marshal(reqPayload)
	if err != nil {
		return nil, fmt.Errorf("erro ao serializar requisição: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.BaseURL+"/api/v1/query", bytes.NewBuffer(data))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("falha ao conectar no backend ReductorPrompt (%s): %w", c.BaseURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("erro da API (HTTP %d): %s", resp.StatusCode, string(body))
	}

	var result QueryResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("erro ao decodificar resposta JSON: %w", err)
	}
	return &result, nil
}

// AskStream executa consulta com Server-Sent Events (SSE) emitindo tokens em tempo real
func (c *ReductorClient) AskStream(ctx context.Context, reqPayload QueryRequest, onToken func(string)) (*QueryResponse, error) {
	data, err := json.Marshal(reqPayload)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.BaseURL+"/api/v1/query/stream", bytes.NewBuffer(data))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")

	client := &http.Client{Timeout: 0} // Sem timeout global para streaming longo
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("falha na conexão de streaming com o backend: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("erro da API no streaming (HTTP %d): %s", resp.StatusCode, string(body))
	}

	scanner := bufio.NewScanner(resp.Body)
	var finalResponse *QueryResponse

	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "data: ") {
			rawJSON := strings.TrimPrefix(line, "data: ")
			var event map[string]any
			if err := json.Unmarshal([]byte(rawJSON), &event); err == nil {
				if t, ok := event["type"].(string); ok {
					if t == "token" {
						if content, ok := event["content"].(string); ok {
							onToken(content)
						}
					} else if t == "final" {
						if respData, ok := event["data"]; ok {
							rawFinal, _ := json.Marshal(respData)
							var qr QueryResponse
							if err := json.Unmarshal(rawFinal, &qr); err == nil {
								finalResponse = &qr
							}
						}
					}
				}
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("erro no canal de streaming SSE: %w", err)
	}
	return finalResponse, nil
}

// Analyze executa uma análise cruzada de projeto
func (c *ReductorClient) Analyze(ctx context.Context, reqPayload AnalyzeRequest) (*AnalyzeResponse, error) {
	data, err := json.Marshal(reqPayload)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.BaseURL+"/api/v1/analyze", bytes.NewBuffer(data))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("erro da API (HTTP %d): %s", resp.StatusCode, string(body))
	}

	var result AnalyzeResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListBooks lista os livros indexados no banco vetorial
func (c *ReductorClient) ListBooks(ctx context.Context, filter string, limit int) (*BooksListResponse, error) {
	url := fmt.Sprintf("%s/api/v1/books?limit=%d", c.BaseURL, limit)
	if filter != "" {
		url += "&query=" + filter
	}

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("erro ao listar livros (HTTP %d): %s", resp.StatusCode, string(body))
	}

	var result BooksListResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return &result, nil
}

// GetBudgetAdvice consulta o oráculo de telemetria de hardware
func (c *ReductorClient) GetBudgetAdvice(ctx context.Context, provider string) (*HardwareAdvice, error) {
	url := c.BaseURL + "/api/v1/hardware/budget-advice"
	if provider != "" {
		url += "?provider=" + provider
	}

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("erro no oráculo de hardware (HTTP %d): %s", resp.StatusCode, string(body))
	}

	var result HardwareAdvice
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return &result, nil
}
