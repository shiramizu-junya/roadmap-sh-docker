FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install uv==0.13.6
RUN uv sync
CMD [".venv/bin/python", "src/manage.py", "runserver", "0.0.0.0:8000"]
