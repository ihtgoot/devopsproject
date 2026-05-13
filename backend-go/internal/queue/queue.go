package queue

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/user/devops-ml-orchestrator/internal/models"
)

type Orchestrator struct {
	JobQueue chan *models.TrainingJob
	Jobs     map[string]*models.TrainingJob
	mu       sync.RWMutex
	trainerURL string
}

func NewOrchestrator(trainerURL string) *Orchestrator {
	return &Orchestrator{
		JobQueue:   make(chan *models.TrainingJob, 100),
		Jobs:       make(map[string]*models.TrainingJob),
		trainerURL: trainerURL,
	}
}

func (o *Orchestrator) SubmitJob(job *models.TrainingJob) {
	o.mu.Lock()
	o.Jobs[job.ID] = job
	o.mu.Unlock()
	o.JobQueue <- job
}

func (o *Orchestrator) GetJob(id string) (*models.TrainingJob, bool) {
	o.mu.RLock()
	defer o.mu.RUnlock()
	job, ok := o.Jobs[id]
	return job, ok
}

func (o *Orchestrator) GetAllJobs() []*models.TrainingJob {
	o.mu.RLock()
	defer o.mu.RUnlock()
	jobs := make([]*models.TrainingJob, 0, len(o.Jobs))
	for _, job := range o.Jobs {
		jobs = append(jobs, job)
	}
	return jobs
}

func (o *Orchestrator) StartWorker() {
	go func() {
		for job := range o.JobQueue {
			o.processJob(job)
		}
	}()
}

func (o *Orchestrator) processJob(job *models.TrainingJob) {
	o.updateStatus(job.ID, models.StatusRunning, "")
	log.Printf("Starting job %s", job.ID)

	// Call Python Trainer Service
	payload, _ := json.Marshal(map[string]interface{}{
		"job_id":       job.ID,
		"dataset_path": job.DatasetPath,
		"epochs":       job.Epochs,
		"lr":           job.LearningRate,
	})

	resp, err := http.Post(o.trainerURL+"/train", "application/json", bytes.NewBuffer(payload))
	if err != nil {
		o.updateStatus(job.ID, models.StatusFailed, fmt.Sprintf("Trainer unavailable: %v", err))
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		o.updateStatus(job.ID, models.StatusFailed, fmt.Sprintf("Trainer returned error: %d", resp.StatusCode))
		return
	}

	o.updateStatus(job.ID, models.StatusCompleted, "")
	log.Printf("Finished job %s", job.ID)
}

func (o *Orchestrator) updateStatus(id string, status models.JobStatus, errMsg string) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if job, ok := o.Jobs[id]; ok {
		job.Status = status
		job.UpdatedAt = time.Now()
		job.Error = errMsg
	}
}
