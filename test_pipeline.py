import os
import sys

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

# Test Ingestion
print("=== Testing Ingestion ===")
from pipeline.ingest import ingest_pdf
words = ingest_pdf("notes.pdf", progress_callback=lambda c, t: None)
print(f"Ingested {len(words)} words.")

from pipeline.chunker import chunk_words
chunks = chunk_words(words)
print(f"Created {len(chunks)} chunks.")

from pipeline.embedder import store_chunks, clear_collection
clear_collection()
stored = store_chunks(chunks)
print(f"Stored {stored} chunks in Chroma.")

# Test Retrieval and Generation
print("\n=== Testing Retrieval & Generation ===")
from pipeline.retriever import hybrid_search
from pipeline.generator import generate_answer

query = "What are the main topics in these notes?"
retrieved = hybrid_search(query, top_k=2)
print(f"Retrieved {len(retrieved)} chunks.")
res = generate_answer(query, retrieved)
print(f"Answer: {res['answer']}")
print(f"Confidence: {res['confidence']}%")

# Test MCQ Generation
print("\n=== Testing MCQ Generation ===")
from modules.mcq_generator import generate_mcqs
mcqs = generate_mcqs(chunks)
print(f"Generated {len(mcqs)} MCQs.")
if mcqs:
    for i, q in enumerate(mcqs[:2]):
        print(f"Q{i+1}: {q.get('question')}")
        print(f"Ans: {q.get('correct_answer')}")

# Test PDF Export
print("\n=== Testing PDF Exporter ===")
from modules.pdf_exporter import export_qa_to_pdf, export_mcqs_to_pdf
qa_bytes = export_qa_to_pdf("notes.pdf", [{"role": "user", "content": query}, {"role": "assistant", "content": res['answer']}])
print(f"QA PDF size: {len(qa_bytes)} bytes")
mcq_bytes = export_mcqs_to_pdf("notes.pdf", mcqs)
print(f"MCQ PDF size: {len(mcq_bytes)} bytes")

print("\nAll pipeline components executed successfully!")
