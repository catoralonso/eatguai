FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data
ENV PORT=8080
EXPOSE 8080
CMD ["python", "app_gradiov4.py"]
