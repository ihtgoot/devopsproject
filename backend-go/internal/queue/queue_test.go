package queue_test

import (
	"fmt"
	"testing"
	"time"

	"github.com/user/devops-ml-orchestrator/internal/models"
	"github.com/user/devops-ml-orchestrator/internal/queue"
)

func TestSubmitAndGetJob(t *testing.T) {
	orc := queue.NewOrchestrator("http://localhost:9999") // unreachable trainer is fine for unit tests
	orc.StartWorker()

	job := &models.TrainingJob{
		ID:           "test-job-123",
		DatasetPath:  "/tmp/test.txt",
		Epochs:       1,
		LearningRate: 1e-4,
		Status:       models.StatusQueued,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}

	orc.SubmitJob(job)

	time.Sleep(100 * time.Millisecond) // let the goroutine pick it up

	got, ok := orc.GetJob("test-job-123")
	if !ok {
		t.Fatal("job not found after submit")
	}
	if got.ID != "test-job-123" {
		t.Errorf("expected ID test-job-123, got %s", got.ID)
	}
}

func TestGetAllJobs(t *testing.T) {
	orc := queue.NewOrchestrator("http://localhost:9999")

	for i := 0; i < 3; i++ {
		job := &models.TrainingJob{
			ID:        fmt.Sprintf("job-%d", i),
			Status:    models.StatusQueued,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
		}
		orc.SubmitJob(job)
	}

	jobs := orc.GetAllJobs()
	if len(jobs) != 3 {
		t.Errorf("expected 3 jobs, got %d", len(jobs))
	}
}
