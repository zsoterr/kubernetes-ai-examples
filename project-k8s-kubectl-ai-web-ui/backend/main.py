from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import subprocess
import re  # for stripping ANSI codes and parsing output

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class RunRequest(BaseModel):
    prompt: str
    skip_permissions: bool = False  # controls --skip-permissions


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

        # Append the prompt as positional argument
        cmd.append(prompt)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        stdout_text = result.stdout or ""

        # Try to extract the actual kubectl command from stdout.
        # We handle both:
        #   1) "Running: kubectl run ..."
        #   2) Error case lines like "* kubectl run ..."
        executed_kubectl = None
        try:
            # Remove ANSI color codes before parsing
            ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
            cleaned = ansi_escape.sub("", stdout_text)

            for line in cleaned.splitlines():
                line_stripped = line.strip()

                # Case 1: "Running: kubectl ..."
                if line_stripped.lower().startswith("running:"):
                    executed_kubectl = line_stripped[len("running:") :].strip()
                    break

                # Case 2: "* kubectl ..." (e.g. in "RunOnce" error messages)
                if line_stripped.startswith("* "):
                    candidate = line_stripped.lstrip("*").strip()
                    if candidate.startswith("kubectl "):
                        executed_kubectl = candidate
                        break

        except Exception:
            executed_kubectl = None

        return {
            "command": " ".join(cmd),              # the kubectl-ai command
            "executed_kubectl": executed_kubectl,  # the actual kubectl command (if detected)
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error while executing kubectl-ai: {e}"},
        )
