FROM python:3.11.12-slim-bookworm@sha256:dbf1de478a55d6763afaa39c2f3d7b54b25230614980276de5cacdde79529d0c
RUN pip install --no-cache-dir coverage==7.8.0 && useradd --uid 10001 --no-create-home runner
COPY harness.py case.py /app/
USER 10001:10001
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1
ENTRYPOINT ["python", "-I", "/app/harness.py"]
