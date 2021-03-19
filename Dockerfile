FROM python:3.8

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --trusted-host pypi.org --no-cache-dir -r requirements.txt

COPY src/* .

CMD ["python", "tipbot_launcher.py"]