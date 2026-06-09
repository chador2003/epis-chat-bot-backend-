import os
import requests
from pathlib import Path

# FastAPI endpoint
API_URL = "http://172.19.9.235:9000/ingest"

# Root folder containing your PDFs
PDF_ROOT = "."  # Change this

def upload_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            files = {
                "file": (os.path.basename(pdf_path), f, "application/pdf")
            }

            response = requests.post(API_URL, files=files)

        if response.status_code == 200:
            print(f"✓ Uploaded: {pdf_path}")
            print(response.json())
        else:
            print(f"✗ Failed: {pdf_path}")
            print(response.status_code, response.text)

    except Exception as e:
        print(f"Error uploading {pdf_path}: {e}")

def main():
    pdf_files = list(Path(PDF_ROOT).rglob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files")

    for pdf_file in pdf_files:
        upload_pdf(str(pdf_file))

    print("All uploads completed")

if __name__ == "__main__":
    main()