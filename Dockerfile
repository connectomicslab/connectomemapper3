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

## Install the connectomemapper3

# Define environment variable
# ENV NAME World

# Run app.py when the container launches
CMD ["python", "run.py"]
