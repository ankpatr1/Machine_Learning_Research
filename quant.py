import PyPDF2
import json

# Use the absolute path to the PDF:
pdf_filepath = 'MR-GMAT.pdf'

output_data = {"questions": []}

with open(pdf_filepath, 'rb') as pdf_file:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    for page_num, page in enumerate(pdf_reader.pages):
        text = page.extract_text()
        question_obj = {
            "id": f"question{page_num + 1}",
            "q": text
        }
        output_data["questions"].append(question_obj)

with open('gmat1.json', 'w') as json_file:
    json.dump(output_data, json_file, indent=4)

print(json.dumps(output_data, indent=4))
