FROM python

WORKDIR /home/myapp

COPY ./requirements.txt /home/myapp/
RUN pip install -r requirements.txt

COPY . .


CMD ["python", "/home/myapp/worker.py"]
