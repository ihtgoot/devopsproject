import os
import time
import logging
from datasets import Dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_dataset_from_path(dataset_path: str) -> Dataset:
    """Load a plain text or JSON lines file into a HuggingFace Dataset."""
    if dataset_path and os.path.exists(dataset_path):
        if dataset_path.endswith(".jsonl") or dataset_path.endswith(".json"):
            import json
            records = []
            with open(dataset_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            # Expect {"text": "..."} records
            return Dataset.from_list(records)
        else:
            # Plain text: each non-empty line becomes one training example
            with open(dataset_path) as f:
                lines = [{"text": l.strip()} for l in f if l.strip()]
            return Dataset.from_list(lines) if lines else _demo_dataset()
    else:
        logger.warning("Dataset path invalid or missing — using built-in demo dataset")
        return _demo_dataset()


def _demo_dataset() -> Dataset:
    """Tiny synthetic dataset used for demo / CI runs."""
    examples = [
        {"text": "### Instruction:\nWhat is Docker?\n\n### Response:\nDocker is a container platform that packages apps with their dependencies."},
        {"text": "### Instruction:\nWhat is a Dockerfile?\n\n### Response:\nA Dockerfile is a text file with instructions to build a Docker image."},
        {"text": "### Instruction:\nWhat is Docker Compose?\n\n### Response:\nDocker Compose lets you define and run multi-container apps with a YAML file."},
        {"text": "### Instruction:\nWhat is Jenkins?\n\n### Response:\nJenkins is an open-source automation server used for CI/CD pipelines."},
        {"text": "### Instruction:\nWhat is LoRA?\n\n### Response:\nLoRA is a parameter-efficient fine-tuning method that adds trainable low-rank matrices to model weights."},
    ]
    return Dataset.from_list(examples)


def run_training(job_id: str, dataset_path: str, epochs: int, lr: float, status_dict: dict):
    logger.info(f"[{job_id}] Starting training — epochs={epochs}, lr={lr}")
    status_dict[job_id]["status"] = "running"
    status_dict[job_id]["progress"] = 0

    try:
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments

        # 1 ─ Load base model
        logger.info(f"[{job_id}] Loading model…")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name="unsloth/gemma-3-4b-it-bnb-4bit",
            max_seq_length=2048,
            load_in_4bit=True,
        )

        # 2 ─ Attach LoRA adapters
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                             "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
        )

        # 3 ─ Load dataset
        dataset = _load_dataset_from_path(dataset_path)
        logger.info(f"[{job_id}] Dataset loaded: {len(dataset)} examples")

        # 4 ─ Train
        output_dir = f"/data/outputs/{job_id}"
        os.makedirs(output_dir, exist_ok=True)

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=2048,
            dataset_num_proc=1,
            packing=False,
            args=TrainingArguments(
                per_device_train_batch_size=1,
                gradient_accumulation_steps=4,
                warmup_steps=2,
                num_train_epochs=epochs,
                max_steps=max(10, epochs * len(dataset)),  # safety cap for demo
                learning_rate=lr,
                fp16=True,
                logging_steps=1,
                optim="adamw_8bit",
                weight_decay=0.01,
                lr_scheduler_type="linear",
                seed=3407,
                output_dir=output_dir,
                report_to="none",
            ),
        )

        # Patch progress into status_dict via a callback
        total_steps = trainer.args.max_steps
        original_log = trainer.log

        def _log_with_progress(logs):
            step = trainer.state.global_step
            status_dict[job_id]["progress"] = round((step / total_steps) * 100, 1)
            status_dict[job_id]["current_step"] = step
            original_log(logs)

        trainer.log = _log_with_progress
        trainer.train()

        # 5 ─ Save adapter
        model_path = f"/data/models/{job_id}_lora"
        os.makedirs(model_path, exist_ok=True)
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)

        status_dict[job_id].update({
            "status": "completed",
            "progress": 100,
            "model_path": model_path,
        })
        logger.info(f"[{job_id}] Completed — adapter saved to {model_path}")

    except Exception as e:
        logger.error(f"[{job_id}] Training failed: {e}", exc_info=True)
        status_dict[job_id]["status"] = "failed"
        status_dict[job_id]["error"] = str(e)
