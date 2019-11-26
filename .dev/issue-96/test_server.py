from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def index(request):
    return {"ok": 1, "data": "welcome to test app 11111111111!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
