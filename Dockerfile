FROM ubuntu:22.04
SHELL ["/bin/bash", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        bzip2 \
        default-jre \
        wget \
        unzip \
        libgl1-mesa-glx \
        libvips42 \
        procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN set -o pipefail && wget -qO- https://get.nextflow.io | bash && \
    mv nextflow -t /root && \
    /root/nextflow self-update

RUN set -o pipefail && wget "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" && \
    unzip awscli-exe-linux-x86_64.zip && \
    ./aws/install && \
    rm awscli-exe-linux-x86_64.zip && \
    rm -rf /aws

ARG VZGPT_VERSION
RUN pip install wheel
RUN --mount=type=secret,id=pipconfig,dst=/etc/pip.conf \
    pip install --no-cache-dir vpt==${VZGPT_VERSION}

ADD nextflow_pipeline /nextflow_pipeline/

CMD /bin/bash
