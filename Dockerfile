FROM python:alpine as base

WORKDIR /app

COPY app/requirements.txt .
RUN pip install -r requirements.txt

ADD app/*.py ./
ENTRYPOINT ["python3"]
CMD ["-u","app.py"]
