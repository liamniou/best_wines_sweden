FROM mcr.microsoft.com/playwright/python:v1.29.0-focal

WORKDIR /app

COPY ./app/requirements.txt ./

RUN pip install -r requirements.txt

COPY ./app ./

CMD ["python3", "best_wines.py"]
