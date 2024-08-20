FROM python:3.12-slim-bullseye

WORKDIR /

ENV PYTHONUNBUFFERED=1

ADD pyproject.toml .
ADD oc_ref_bot /oc_ref_bot

RUN pip install --upgrade pip wheel && pip install -e '.'

CMD ["start-bot"]
