FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install unsloth separately if needed or just rely on requirements.txt
# RUN pip3 install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["python3", "app.py"]
