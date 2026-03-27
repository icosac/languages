FROM --platform=linux/amd64 ubuntu:22.04

WORKDIR /

COPY requirements.txt /

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv git && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /venv
RUN /venv/bin/pip install --upgrade pip
RUN /venv/bin/pip install -r requirements.txt

RUN echo "source /venv/bin/activate" >> ~/.bashrc

ENTRYPOINT [ "python3 /app/src/learn_numbers.py" ]