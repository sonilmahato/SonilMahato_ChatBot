from flask import Flask, request, jsonify, render_template_string
from sentence_transformers import SentenceTransformer
from transformers import T5ForConditionalGeneration, T5Tokenizer
import faiss
import pandas as pd
import torch
import numpy as np

app = Flask(__name__)

# Load embedding and generation models
embedder = SentenceTransformer('all-MiniLM-L6-v2')
t5_model = T5ForConditionalGeneration.from_pretrained('google/flan-t5-small')
t5_tokenizer = T5Tokenizer.from_pretrained('google/flan-t5-small')

# Load QA data
df = pd.read_csv("data/qa_dataset.csv")  # Include this file in your project
questions = df['question'].tolist()
answers = df['answer'].tolist()

# Create embeddings and FAISS index
corpus_embeddings = embedder.encode(questions, convert_to_tensor=True).cpu().detach().numpy()
index = faiss.IndexFlatL2(corpus_embeddings.shape[1])
index.add(corpus_embeddings)

# Search function
def search_answer(user_input, top_k=1, threshold=0.7):
    query_embedding = embedder.encode([user_input], convert_to_tensor=True).cpu().detach().numpy()
    D, I = index.search(query_embedding, top_k)
    if D[0][0] < threshold:
        return answers[I[0][0]]
    return None

# Generate follow-up questions
def generate_questions(prompt, num_return_sequences=3):
    input_text = f"Generate questions: {prompt}"
    input_ids = t5_tokenizer.encode(input_text, return_tensors="pt")
    outputs = t5_model.generate(
        input_ids=input_ids,
        max_length=64,
        num_return_sequences=num_return_sequences,
        do_sample=True,
        top_k=50,
        top_p=0.95
    )
    questions = [t5_tokenizer.decode(output, skip_special_tokens=True) for output in outputs]
    return list(set(questions))

# HTML frontend as a string
html_template = """
<!DOCTYPE html>
<html>
<head>
  <title>University Chatbot</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 30px; background: #f4f4f9; }
    #chatbox { width: 100%; max-width: 700px; margin: auto; }
    .bubble { padding: 10px 15px; margin: 10px; border-radius: 10px; }
    .user { background-color: #d1e7dd; text-align: right; }
    .bot { background-color: #f8d7da; text-align: left; }
    input, button { padding: 10px; font-size: 16px; width: 80%; }
    button { width: 15%; }
  </style>
</head>
<body>
  <div id="chatbox">
    <h2>🎓 University Enquiry Chatbot</h2>
    <div id="messages"></div>
    <input type="text" id="user_input" placeholder="Ask a question..." />
    <button onclick="sendMessage()">Send</button>
  </div>

  <script>
    async function sendMessage() {
      const input = document.getElementById("user_input");
      const message = input.value.trim();
      if (!message) return;
      document.getElementById("messages").innerHTML += `<div class='bubble user'><b>You:</b> ${message}</div>`;
      input.value = '';

      const res = await fetch("/chat", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
      });

      const data = await res.json();
      document.getElementById("messages").innerHTML += `<div class='bubble bot'><b>Bot:</b> ${data.response.replace(/\\n/g, "<br>")}</div>`;
    }
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_template)

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json['message']
    response = search_answer(user_input)
    if response:
        return jsonify({'response': response})
    else:
        followups = generate_questions(user_input)
        return jsonify({'response': "I'm not sure, but you could try one of these:\n" + "\n".join(f"- {q}" for q in followups)})

if __name__ == '__main__':
    app.run(debug=True)
