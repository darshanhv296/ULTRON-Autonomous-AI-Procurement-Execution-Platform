# Local setup

Use Python 3.10 or newer. On Windows, run `run.bat`. On macOS/Linux, create a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, and start with `uvicorn backend.main:app --host 127.0.0.1 --port 8000`.

The app serves `index.html` at `/` and the API documentation at `/docs`. Configure optional integrations in `.env`. Do not commit `.env` or runtime files.
