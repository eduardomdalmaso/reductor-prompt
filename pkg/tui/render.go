package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/eduardomdalmaso/reductor-cli/pkg/client"
)

var (
	// Paleta de Estilos Lipgloss
	TitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#00FFFF")).
			Background(lipgloss.Color("#1F1F2E")).
			Padding(0, 1).
			MarginBottom(1)

	AnswerStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#E0E0E0")).
			MarginTop(1).
			MarginBottom(1)

	MetricBox = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#7D56F4")).
			Padding(0, 1).
			MarginTop(1)

	SourceStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFA500")).
			MarginTop(1)

	SuccessStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#00FF66"))

	WarnStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FFCC00"))

	ErrorStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FF3366"))
)

// PrintBanner exibe o cabeçalho moderno da CLI em Go
func PrintBanner() {
	banner := TitleStyle.Render("📚 ReductorPrompt CLI (Go Native v2.0)")
	fmt.Println(banner)
}

// RenderAskResult renderiza o resultado da consulta com métricas e fontes
func RenderAskResult(resp *client.QueryResponse) {
	if resp == nil {
		return
	}

	fmt.Println("\n" + SuccessStyle.Render("💡 Resposta:"))
	fmt.Println(AnswerStyle.Render(resp.Response))
	fmt.Println(strings.Repeat("─", 65))

	// Métricas de Economia de Tokens
	origin := "📚 RAG 194+ Livros"
	if resp.FromBrain {
		origin = "🧠 Cérebro Episódico (<2ms)"
	}

	metrics := fmt.Sprintf(
		"Tokens Usados: %d  |  Tokens Economizados: %d  |  Redução: %.2f%%  |  Origem: %s",
		resp.TokensUsed, resp.TokensSaved, resp.ReductionPercentage, origin,
	)
	fmt.Println(MetricBox.Render(metrics))

	// Fontes Citadas
	if len(resp.Sources) > 0 {
		fmt.Println("\n" + SourceStyle.Render("📖 Fontes Consultadas:"))
		for _, s := range resp.Sources {
			loc := ""
			if s.Chapter != "" {
				loc = fmt.Sprintf(" (%s", s.Chapter)
				if s.Page > 0 {
					loc += fmt.Sprintf(", Pág %d", s.Page)
				}
				loc += ")"
			}
			fmt.Printf(" • %s%s - Similaridade: %.3f\n", s.BookTitle, loc, s.Score)
		}
	}
	fmt.Println()
}

// RenderBooksTable renderiza a lista de livros disponíveis
func RenderBooksTable(books []client.BookItem) {
	if len(books) == 0 {
		fmt.Println(WarnStyle.Render("Nenhum livro indexado no banco vetorial."))
		return
	}

	fmt.Printf("\n%s (Total: %d obras)\n", SuccessStyle.Render("📚 Livros e Manuais no Banco Vetorial:"), len(books))
	fmt.Println(strings.Repeat("─", 75))
	for _, b := range books {
		idShort := b.BookID
		if len(idShort) > 12 {
			idShort = idShort[:12] + "..."
		}
		fmt.Printf(" [%s] %-52s (%3d chunks)\n", idShort, b.Title, b.ChunksCount)
	}
	fmt.Println(strings.Repeat("─", 75) + "\n")
}
