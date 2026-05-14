from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import time
import os
import uvicorn
from train import run_training
from unsloth import FastLanguageModel
import torch
from typing import Optional

app = FastAPI()

# Shared state for tracking training progress
jobs = {}

class TrainRequest(BaseModel):
    job_id: Optional[str] = None
    dataset_path: Optional[str] = None
    epochs: Optional[int] = 1
    lr: Optional[float] = 1e-4

@app.post('/train', status_code=202)
def train(req: TrainRequest, background_tasks: BackgroundTasks):
    job_id = req.job_id or str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "start_time": time.time()
    }

    # Start training in a background task to keep the API responsive
    background_tasks.add_task(run_training, job_id, req.dataset_path, req.epochs, req.lr, jobs)

    return {"job_id": job_id, "status": "queued"}

@app.get('/status/{job_id}')
def status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

class InferenceRequest(BaseModel):
    model_id: Optional[str] = "psychotic_uncle_lora"
    instruction: Optional[str] = "what is life ?"

@app.post('/inference')
def inference(req: InferenceRequest):
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = req.model_id,
            max_seq_length = 1024,
            load_in_4bit = True,
        )
        FastLanguageModel.for_inference(model)
        
        formatted_prompt = f"### Instruction:\n{req.instruction}\n\n### Response:\n"
        inputs = tokenizer(formatted_prompt, return_tensors="pt").to("cuda")
        
        outputs = model.generate(
            **inputs,
            max_new_tokens = 200,
            temperature = 0.8,
            do_sample = True,
        )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens = True)
        if "### Response:" in response:
            clean_response = response.split("### Response:")[1].strip()
        else:
            clean_response = response[len(formatted_prompt):].strip()
            
        return {"response": clean_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/health')
def health():
    return {"status": "up"}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
