FROM python

RUN pip install --upgrade pip
RUN pip install flask \
    waitress

RUN mkdir -p /app
WORKDIR /app
COPY . .

EXPOSE 80

CMD ["python", "app.py"]