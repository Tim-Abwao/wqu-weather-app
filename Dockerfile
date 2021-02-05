FROM python:3.8-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt \
    # wait 2 minutes before timing out in slow/unstable networks
    --default-timeout=120
COPY weather_app ./weather_app
EXPOSE 5000
CMD gunicorn -w 4 -b 0.0.0.0:5000 weather_app:app
