from flask import Flask, request, render_template_string, jsonify
import pandas as pd
import re
import os

# === Load CSV ===
df = pd.read_csv("qa_dataset.csv")
df['question'] = df['question'].astype(str).str.strip()
df['answer'] = df['answer'].astype(str).str.strip()
questions = df['question'].tolist()
answers = df['answer'].tolist()

# === Initialize App ===
app = Flask(__name__)

# === Text Normalizer ===
def normalize(text):
    return re.sub(r'[^\w\s]', '', text.strip().lower())

# === Exact Match Function ===
def is_exact_match(query):
    nq = normalize(query)
    for i, q in enumerate(questions):
        if normalize(q) == nq:
            return True, answers[i]
    return False, None

# === Related Questions (Substring Matching) ===
def get_related_questions(query, limit=3):
    keywords = normalize(query).split()
    related = []
    seen = set()
    for q in questions:
        q_norm = normalize(q)
        if any(k in q_norm for k in keywords) and q not in seen:
            related.append(q)
            seen.add(q)
    return related[:limit]

# === HTML Frontend ===
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

# === Route for frontend ===
@app.route("/")
def index():
    return render_template_string(html_template)

# === API route for chat ===
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("message", "")
    match, answer = is_exact_match(query)
    if match:
        response = answer + " Would you like to ask another question?"
    else:
        related = get_related_questions(query)
        if related:
            response = "I couldn’t find an exact answer. Here are related questions you can try:\n" + "\n".join(f"- {q}" for q in related)
        else:
            response = "I couldn’t find an exact answer or related questions."
    return jsonify({"response": response})

# === Run App on Render-Compatible Port ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
