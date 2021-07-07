SHELL := /bin/bash

.PHONY: all deploy

all: requirements.txt
	test -d venv || python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt
	touch venv

develop:
	source venv/bin/activate && \
	export FLASK_APP=weather_app && \
	export FLASK_ENV=development && \
	flask run

deploy:
	source venv/bin/activate && \
	waitress-serve --listen 0.0.0.0:5000 weather_app:app

test:
	source venv/bin/activate && \
	pytest tests
