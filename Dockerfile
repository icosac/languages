FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "npm run build-css && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
