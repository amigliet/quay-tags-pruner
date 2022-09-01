FROM registry.access.redhat.com/ubi8:latest

COPY requirements.txt /tmp/requirements.txt
COPY src/pruner.py /usr/bin/

RUN dnf install -y python3.8 && dnf clean all && \
    pip-3.8 install -r /tmp/requirements.txt

USER 1001
ENTRYPOINT ["/usr/bin/python3.8", "-u", "/usr/bin/pruner.py"]
