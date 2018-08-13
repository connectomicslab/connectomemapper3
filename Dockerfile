# Use an official Python runtime as a parent image
FROM sebastientourbier/neurodocker-image
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
RUN python setup.py install

## Install the connectomemapper3

# Acquire script to be executed
COPY run_connectomemapper3.py /run_connectomemapper3.py
RUN chmod 775 /run_connectomemapper3.py

#COPY version /version

#ENTRYPOINT ["/run_connectomemapper3.py"]

# # Display for X11 pipe
# ENV DISPLAY :0
