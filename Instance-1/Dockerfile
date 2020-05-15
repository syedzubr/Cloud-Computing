FROM python:3.6.8-alpine3.9

WORKDIR /home/ubuntu/flaskapp/appp/

ADD . /home/ubuntu/flaskapp/appp/
RUN pip install -r requirements.txt
RUN pip install gunicorn==19.9.0

EXPOSE 8000

CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:80", "wsgi:app"]
 