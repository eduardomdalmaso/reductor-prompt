package client

// QueryRequest representa o payload enviado ao backend FastAPI (/api/v1/query e /api/v1/query/stream)
type QueryRequest struct {
	Query            string  `json:"query"`
	BookFilter       *string `json:"book_filter,omitempty"`
	MaxTokens        int     `json:"max_tokens"`
	OnlyContext      bool    `json:"only_context"`
	DeepReasoning    bool    `json:"deep_reasoning"`
	EnableRewriting  bool    `json:"enable_rewriting"`
	UseBrain         bool    `json:"use_brain"`
	AutoLearn        bool    `json:"auto_learn"`
	ProviderOverride *string `json:"provider_override,omitempty"`
}

// SourceItem representa uma fonte citada
type SourceItem struct {
	BookTitle string  `json:"book_title"`
	Chapter   string  `json:"chapter"`
	Page      int     `json:"page"`
	Score     float64 `json:"score"`
	Tokens    int     `json:"tokens"`
}

// QueryResponse representa a resposta estruturada do backend
type QueryResponse struct {
	Response            string       `json:"response"`
	Sources             []SourceItem `json:"sources"`
	TokensUsed          int          `json:"tokens_used"`
	TokensSaved         int          `json:"tokens_saved"`
	ReductionPercentage float64      `json:"reduction_percentage"`
	QueryVariations     []string     `json:"query_variations"`
	FromBrain           bool         `json:"from_brain"`
}

// AnalyzeRequest representa a requisição de análise cruzada
type AnalyzeRequest struct {
	ProjectDescription string  `json:"project_description"`
	FocusTopic         *string `json:"focus_topic,omitempty"`
	BookFilter         *string `json:"book_filter,omitempty"`
	MaxTokens          int     `json:"max_tokens"`
	ProviderOverride   *string `json:"provider_override,omitempty"`
}

// TokenStats representa estatísticas de economia de tokens
type TokenStats struct {
	TokensUsed       int     `json:"tokens_used"`
	TokensSaved      int     `json:"tokens_saved"`
	ReductionPercent float64 `json:"reduction_percent"`
}

// AnalyzeResponse representa a resposta da análise cruzada
type AnalyzeResponse struct {
	RawResponse string     `json:"raw_response"`
	TokenStats  TokenStats `json:"token_stats"`
	Sources     []string   `json:"sources"`
}

// BookItem representa um livro indexado no catálogo
type BookItem struct {
	BookID      string `json:"book_id"`
	Title       string `json:"title"`
	ChunksCount int    `json:"chunks_count"`
}

// BooksListResponse representa a lista de livros do banco vetorial
type BooksListResponse struct {
	Books []BookItem `json:"books"`
	Total int        `json:"total"`
}

// HardwareAdvice representa a telemetria de hardware e orçamento
type HardwareAdvice struct {
	RuntimeEnvironment string            `json:"runtime_environment"`
	HardwareDetected   string            `json:"hardware_detected"`
	ActiveProvider     string            `json:"active_provider"`
	StrategyName       string            `json:"strategy_name"`
	FinancialCost      string            `json:"financial_cost"`
	OptimalParameters  map[string]any    `json:"optimal_parameters"`
	GuidanceForAgent   string            `json:"guidance_for_agent"`
}
