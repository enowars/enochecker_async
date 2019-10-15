FROM python
LABEL maintainer="ENOFLAG <mail@enoflag.de>"

WORKDIR /checker
COPY ./requirements.txt /checker/requirements.txt
RUN python3 -m pip install -r requirements.txt
COPY . .

ENTRYPOINT ["python", "checker.py" ]
