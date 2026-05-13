package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/mux"
	"github.com/user/devops-ml-orchestrator/internal/models"
	"github.com/user/devops-ml-orchestrator/internal/queue"
)

type Handler struct {
	Orchestrator *queue.Orchestrator
	DataDir      string
	TrainerURL   string
}

func (h *Handler) RegisterRoutes(r *mux.Router) {
	r.HandleFunc("/train", h.HandleTrain).Methods("POST", "OPTIONS")
	r.HandleFunc("/status/{id}", h.HandleStatus).Methods("GET")
	r.HandleFunc("/jobs", h.HandleListJobs).Methods("GET")
	r.HandleFunc("/health", h.HandleHealth).Methods("GET")
	r.HandleFunc("/inference", h.HandleInference).Methods("POST", "OPTIONS")
	r.Use(corsMiddleware)
}

// corsMiddleware adds CORS headers for frontend
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// HandleTrain accepts dataset_text (raw text) or dataset_path, creates job
func (h *Handler) HandleTrain(w http.ResponseWriter, r *http.Request) {
	var req struct {
		DatasetText  string  `json:"dataset_text"`
		DatasetPath  string  `json:"dataset_path"`
		Epochs       int     `json:"epochs"`
		LearningRate float64 `json:"learning_rate"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Default values
	if req.Epochs == 0 {
		req.Epochs = 1
	}
	if req.LearningRate == 0 {
		req.LearningRate = 1e-4
	}

	// If raw text was sent, save it to the shared data dir
	datasetPath := req.DatasetPath
	if req.DatasetText != "" {
		jobID := uuid.New().String()
		filename := filepath.Join(h.DataDir, jobID+".txt")
		if err := os.MkdirAll(h.DataDir, 0755); err == nil {
			os.WriteFile(filename, []byte(req.DatasetText), 0644)
			datasetPath = filename
		}
	}

	job := &models.TrainingJob{
		ID:           uuid.New().String(),
		DatasetPath:  datasetPath,
		Epochs:       req.Epochs,
		LearningRate: req.LearningRate,
		Status:       models.StatusQueued,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}

	h.Orchestrator.SubmitJob(job)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(job)
}

func (h *Handler) HandleStatus(w http.ResponseWriter, r *http.Request) {
	id := mux.Vars(r)["id"]
	job, ok := h.Orchestrator.GetJob(id)
	if !ok {
		http.Error(w, `{"error":"Job not found"}`, http.StatusNotFound)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(job)
}

func (h *Handler) HandleListJobs(w http.ResponseWriter, r *http.Request) {
	jobs := h.Orchestrator.GetAllJobs()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(jobs)
}

func (h *Handler) HandleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintln(w, `{"status":"ok","service":"go-api"}`)
}

// HandleInference proxies inference requests to Python trainer
func (h *Handler) HandleInference(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request", http.StatusBadRequest)
		return
	}

	resp, err := http.Post(h.TrainerURL+"/inference", "application/json", bytes.NewBuffer(body))
	if err != nil {
		http.Error(w, fmt.Sprintf(`{"error":"Trainer unreachable: %v"}`, err), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}
