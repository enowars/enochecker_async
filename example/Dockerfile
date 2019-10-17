FROM python
LABEL maintainer="ENOFLAG <mail@enoflag.de>"

WORKDIR /checker

# Install local enochecker_async version
COPY requirements.txt requirements.txt
RUN python3 -m pip install -r requirements.txt
COPY README.md README.md
COPY setup.py setup.py
COPY enochecker_async enochecker_async
RUN python3 setup.py install

# Install example
COPY example example
WORKDIR /checker/example
RUN python3 -m pip install -r requirements.txt

ENTRYPOINT ["python", "checker.py" ]
