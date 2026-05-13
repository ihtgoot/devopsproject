from flask import Flask, request, jsonify
import threading
import uuid
import time
import os
from train import run_training
from unsloth import FastLanguageModel
import torch

app = Flask(__name__)

# Shared state for tracking training progress
jobs = {}

@app.route('/train', methods=['POST'])
def train():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    job_id = data.get('job_id', str(uuid.uuid4()))
    dataset_path = data.get('dataset_path')
    epochs = data.get('epochs', 1)
    lr = data.get('lr', 1e-4)

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "start_time": time.time()
    }

    # Start training in a separate thread to keep the API responsive
    thread = threading.Thread(target=run_training, args=(job_id, dataset_path, epochs, lr, jobs))
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"}), 202

@app.route('/status/<job_id>', methods=['GET'])
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route('/inference', methods=['POST'])
def inference():
    data = request.json
    model_name = data.get('model_id', "psychotic_uncle_lora")
    instruction = data.get('instruction', "what is life ?")
    
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = model_name,
            max_seq_length = 1024,
            load_in_4bit = True,
        )
        FastLanguageModel.for_inference(model)
        
        formatted_prompt = f"### Instruction:\n{instruction}\n\n### Response:\n"
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
            
        return jsonify({"response": clean_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "up"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
