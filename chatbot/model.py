import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_PATH = "google/flan-t5-small"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

device = torch.device("cpu")
model.to(device)

def get_answer(question: str) -> str:
    """Generate an answer to *question* using FLAN‑T5‑small.
    The prompt frames the model as a university student‑support assistant.
    """
    prompt = (
        "You are a university student support assistant. "
        "Answer the student's question clearly and concisely. "
        f"Question: {question}"
    )
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=256,
    ).to(device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            num_beams=2,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

if __name__ == "__main__":
    q = input("Ask your university chatbot: ")
    print("Answer:", get_answer(q))
