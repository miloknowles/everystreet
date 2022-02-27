FROM python:3.10.1

EXPOSE 5000
EXPOSE 80

ENV APP_DIR /usr/src/everystreet

RUN mkdir $APP_DIR
WORKDIR $APP_DIR
COPY . $APP_DIR

RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile && \
    chmod -R ug+rw $APP_DIR

ENTRYPOINT ["gunicorn"]
CMD ["--log-level", "debug", "--bind", "0.0.0.0:80", "app:app"]
