FROM python

WORKDIR /home/myapp

COPY ./templates/* /home/myapp/templates/
COPY ./static/* /home/myapp/static/
COPY ./requirements.txt /home/myapp/
COPY ./app.py /home/myapp/

RUN pip install -r requirements.txt

CMD ["python", "/home/myapp/app.py"]

EXPOSE 8080
