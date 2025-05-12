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

# Tree of Thought prompt template for SAT problem solving (generic)
def tree_of_thought_prompt(q):
    question = q.get("question", "")
    choices = q.get("options", [])
    prompt = (
        "You are an expert problem-solving tutor.\n"
        "Use the Tree-of-Thought method to solve the following question step by step.\n\n"
        f"QUESTION:\n{question}\n\n"
        "Choices:\n"
    )
    for opt in choices:
        prompt += f"- {opt}\n"
    prompt += "\nProvide your reasoning, and then at the end type 'Answer: <choice>'."
    return prompt


def evaluate_with_g4f(prompt, model):
    try:
        return g4f.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
    except ResponseStatusError as e:
        print(f"⚠️ HTTP error from provider for model {model}: {e}", file=sys.stderr)
    except RetryProviderError as e:
        print(f"⚠️ All providers failed for model {model}: {e}", file=sys.stderr)
    return ""


def evaluate_question(q, model):
    prompt = tree_of_thought_prompt(q)
    print(f"Evaluating Q{q.get('number')} with {model}...")
    response = evaluate_with_g4f(prompt, model)

    # parse 'Answer:' line
    answer_line = next(
        (line for line in response.splitlines()
         if line.strip().lower().startswith("answer:")),
        ""
    )
    predicted = answer_line.split(" :" if ":" in answer_line else ":", 1)[-1].strip()
    correct_ans = q.get("correct_answer") or q.get("correctAnswer")
    is_correct = str(predicted).lower() == str(correct_ans).lower()
    return predicted, is_correct


def process_file(input_path, output_path):
    # Load questions
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    questions = data.get('questions', [])

    results = {
        "file": os.path.basename(input_path),
        "total_questions": len(questions),
        "questions": [],
        "accuracy": {},
        "overall_accuracy": {}
    }

    for model in models:
        results['accuracy'][model] = {ps: {'correct': 0, 'total': len(questions)} for ps in prompt_style}
        for ps in prompt_style:
            correct_count = 0
            for q in questions:
                predicted, is_corr = evaluate_question(q, model)
                results['questions'].append({
                    'number': q.get('number'),
                    'model': model,
                    'prompt_style': ps,
                    'predicted': predicted,
                    'correct_answer': q.get('correct_answer'),
                    'is_correct': is_corr
                })
                if is_corr:
                    correct_count += 1
            results['accuracy'][model][ps]['correct'] = correct_count
            results['overall_accuracy'].setdefault(model, {})[ps] = {
                'correct': correct_count,
                'total': len(questions),
                'accuracy_percent': round((correct_count / len(questions)) * 100, 2) if questions else 0
            }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"✅ Results saved to {output_path}")


def main():
    # List of JSON files to process and their output filenames
    files = [
        ("Standard_English_Conventions.json", "results/SEC_results.json"),
        ("Information_And_Ideas.json",       "results/IA_results.json"),
        ("Expression_of_ideas.json",        "results/EOI_results.json"),
        ("Craft_and_Structure.json",        "results/CAS_results.json"),
        ("Geometry_and_Trigonometry.json",  "results/GT_results.json"),
        ("Algebra.json",                    "results/ALG_results.json"),
        ("Advanced_maths.json",            "results/AM_results.json"),
        ("problem-solving_and_DA.json",    "results/SAT_PS_results.json")
    ]

    for inp, out in files:
        process_file(inp, out)


if __name__ == "__main__":
    main()
