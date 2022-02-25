FROM python:3.10.1

EXPOSE 5000

ENV APP_DIR /usr/src/everystreet
# ENV FLASK_APP $APP_DIR/autoapp.py
# ENV FLASK_DEBUG false

RUN mkdir $APP_DIR
WORKDIR $APP_DIR
COPY . $APP_DIR

RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile && \
    chmod -R ug+rw $APP_DIR

ENTRYPOINT ["gunicorn"]
CMD ["--log-level", "debug", "--bind", "0.0.0.0:5000", "app:app"]
