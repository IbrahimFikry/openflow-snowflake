FROM python:3.10-slim

WORKDIR /app
COPY ./app /app/app
RUN pip install fastapi pymongo uvicorn faker

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]