FROM registry.access.redhat.com/ubi8:latest

COPY requirements.txt /tmp/requirements.txt
COPY src/pruner.py /usr/bin/
COPY src/prunerLib /usr/lib/pruner/prunerLib

ENV PYTHONPATH "${PYTHONPATH}:/usr/lib/pruner"

RUN dnf install -y python3.9 && dnf clean all && \
    pip-3.9 install -r /tmp/requirements.txt

USER 1001
ENTRYPOINT ["/usr/bin/python3.9", "-u", "/usr/bin/pruner.py"]
