import httpx

PROXY_URL = "http://localhost:8080"
client_cert = "server.pem"
client = httpx.Client(
    proxies={"http": PROXY_URL, "https": PROXY_URL}, verify=client_cert
)
request = client.get("https://duckduckgo.com")
print(request)
