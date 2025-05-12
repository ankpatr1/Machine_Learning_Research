#!/usr/bin/env python3

import g4f
import json
import os
import sys
from dotenv import load_dotenv
from g4f.errors import RetryProviderError, ResponseStatusError

# Load .env for API tokens
load_dotenv()

# Configuration
models = [
    "gpt-4", "gpt-4o", "gpt-4o-mini",
    "llama-3.1-8b", "llama-3.1-70b", "llama-3.1-405b",
    "gemini-1.5-flash"
]
prompt_styles = ["tree_of_thought"]

# Input / output files
input_file = "Geometry_and_Trigonometry.json"
output_file = "Geometry_and_Trigonometry_results.json"

# Tree-of-Thought prompt for Geometry & Trigonometry
def tree_of_thought_prompt(q):
    question = q.get('question', '')
    opts = q.get('options', [])
    prompt = (
        "You are an expert SAT Geometry and Trigonometry tutor.\n"
        "Use the Tree-of-Thought method to solve this problem step by step.\n\n"
        f"QUESTION:\n{question}\n\n"
        "Choices:\n"
    )
    if isinstance(opts, dict):
        for key, val in opts.items():
            prompt += f"- {key}: {val}\n"
    elif isinstance(opts, list):
        for opt in opts:
            prompt += f"- {opt}\n"
    prompt += "\nProvide your reasoning, then at the end type 'Answer: <choice>'."
    return prompt

# Send prompt to g4f
def evaluate_with_g4f(prompt, model):
    try:
        return g4f.ChatCompletion.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            stream=False
        )
    except ResponseStatusError as e:
        print(f"⚠️ HTTP error for {model}: {e}", file=sys.stderr)
    except RetryProviderError as e:
        print(f"⚠️ Providers failed for {model}: {e}", file=sys.stderr)
    return ""

# Extract answer and compare
def evaluate_question(q, model):
    prompt = tree_of_thought_prompt(q)
    print(f"Evaluating Q{q.get('number')} with {model}…")
    resp = evaluate_with_g4f(prompt, model)
    answer_line = next(
        (line for line in resp.splitlines() if line.strip().lower().startswith('answer:')),
        ''
    )
    predicted = answer_line.split(':', 1)[-1].strip()
    correct = q.get('correct_answer') or q.get('correctAnswer')
    is_correct = str(predicted).lower() == str(correct).lower()
    return predicted, is_correct

# Main execution
def main():
    # Load JSON
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: '{input_file}' not found.")
        sys.exit(1)

    # Support top-level list or dict with 'questions'
    if isinstance(data, dict):
        questions = data.get('questions', [])
    elif isinstance(data, list):
        questions = data
    else:
        print(f"Error: unexpected JSON format in {input_file}.")
        sys.exit(1)

    print(f"Loaded {len(questions)} questions from {input_file}\n")

    results = {
        'file': input_file,
        'total_questions': len(questions),
        'questions': [],
        'accuracy': {},
        'overall_accuracy': {}
    }

    # Evaluate models
    for model in models:
        results['accuracy'][model] = {}
        results['overall_accuracy'][model] = {}
        for style in prompt_styles:
            correct_count = 0
            for q in questions:
                pred, ok = evaluate_question(q, model)
                results['questions'].append({
                    'number': q.get('number'),
                    'model': model,
                    'predicted': pred,
                    'correct_answer': q.get('correct_answer') or q.get('correctAnswer'),
                    'is_correct': ok
                })
                if ok:
                    correct_count += 1
            total = len(questions)
            results['accuracy'][model][style] = {'correct': correct_count, 'total': total}
            results['overall_accuracy'][model][style] = {
                'correct': correct_count,
                'total': total,
                'accuracy_percent': round((correct_count / total) * 100, 2) if total else 0
            }

    # Write results
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results saved to {output_file}")

if __name__ == '__main__':
    main()
