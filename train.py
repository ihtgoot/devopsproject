from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import torch


model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = ".",
    max_seq_length = 512,
    dtype = None,
    load_in_4bit = True,
)


model = FastLanguageModel.get_peft_model(
    model,
    r = 64, 
    target_modules = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha = 64,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
)

dataset = load_dataset(
    "json",
    data_files = "dataset.jsonl",
    split = "train"
)


def format_example(example):
    # For Instruct models, it helps to have a clear 'Uncle' indicator
    text = f"### Instruction: {example['instruction']}\n### Response: {example['output']}"
    return { "text": text }

dataset = dataset.map(format_example)

# 5. Trainer Configuration
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = 2048,
    packing = True,
    args = TrainingArguments(
        per_device_train_batch_size = 8,      
        gradient_accumulation_steps = 2,

        warmup_steps = 10,
        num_train_epochs = 2,               

        learning_rate = 1e-4,               
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(), 

        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        output_dir = "outputs",
        save_strategy = "no",               
    ),
)

# 6. Train and Save Adapters
trainer.train()

model.save_pretrained("psychotic_uncle_lora")
tokenizer.save_pretrained("psychotic_uncle_lora")