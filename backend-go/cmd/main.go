package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
	"github.com/user/devops-ml-orchestrator/internal/api"
	"github.com/user/devops-ml-orchestrator/internal/queue"
)

func main() {
	trainerURL := os.Getenv("TRAINER_URL")
	if trainerURL == "" {
		trainerURL = "http://trainer:8000"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		dataDir = "/data/datasets"
	}

	orchestrator := queue.NewOrchestrator(trainerURL)
	orchestrator.StartWorker()

	handler := &api.Handler{
		Orchestrator: orchestrator,
		DataDir:      dataDir,
		TrainerURL:   trainerURL,
	}

	r := mux.NewRouter()
	handler.RegisterRoutes(r)

	log.Printf("Go API starting on :%s — Trainer: %s", port, trainerURL)
	log.Fatal(http.ListenAndServe(":"+port, r))
}
