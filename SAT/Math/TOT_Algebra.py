# TOT_ALGEBRA.py
#!/usr/bin/env python3

import g4f
import json
import os
import sys
from dotenv import load_dotenv
from g4f.errors import RetryProviderError, ResponseStatusError

# Load your .env (with API tokens)
load_dotenv()

# === Config ===
models = [
    "gpt-4", "gpt-4o", "gpt-4o-mini",
    "llama-3.1-8b", "llama-3.1-70b", "llama-3.1-405b",
    "gemini-1.5-flash"
]
prompt_styles = ["tree_of_thought"]

input_file  = "Algebra.json"
output_file = "Algebra_results.json"

# === Prompt builder ===
def tree_of_thought_prompt(q):
    question = q.get("question", "")
    choices  = q.get("options") or q.get("choices") or {}
    p  = (
        "You are an expert SAT Algebra tutor.\n"
        "Use the Tree‑of‑Thought method to solve this problem step by step.\n\n"
        f"QUESTION:\n{question}\n\n"
    )
    if isinstance(choices, dict):
        p += "Choices:\n"
        for k,v in choices.items():
            p += f"- {k}: {v}\n"
    elif isinstance(choices, list):
        p += "Choices:\n"
        for opt in choices:
            if isinstance(opt, str):
                p += f"- {opt}\n"
            else:
                lbl = opt.get("label","")
                txt = opt.get("text","")
                p += f"- {lbl}: {txt}\n"
    p += "\nProvide your reasoning, then at the end type 'Answer: <choice>'."
    return p

# === LLM wrapper ===
def evaluate_with_g4f(prompt, model):
    try:
        return g4f.ChatCompletion.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            stream=False
        )
    except ResponseStatusError as e:
        print(f"⚠️ HTTP error for {model}: {e}", file=sys.stderr)
    except RetryProviderError as e:
        print(f"⚠️ Providers failed for {model}: {e}", file=sys.stderr)
    return ""

# === Single-question eval ===
def evaluate_question(q, model):
    prompt = tree_of_thought_prompt(q)
    print(f"Evaluating Q{q.get('number')} with {model}…")
    resp = evaluate_with_g4f(prompt, model)
    ans_line = next((L for L in resp.splitlines() if L.strip().lower().startswith("answer:")), "")
    pred = ans_line.split(":",1)[-1].strip()
    corr = q.get("correct_answer") or q.get("correctAnswer")
    ok = str(pred).lower() == str(corr).lower()
    return pred, ok

# === Main ===
def main():
    # Load questions
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: cannot find {input_file}", file=sys.stderr)
        sys.exit(1)

    qs = data.get("questions") if isinstance(data, dict) else data
    print(f"Loaded {len(qs)} questions from {input_file}\n")

    results = {
        "file": input_file,
        "total_questions": len(qs),
        "questions": [],
        "accuracy": {},
        "overall_accuracy": {}
    }

    for model in models:
        results["accuracy"][model]     = {}
        results["overall_accuracy"][model] = {}
        for style in prompt_styles:
            correct = 0
            for q in qs:
                pred, ok = evaluate_question(q, model)
                results["questions"].append({
                    "number":         q.get("number"),
                    "model":          model,
                    "predicted":      pred,
                    "correct_answer": q.get("correct_answer") or q.get("correctAnswer"),
                    "is_correct":     ok
                })
                if ok: correct += 1
            total = len(qs)
            results["accuracy"][model][style] = {"correct": correct, "total": total}
            results["overall_accuracy"][model][style] = {
                "correct": correct,
                "total": total,
                "accuracy_percent": round(correct/total*100,2) if total else 0
            }

    # Write results
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results saved to {output_file}")

if __name__ == "__main__":
    main()
