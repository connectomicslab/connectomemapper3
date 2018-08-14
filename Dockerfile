# Use an official Python runtime as a parent image
FROM sebastientourbier/neurodocker-image:cmp-ready
MAINTAINER Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>

##
# Install any needed packages specified in requirements.txt
# RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
# EXPOSE 80

# Set the working directory to /connectomemapper3
WORKDIR /connectomemapper3

# Copy the current directory contents into the container at /app
ADD . /connectomemapper3
WORKDIR /connectomemapper3

## Xvfb installed as a Service to smulate a Xserver in the container
#RUN apt-get update && apt-get install -y xvfb x11vnc x11-xkb-utils xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic x11-apps
#ADD docker/files/xvfb_init /etc/init.d/xvfb
#RUN chmod a+x /etc/init.d/xvfb
#ADD docker/files/xvfb_daemon_run /usr/bin/xvfb-daemon-run
#RUN chmod a+x /usr/bin/xvfb-daemon-run

#ENV DISPLAY :99

#RUN Xvfb :1 -screen 0 1024x768x16 &> /xvfb.log
#ENV DISPLAY :1

## Install the connectomemapper3
RUN python setup.py install

RUN echo '#! /bin/sh \n xvfb-run python "/run_connectomemapper3.py" "$@"' > /run_connectomemapper3.sh

# Acquire script to be executed
COPY run_connectomemapper3.py /run_connectomemapper3.py
RUN chmod 775 /run_connectomemapper3.py
RUN chmod 775 /run_connectomemapper3.sh

#COPY version /version

ENTRYPOINT ["/run_connectomemapper3.sh"]

# # Display for X11 pipe
#ENV DISPLAY :0
