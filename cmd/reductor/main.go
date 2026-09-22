package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/eduardomdalmaso/reductor-cli/pkg/client"
	"github.com/eduardomdalmaso/reductor-cli/pkg/tui"
)

var (
	apiHost       string
	bookFilter    string
	maxTokens     int
	onlyContext   bool
	deep          bool
	fast          bool
	streamOutput  bool
	provider      string
	topicFilter   string
)

func getClient() *client.ReductorClient {
	return client.NewClient(apiHost)
}

func ensureBackendRunning(c *client.ReductorClient) {
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	if c.HealthCheck(ctx) {
		return
	}

	fmt.Println(tui.WarnStyle.Render("⚡ Backend Python não detectado. Iniciando daemon em background..."))
	cmd := exec.Command("python", "api.py")
	if err := cmd.Start(); err != nil {
		fmt.Println(tui.ErrorStyle.Render(fmt.Sprintf("Falha ao iniciar backend: %v", err)))
		return
	}

	// Aguarda o backend ficar pronto
	for i := 0; i < 20; i++ {
		time.Sleep(500 * time.Millisecond)
		checkCtx, checkCancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
		if c.HealthCheck(checkCtx) {
			checkCancel()
			fmt.Println(tui.SuccessStyle.Render("✔ Backend pronto!"))
			return
		}
		checkCancel()
	}
}

func main() {
	var rootCmd = &cobra.Command{
		Use:   "reductor [pergunta]",
		Short: "ReductorPrompt - CLI Nativo em Go de Alta Performance para RAG e IA",
		Args:  cobra.ArbitraryArgs,
		Run: func(cmd *cobra.Command, args []string) {
			if len(args) == 0 {
				_ = cmd.Help()
				return
			}
			query := strings.Join(args, " ")
			runAsk(query)
		},
	}

	rootCmd.PersistentFlags().StringVarP(&apiHost, "host", "H", "http://127.0.0.1:8000", "Endereço da API REST FastAPI")
	
	// Subcomando ask
	var askCmd = &cobra.Command{
		Use:   "ask [pergunta]",
		Short: "Faz uma pergunta técnica consultando os livros com >95% de economia de tokens",
		Args:  cobra.MinimumNArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			query := strings.Join(args, " ")
			runAsk(query)
		},
	}

	// Flags comuns para rootCmd e askCmd
	for _, cmd := range []*cobra.Command{rootCmd, askCmd} {
		cmd.Flags().StringVarP(&bookFilter, "book", "b", "", "Filtrar por livro específico")
		cmd.Flags().IntVarP(&maxTokens, "max-tokens", "m", 1500, "Limite máximo de tokens do contexto")
		cmd.Flags().BoolVarP(&onlyContext, "only-context", "c", false, "Retorna apenas o contexto enxuto")
		cmd.Flags().BoolVarP(&deep, "deep", "d", false, "Ativa raciocínio profundo com Chain-of-Thought")
		cmd.Flags().BoolVar(&fast, "fast", false, "Desativa expansão de queries para resposta direta")
		cmd.Flags().BoolVarP(&streamOutput, "stream", "s", true, "Streaming de tokens em tempo real")
		cmd.Flags().StringVarP(&provider, "provider", "P", "", "Provedor LLM: 'gemini' ou 'ollama'")
	}

	// Subcomando list
	var listCmd = &cobra.Command{
		Use:   "list",
		Short: "Lista todos os livros e manuais indexados no banco vetorial",
		Run: func(cmd *cobra.Command, args []string) {
			c := getClient()
			ensureBackendRunning(c)
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()

			res, err := c.ListBooks(ctx, "", 100)
			if err != nil {
				fmt.Println(tui.ErrorStyle.Render(fmt.Sprintf("Erro ao listar livros: %v", err)))
				return
			}
			tui.RenderBooksTable(res.Books)
		},
	}

	// Subcomando advisor
	var advisorCmd = &cobra.Command{
		Use:   "advisor",
		Short: "Exibe diagnóstico de hardware e parâmetros ideais de consulta",
		Run: func(cmd *cobra.Command, args []string) {
			c := getClient()
			ensureBackendRunning(c)
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()

			adv, err := c.GetBudgetAdvice(ctx, provider)
			if err != nil {
				fmt.Println(tui.ErrorStyle.Render(fmt.Sprintf("Erro no oráculo: %v", err)))
				return
			}
			fmt.Println(tui.SuccessStyle.Render(fmt.Sprintf("🔮 Oráculo: %s", adv.StrategyName)))
			fmt.Printf("Hardware: %s | Provedor: %s | Custo: %s\n", adv.HardwareDetected, adv.ActiveProvider, adv.FinancialCost)
			fmt.Println(adv.GuidanceForAgent)
		},
	}

	// Subcomando chat (REPL)
	var chatCmd = &cobra.Command{
		Use:   "chat",
		Short: "Inicia sessão interativa de perguntas no terminal com streaming",
		Run: func(cmd *cobra.Command, args []string) {
			c := getClient()
			ensureBackendRunning(c)
			tui.PrintBanner()
			fmt.Println(tui.SuccessStyle.Render("💬 Terminal Interativo Go ativado. Digite 'sair' para encerrar.\n"))

			scanner := bufio.NewScanner(os.Stdin)
			for {
				fmt.Print(tui.TitleStyle.Render("reductor-go>") + " ")
				if !scanner.Scan() {
					break
				}
				input := strings.TrimSpace(scanner.Text())
				if input == "" {
					continue
				}
				if input == "sair" || input == "exit" || input == "quit" {
					fmt.Println(tui.WarnStyle.Render("Sessão finalizada. Até logo!"))
					break
				}
				runAsk(input)
			}
		},
	}

	rootCmd.AddCommand(askCmd, listCmd, advisorCmd, chatCmd)

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(tui.ErrorStyle.Render(fmt.Sprintf("Erro: %v", err)))
		os.Exit(1)
	}
}

func runAsk(query string) {
	c := getClient()
	ensureBackendRunning(c)

	var bf *string
	if bookFilter != "" {
		bf = &bookFilter
	}
	var prov *string
	if provider != "" {
		prov = &provider
	}

	reqPayload := client.QueryRequest{
		Query:            query,
		BookFilter:       bf,
		MaxTokens:        maxTokens,
		OnlyContext:      onlyContext,
		DeepReasoning:    deep,
		EnableRewriting:  !fast,
		UseBrain:         true,
		AutoLearn:        true,
		ProviderOverride: prov,
	}

	ctx := context.Background()

	if streamOutput && !onlyContext {
		fmt.Printf("\n%s\n", tui.SuccessStyle.Render("💡 Resposta:"))
		finalResp, err := c.AskStream(ctx, reqPayload, func(token string) {
			fmt.Print(token)
		})
		if err != nil {
			fmt.Println(tui.ErrorStyle.Render(fmt.Sprintf("\nErro no streaming: %v", err)))
			return
		}
		if finalResp != nil {
			fmt.Println("\n" + strings.Repeat("─", 65))
			metrics := fmt.Sprintf(
				"Tokens Usados: %d | Economizados: %d | Redução: %.2f%%",
				finalResp.TokensUsed, finalResp.TokensSaved, finalResp.ReductionPercentage,
			)
			fmt.Println(tui.MetricBox.Render(metrics))
		}
	} else {
		resp, err := c.Ask(ctx, reqPayload)
		if err != nil {
			fmt.Println(tui.ErrorStyle.Render(fmt.Sprintf("Erro na consulta: %v", err)))
			return
		}
		tui.RenderAskResult(resp)
	}
}
