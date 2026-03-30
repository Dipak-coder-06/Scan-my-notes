"""
modules/mcq_generator.py
------------------------
Generates 10-15 Multiple Choice Questions from the entire document content.
Uses Ollama with llama3.2 in JSON mode to guarantee structured output.
"""
import os
import json
from typing import List, Dict, Any
import ollama

def generate_mcqs(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes all document chunks, extracts the raw text, and asks llama3.2 
    to generate 10-15 MCQs covering all key topics.
    Returns a list of dictionaries.
    """
    # Combine chunk texts to give full context. 
    # For very large documents, we might need to summarize first, but for now we pass it in.
    # To avoid exceeding context limits, we'll take top N chunks or sample them evenly.
    sampled_chunks = chunks
    if len(chunks) > 20:
        step = len(chunks) // 20
        sampled_chunks = chunks[::step][:20]
        
    full_text = "\n\n".join([c["text"] for c in sampled_chunks])
    
    system_prompt = """
    You are an expert educator creating a comprehensive quiz.
    Based on the provided document text, generate 10 to 15 Multiple Choice Questions (MCQs).
    The questions must cover the entire span of the document and test key concepts, not trivial details.
    
    You MUST output valid JSON only, using this exact schema:
    {
      "mcqs": [
        {
          "question": "The question text",
          "options": ["A) First", "B) Second", "C) Third", "D) Fourth"],
          "correct_answer": "A) First",
          "explanation": "Short explanation of why A is correct."
        }
      ]
    }
    """
    
    llm_model = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
    client = ollama.Client(host=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    
    try:
        response = client.chat(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Document Text:\n{full_text}"}
            ],
            options={
                "temperature": 0.3, # Slightly creative but focused
            },
            format="json", # Force JSON output
            keep_alive=0
        )
        
        content = response["message"]["content"]
        data = json.loads(content)
        return data.get("mcqs", [])
    except Exception as e:
        print(f"Error generating MCQs: {e}")
        return []
