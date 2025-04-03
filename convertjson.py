import PyPDF2
import re
import json

pdf_filepath = 'Gmat1.pdf'
output_data = {"questions": []}

# Define a simple set of math symbols to detect questions with complex symbols.
math_symbols = ['√', 'π', '∑', '∞', '≈', '≠', '≥', '≤', '∫']

# 1. Read all pages of the PDF into a single string.
with open(pdf_filepath, 'rb') as pdf_file:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    all_text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            all_text += page_text + "\n"

# 2. Define a regex pattern that captures each question block.
#    This assumes questions are numbered with "1. ", "2. ", etc.
question_pattern = r"(\d+\.\s.*?)(?=\d+\.\s|$)"
questions = re.findall(question_pattern, all_text, flags=re.DOTALL)

# 3. Process each question block to extract details.
for i, q_block in enumerate(questions):
    q_block = q_block.strip()
    
    # --- Determine the question type (simple heuristic) ---
    # If "PS" is found, assume it is a Quantitative Problem Solving question.
    if "PS" in q_block:
        question_type = "Quantitative Problem Solving"
    elif "DS" in q_block:
        question_type = "Data Sufficiency"
    else:
        question_type = "Unknown"
    
    # --- Extract the question text ---
    # Assume options start with "A" so extract text up to that point.
    option_a_match = re.search(r"A[.:]\s*", q_block)
    if option_a_match:
        question_text = q_block[:option_a_match.start()].strip()
    else:
        question_text = q_block  # fallback if options not found

    # --- Check if the question has math symbols. ---
    # If found, assume you want to use a screenshot instead.
    if any(symbol in question_text for symbol in math_symbols):
        # You can change this path to your actual screenshot file
        question_content = f"screenshots/question{i+1}.png"
    else:
        question_content = question_text

    # --- Extract Options ---
    options = {}
    # Patterns for options A, B, C, and D.
    pattern_a = r"A[.:]\s*(.*?)\s*(?=B[.:])"
    pattern_b = r"B[.:]\s*(.*?)\s*(?=C[.:])"
    pattern_c = r"C[.:]\s*(.*?)\s*(?=D[.:])"
    # For D, we stop at "Answer:" if available, otherwise end of block.
    pattern_d = r"D[.:]\s*(.*?)(?=(Answer[:.]|$))"
    
    a_match = re.search(pattern_a, q_block, flags=re.DOTALL)
    b_match = re.search(pattern_b, q_block, flags=re.DOTALL)
    c_match = re.search(pattern_c, q_block, flags=re.DOTALL)
    d_match = re.search(pattern_d, q_block, flags=re.DOTALL)
    
    options["A"] = a_match.group(1).strip() if a_match else ""
    options["B"] = b_match.group(1).strip() if b_match else ""
    options["C"] = c_match.group(1).strip() if c_match else ""
    options["D"] = d_match.group(1).strip() if d_match else ""
    
    # --- Extract Answer ---
    answer_match = re.search(r"Answer[.:]\s*(.*?)(?=(Explanation[:.]|$))", q_block, flags=re.DOTALL)
    answer = answer_match.group(1).strip() if answer_match else ""
    
    # --- Extract Explanation ---
    explanation_match = re.search(r"Explanation[.:]\s*(.*)", q_block, flags=re.DOTALL)
    explanation = explanation_match.group(1).strip() if explanation_match else ""
    
    # --- Build question JSON entry ---
    question_entry = {
        "id": f"question{i+1}",
        "type": question_type,
        "question": question_content,
        "options": options,
        "Answer": answer,
        "Explanation": explanation
    }
    
    output_data["questions"].append(question_entry)

# 4. Write the JSON to file.
with open('gmat1.json', 'w') as json_file:
    json.dump(output_data, json_file, indent=4)

# 5. (Optional) Print to console
print(json.dumps(output_data, indent=4))
