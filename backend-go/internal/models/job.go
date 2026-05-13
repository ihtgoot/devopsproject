package models

import "time"

type JobStatus string

const (
	StatusQueued    JobStatus = "queued"
	StatusRunning   JobStatus = "running"
	StatusCompleted JobStatus = "completed"
	StatusFailed    JobStatus = "failed"
)

type TrainingJob struct {
	ID          string    `json:"id"`
	DatasetPath string    `json:"dataset_path"`
	Epochs      int       `json:"epochs"`
	LearningRate float64  `json:"learning_rate"`
	Status      JobStatus `json:"status"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	Error       string    `json:"error,omitempty"`
}
