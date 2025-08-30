import os
from flask import Flask, render_template

app = Flask(__name__)

@app.get("/")
def index():
    maptile_key = os.getenv("MAPTILER_KEY", "")  
    return render_template("index.html", MAPTILER_KEY=maptile_key)

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
