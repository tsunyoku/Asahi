FROM python:3.9-slim-buster

WORKDIR /asahi
COPY . /asahi

RUN pip install -r requirements.txt
CMD ["python", "main.py"]
