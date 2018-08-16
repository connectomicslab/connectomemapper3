# Use an official Python runtime as a parent image
FROM sebastientourbier/neurodocker-image:cmp-ready
MAINTAINER Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>

##
# Install any needed packages specified in requirements.txt
# RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
# EXPOSE 80

# Set the working directory to /app and copy contents of this repository
WORKDIR /app
ADD . /app

#Clone the master branch of connectomemapper 3 from BitBucket
ARG password
RUN git clone --progress --verbose https://sebastientourbier:$password@bitbucket.org/sebastientourbier/connectomemapper3.git connectomemapper3
RUN git checkout master

# Set the working directory to /app/connectomemapper3 and install connectomemapper3
WORKDIR /app/connectomemapper3
RUN python setup.py install

# Create entrypoint script that simulated a X server - required by traitsui
RUN echo '#! /bin/sh \n xvfb-run python "/app/run_connectomemapper3.py" "$@"' > /app/run_connectomemapper3.sh

# Set the working directory back to /app
# Acquire script to be executed
RUN chmod 775 /app/run_connectomemapper3.py
RUN chmod 775 /app/run_connectomemapper3.sh

#COPY version /version
ENTRYPOINT ["/app/run_connectomemapper3.sh"]
