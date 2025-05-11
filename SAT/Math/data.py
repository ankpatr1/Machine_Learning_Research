#!/usr/bin/env python3
import g4f
import json
import os
import sys
import argparse
from dotenv import load_dotenv
from g4f.errors import RetryProviderError, ResponseStatusError

load_dotenv()

# Default models and styles
DEFAULT_MODELS = [
    "gpt-4", "gpt-4o", "gpt-4o-mini",
    "llama-3.1-8b", "llama-3.1-70b", "llama-3.1-405b",
    "gemini-1.5-flash"
]
DEFAULT_STYLES = ["tree_of_thought"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate SAT problems with multiple LLMs using Tree-of-Thought"
    )
    parser.add_argument(
        "--infile", "-i",
        default="problem-solving_and_da.json",
        help="Input JSON file with SAT questions (default: %(default)s)"
    )
    parser.add_argument(
        "--outfile", "-o",
        default="SAT_PS_results.json",
        help="Output JSON file for consolidated results (default: %(default)s)"
    )
    parser.add_argument(
        "--models", "-m",
        nargs='+',
        default=DEFAULT_MODELS,
        help="List of model names to evaluate"
    )
    parser.add_argument(
        "--styles", "-s",
        nargs='+',
        default=DEFAULT_STYLES,
        help="List of prompt styles to use"
    )
    return parser.parse_args()


def tree_of_thought_prompt_sat(q):
    question = q.get("question", "")
    choices = q.get("options", [])
    prompt = (
        "You are an expert SAT problem-solving tutor.\n"
        "Use the Tree-of-Thought method to solve the following problem step by step.\n\n"
        f"QUESTION:\n{question}\n\nChoices:\n"
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


def evaluate_question(q, model, style):
    prompt = tree_of_thought_prompt_sat(q) if style == "tree_of_thought" else q.get("question", "")
    print(f"Evaluating Q{q.get('number')} with {model} - {style}...")
    response = evaluate_with_g4f(prompt, model=model)

    answer_line = next(
        (line for line in response.splitlines() if line.strip().lower().startswith("answer:")),
        ""
    )
    predicted = answer_line.split(":", 1)[-1].strip()
    is_correct = predicted.lower() == str(q.get("correct_answer", "")).lower()
    return predicted, is_correct


def main():
    args = parse_args()
    # Load questions
    try:
        with open(args.infile, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f"ERROR loading input file: {e}")
    questions = data.get("questions", [])

    # Initialize results
    results = {
        "total_questions": len(questions),
        "questions": [],
        "accuracy": {},
        "overall_accuracy": {},
        "answers": {}  # summary of predictions per model
    }

    # Prepare answer summary dict
    for model in args.models:
        results["answers"][model] = {}

    for style in args.styles:
        results["accuracy"][style] = {}
        for model in args.models:
            correct_count = 0
            for q in questions:
                predicted, is_correct = evaluate_question(q, model, style)
                q_num = q.get("number")
                # record individual question result
                results["questions"].append({
                    "number": q_num,
                    "model": model,
                    "style": style,
                    "predicted": predicted,
                    "correct_answer": q.get("correct_answer"),
                    "is_correct": is_correct
                })
                # record prediction in summary
                results["answers"][model][str(q_num)] = predicted
                correct_count += int(is_correct)

            total = len(questions)
            results["accuracy"][style][model] = {
                "correct": correct_count,
                "total": total
            }
            results["overall_accuracy"][f"{model}-{style}"] = {
                "correct": correct_count,
                "total": total,
                "accuracy": round((correct_count / total) * 100, 2) if total else 0
            }

    # Save results
    try:
        with open(args.outfile, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {args.outfile}")
    except Exception as e:
        sys.exit(f"ERROR writing output file: {e}")


if __name__ == "__main__":
    main()
