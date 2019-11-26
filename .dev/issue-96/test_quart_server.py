from quart import Quart

app = Quart(__name__)


@app.route("/", methods=["GET", "POST"])
async def hello():
    return "Hello, World!"


if __name__ == "__main__":
    app.run(port=5001)
