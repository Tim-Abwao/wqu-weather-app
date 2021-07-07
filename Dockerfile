FROM python:3.9.6-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt \
    # wait 2 minutes before timing out in slow/unstable networks
    --timeout=120
COPY weather_app ./weather_app
EXPOSE 5000
CMD waitress-serve --listen 0.0.0.0:5000 weather_app:app
