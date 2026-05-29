from unsloth import FastLanguageModel

# 1. Load the model and tokenizer
# Point model_name to your LoRA folder (e.g., "psychotic_uncle_lora" or "outputs")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "psychotic_uncle_lora", 
    max_seq_length = 1024,
    load_in_4bit = True, # Essential for your 8GB 4060
)

# Enable faster inference
FastLanguageModel.for_inference(model)

# 2. Define the exact prompt format used in training
prompt_style = """### Instruction:
keep the respnsnea s short as you can , be crisp and recise and to the point, , go all low as possible ,
{}

### Response:
"""

# 3. Choose your trigger question
instruction = "what is life ?"
formatted_prompt = f"### Instruction:\n{instruction}\n\n### Response:\nLook, you little"


# 4. Tokenize and Generate
inputs = tokenizer(formatted_prompt, return_tensors="pt").to("cuda")

outputs = model.generate(
    **inputs,
    max_new_tokens = 200,
    temperature = 0.8,           
    top_p = 0.75,
    repetition_penalty = 1.25,    
    no_repeat_ngram_size = 2,    
    do_sample = True,
)

# 5. Robust Output Cleaning
response = tokenizer.decode(outputs[0], skip_special_tokens = True)

print("\n" + "="*40)
print("       PSYCHOTIC UNCLE'S TAKE        ")
print("="*40)

# Split logic that won't crash
if "### Response:" in response:
    clean_response = response.split("### Response:")[1].strip()
    # Sometimes models repeat the header or prompt; this grabs just the new text
    print("Look, you little" + clean_response)
else:
    # Fallback: Print everything generated after the prompt
    print(response[len(formatted_prompt):].strip())

print("="*40 + "\n")