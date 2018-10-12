FROM python:2.7

# upgrade the setuptools, required for nsenenter
RUN pip install setuptools --upgrade

# copy source code to container
RUN mkdir /opt/axon
COPY . /opt/axon

# install dependencies
WORKDIR /opt/axon
RUN pip install -r requirements.txt
RUN python setup.py install

# expose 5678
EXPOSE 5678

# RUN the service
CMD python -m axon.controller.axon_rpyc_controller 





