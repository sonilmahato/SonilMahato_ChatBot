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
  <link href="https://fonts.googleapis.com/css2?family=Segoe+UI&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      margin: 0;
      background: linear-gradient(135deg, #e0f7fa, #f4f4f9);
      display: flex;
      align-items: center;
      justify-content: center;
      height: 200vh;
    }
    #chatbox {
      background: white;
      width: 90%;
      max-width: 800px;
      padding: 25px 30px;
      border-radius: 40px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
    }
    h2 {
      text-align: center;
      color: #004d99;
      margin-bottom: 20px;
    }
    .bubble {
      padding: 12px 16px;
      margin: 10px 0;
      border-radius: 20px;
      max-width: 80%;
      line-height: 1.4;
      animation: fadeIn 0.3s ease-in-out;
    }
    .user {
      background-color: #d1e7dd;
      align-self: flex-end;
      text-align: right;
      margin-left: auto;
    }
    .bot {
      background-color: #fce4ec;
      align-self: flex-start;
      text-align: left;
      margin-right: auto;
    }
    #messages {
      display: flex;
      flex-direction: column;
      min-height: 300px;
    }
    input, button {
      font-size: 16px;
      padding: 12px;
      margin-top: 10px;
      border-radius: 12px;
      border: 1px solid #ccc;
    }
    input {
      width: 70%;
      margin-right: 5%;
    }
    button {
      width: 23%;
      background-color: #004d99;
      color: white;
      border: none;
      cursor: pointer;
    }
    button:hover {
      background-color: #003366;
    }
    .button-row {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-top: 20px;
    }
    .contact-btn {
      background: #6c757d;
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: 12px;
      cursor: pointer;
      font-size: 14px;
    }
    .contact-btn:hover {
      background-color: #5a6268;
    }
    .contact-box {
      margin-top: 20px;
      background-color: #f1f1f1;
      padding: 15px;
      border-radius: 10px;
      display: none;
      font-size: 14px;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>
  <div id="chatbox">
    <h2>🎓 University Enquiry Chatbot</h2>
    <div id="messages"></div>
    <div style="display: flex;">
      <input type="text" id="user_input" placeholder="Ask a question..." />
      <button onclick="sendMessage()">Send</button>
    </div>

    <div class="button-row">
      <button class="contact-btn" onclick="toggleContact()">📧 Contact Designer</button>
    </div>

    <div id="contact-info" class="contact-box">
      <strong>Designer:</strong> Sonil Mahato<br>
      <strong>Email:</strong> <a href="mailto:sonilmahato12@gmail.com">sonilmahato12@gmail.com</a><br>
      <strong>University:</strong> University of East London<br>
      <strong>Role:</strong> ML/AI Developer
    </div>
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

    function toggleContact() {
      const box = document.getElementById("contact-info");
      box.style.display = box.style.display === "none" || box.style.display === "" ? "block" : "none";
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
