import httpx

URL = "https://httpbin.org/digest-auth/auth/yeray/{password}/{algorithm}"

ALGORITHMS = [
    "MD5",
    "MD5-SESS",
    "SHA",
    "SHA-SESS",
    "SHA-256",
    "SHA-256-SESS",
    "SHA-512",
    "SHA-512-SESS",
]


def main():
    password = "foo"
    with httpx.Client(auth=httpx.DigestAuth("yeray", password)) as client:
        for algorithm in ALGORITHMS:
            response = client.get(URL.format(password=password, algorithm=algorithm))
            print("FAILED!" if response.status_code != 200 else "", algorithm, response)

        print("\nThis should fail...")
        print(client.get(URL.format(password="bar", algorithm=ALGORITHMS[0])))


if __name__ == "__main__":
    main()
