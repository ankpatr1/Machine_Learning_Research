import g4f
import json
import os
import sys
from dotenv import load_dotenv
from g4f.errors import RetryProviderError, ResponseStatusError

load_dotenv()

# Configurations
models = [
    "gpt-4", "gpt-4o", "gpt-4o-mini",
    "llama-3.1-8b", "llama-3.1-70b", "llama-3.1-405b",
    "gemini-1.5-flash"
]
prompt_style = ["tree_of_thought"]
question_type = "problem_solving"

# Tree of Thought prompt template for SAT problem solving
def tree_of_thought_prompt_sat(q):
    question = q.get("question", "")
    choices = q.get("options", [])
    # Build prompt with question and choices
    prompt = f"""
You are an expert SAT problem-solving tutor.
Use the Tree-of-Thought method to solve the following problem step by step.

QUESTION:
{question}

Choices:
"""
    for opt in choices:
        prompt += f"- {opt}\n"
    prompt += "\nProvide your reasoning, and then at the end type 'Answer: <choice>'."
    return prompt


def evaluate_with_g4f(prompt, model):
    try:
        response = g4f.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return response
    except ResponseStatusError as e:
        print(f"⚠️ HTTP error from provider for model {model}: {e}", file=sys.stderr)
    except RetryProviderError as e:
        print(f"⚠️ All providers failed for model {model}: {e}", file=sys.stderr)
    return ""


def evaluate_question(q, model, prompt_style="tree_of_thought"):
    prompt = tree_of_thought_prompt_sat(q)
    print(f"Evaluating Q{q.get('number')} with {model} - {prompt_style}...")
    response = evaluate_with_g4f(prompt, model=model)

    answer_line = next(
        (line for line in response.splitlines()
         if line.strip().lower().startswith("answer:")),
        ""
    )
    predicted_answer = answer_line.split(":", 1)[-1].strip()
    correct = str(predicted_answer).lower() == str(q.get("correct_answer", "")).lower()

    return predicted_answer, correct


def main():
    with open("problem-solving_and_DA.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data.get("questions", [])

    results = {
        "total_questions": len(questions),
        "questions": [],
        "accuracy": {question_type: {}},
        "overall_accuracy": {}
    }

    for model in models:
        results["accuracy"][question_type][model] = {}
        results["overall_accuracy"][model] = {}
        for ps in prompt_style:
            correct_count = 0
            total = 0
            for q in questions:
                predicted, is_correct = evaluate_question(q, model, ps)
                results["questions"].append({
                    "number": q.get("number"),
                    "model": model,
                    "prompt_style": ps,
                    "predicted": predicted,
                    "correct_answer": q.get("correct_answer"),
                    "is_correct": is_correct
                })
                total += 1
                if is_correct:
                    correct_count += 1
            results["accuracy"][question_type][model][ps] = {
                "correct": correct_count,
                "total": total
            }
            results["overall_accuracy"][model][ps] = {
                "correct": correct_count,
                "total": total,
                "accuracy": round((correct_count / total) * 100, 2) if total else 0
            }

    with open("SAT_PS_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\n✅ Results saved to SAT_PS_results.json")


if __name__ == "__main__":
    main()
