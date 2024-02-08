FROM ubuntu:22.04
SHELL ["/bin/bash", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system libraries
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    bzip2 \
    default-jre \
    curl \
    unzip \
    libgl1-mesa-glx \
    libvips42 \
    procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Nextflow
RUN curl -fsSL get.nextflow.io | bash && \
    mv nextflow -t /root && \
    /root/nextflow self-update

# Install aws cli
RUN curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip --output awscli-exe-linux-x86_64.zip && \
    unzip awscli-exe-linux-x86_64.zip && \
    ./aws/install && \
    rm awscli-exe-linux-x86_64.zip && \
    rm -rf /aws

# Install vpt
ADD . /vizgen_postprocessing/
RUN pip install --upgrade pip && \
    pip install /vizgen_postprocessing/[all] && \
    rm -rf /root/.cache

CMD /bin/bash
