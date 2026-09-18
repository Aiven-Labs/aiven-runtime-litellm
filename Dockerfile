FROM ghcr.io/berriai/litellm:v1.101.0@sha256:d295634e09c648dcdb72c4cc2dd226f5fb87823a73e88cbbed6f205e4deb044b

COPY bootstrap.py /starter/bootstrap.py
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/liveliness', timeout=4)"
ENTRYPOINT ["python", "/starter/bootstrap.py"]
CMD []
