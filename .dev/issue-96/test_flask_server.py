from flask import Flask

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    return {"ok": 1, "data": "welcome to test app 11111111111!"}


if __name__ == "__main__":
    app.run(port=5000)
