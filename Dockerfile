FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir .
EXPOSE 8000
ENV COLLOCAGENT_HOST=0.0.0.0
CMD ["python", "-m", "collocagent.server"]
