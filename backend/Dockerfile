# app/Dockerfile

FROM python:3.12

COPY requirements.txt /app/requirements.txt
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*


RUN pip3 install -r requirements.txt

COPY /model_settings /app/model_settings
COPY /utils /app/utils
COPY /main.py /app/main.py
ENV POSTGRES_DB=budget_optimizer
ENV POSTGRES_HOST=postgress_server
ENV POSTGRES_PORT=5432

EXPOSE 8000

#HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["fastapi", "run", "main.py"]