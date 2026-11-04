FROM python:3.13-slim
WORKDIR /app
RUN pip install uv==0.13.6
COPY pyproject.toml uv.lock ./
RUN uv sync --locked
COPY . .
CMD [".venv/bin/python", "src/manage.py", "runserver", "0.0.0.0:8000"]
