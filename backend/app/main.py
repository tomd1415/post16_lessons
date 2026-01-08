from fastapi import FastAPI

app = FastAPI(
    title="Thinking like a Coder API",
    version="0.0.0",
)


@app.get("/")
def root():
    return {
        "status": "stub",
        "message": "API not implemented yet",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
