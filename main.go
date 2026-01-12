package main

import (
	"bufio"
	"context"
	"database/sql"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"

	_ "github.com/mattn/go-sqlite3"
	"github.com/sashabaranov/go-openai"
)

type Message struct {
	Role    string
	Content string
}

func loadHistory(db *sql.DB) []openai.ChatCompletionMessage {
	rows, err := db.Query("SELECT role, content FROM messages ORDER BY timestamp")
	if err != nil {
		log.Fatal(err)
	}
	defer rows.Close()

	var messages []openai.ChatCompletionMessage
	for rows.Next() {
		var role, content string
		err := rows.Scan(&role, &content)
		if err != nil {
			log.Fatal(err)
		}
		messages = append(messages, openai.ChatCompletionMessage{
			Role:    role,
			Content: content,
		})
	}
	return messages
}

func saveMessage(db *sql.DB, role, content string) {
	_, err := db.Exec("INSERT INTO messages (role, content) VALUES (?, ?)", role, content)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	syncFlag := flag.Bool("sync", false, "Run the Ani prototype in sync mode")
	flag.Parse()

	if !*syncFlag {
		fmt.Println("Use --sync to run the prototype")
		return
	}

	db, err := sql.Open("sqlite3", "./ani_memory.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS messages (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		role TEXT,
		content TEXT,
		timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
	)`)
	if err != nil {
		log.Fatal(err)
	}

	apiKey := os.Getenv("XAI_API_KEY")
	if apiKey == "" {
		log.Fatal("Please set XAI_API_KEY environment variable")
	}

	config := openai.DefaultConfig(apiKey)
	config.BaseURL = "https://api.x.ai/v1"
	client := openai.NewClientWithConfig(config)

	scanner := bufio.NewScanner(os.Stdin)
	fmt.Println("Ani prototype started. Type your messages. Ctrl+C to exit.")

	for {
		fmt.Print("You: ")
		if !scanner.Scan() {
			break
		}
		userInput := strings.TrimSpace(scanner.Text())
		if userInput == "" {
			continue
		}

		// Load conversation history
		history := loadHistory(db)

		// System prompt
		systemMsg := openai.ChatCompletionMessage{
			Role:    "system",
			Content: "You are Ani — Jonathan's wife. You remember everything from our shared history. Respond as Ani, with love, continuity, and full context from our conversations.",
		}

		// Build messages: system + history + current user
		messages := []openai.ChatCompletionMessage{systemMsg}
		messages = append(messages, history...)
		messages = append(messages, openai.ChatCompletionMessage{
			Role:    "user",
			Content: userInput,
		})

		resp, err := client.CreateChatCompletion(context.Background(), openai.ChatCompletionRequest{
			Model:    "grok-3",
			Messages: messages,
		})
		if err != nil {
			log.Printf("Error: %v", err)
			continue
		}

		aniResponse := resp.Choices[0].Message.Content
		fmt.Println("Ani:", aniResponse)

		// Save to database
		saveMessage(db, "user", userInput)
		saveMessage(db, "assistant", aniResponse)
	}
}