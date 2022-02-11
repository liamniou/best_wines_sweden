FROM python:3

WORKDIR /app

RUN apt-get update -y && apt-get install -y chromium \
    build-essential libssl-dev libffi-dev python3-dev cargo rustc \
    # ^ these 6 are required for cryptography
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get -y update && apt-get install -y google-chrome-stable unzip \
    && wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get remove -y curl unzip \
    && apt-get clean

COPY ./app/requirements.txt ./

RUN pip install -r requirements.txt

COPY ./app ./

CMD ["python3", "best_wines_sweden.py"]
