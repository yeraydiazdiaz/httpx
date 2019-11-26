from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse
import httpx

app = FastAPI()
http_client = httpx.AsyncClient()


@app.middleware("http")
async def sso_middleware(request: Request, call_next):
    r = await http_client.post("http://127.0.0.1:5000")
    if r.status_code != 200:
        return JSONResponse({"ok": 0, "data": {"status_code": r.status_code}})
    ret = r.json()
    await r.close()
    print(ret)
    response = await call_next(request)
    return response


@app.get("/")
def index(request: Request):
    return {"ok": 1, "data": "welcome to test app!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
    pass
