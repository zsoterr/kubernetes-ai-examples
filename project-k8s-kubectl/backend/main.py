from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import subprocess

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class RunRequest(BaseModel):
    prompt: str
    skip_permissions: bool = False  # NEW: controls --skip-permissions


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/run")
async def run_command(run_req: RunRequest):
    prompt = run_req.prompt.strip()

    if not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "Prompt is empty. Please enter a request for kubectl-ai."},
        )

    try:
        # Base command – adjust if you ever switch to kubectl plugin form:
        # cmd = ["kubectl", "ai", ...]
        cmd = [
            "kubectl-ai",
            "--llm-provider=openai",
            "--model=gpt-4.1",
            "--quiet",  # enforce non-interactive mode
        ]

        # If the user explicitly allows it, skip permission checks in kubectl-ai
        if run_req.skip_permissions:
            cmd.append("--skip-permissions")

        # Finally append the prompt as positional argument
        cmd.append(prompt)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        return {
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error while executing kubectl-ai: {e}"},
        )

