# Build environment variables arguments
ARG MAIN_DOCKER
ARG MAIN_VERSION
ARG VERSION
ARG BUILD_DATE
ARG VCS_REF

# Use an initial image, where all Connectome Mapper 3 dependencies are installed, as a parent image
FROM "${MAIN_DOCKER}":"${MAIN_VERSION}"

#RUN groupadd -r -g 1000 cmp && \
#    useradd -r -M -u 1000 -g cmp cmp

##
# Install any needed packages specified in requirements.txt
# RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
# EXPOSE 80

# WORKDIR /bids_dataset
# WORKDIR /bids_dataset/derivatives
# WORKDIR /bids_dataset/derivatives/freesurfer
# WORKDIR /bids_dataset/derivatives/freesurfer/fsaverage
# WORKDIR /opt/freesurfer/subjects/fsaverage
# ADD . /bids_dataset/derivatives/freesurfer/fsaverage

# Set the working directory to /app and copy contents of this repository
WORKDIR /app/connectomemapper3
COPY . /app/connectomemapper3

ENV CONDA_ENV py37cmp-core

#RUN apt-get -qq -y install libtiff5-dev=4.0.6-1ubuntu0.4 libssl-dev=1.0.2g-1ubuntu4.13
RUN /bin/bash -c ". activate $CONDA_ENV && pip install networkx==2.4 &&\
    python setup.py install"

# ENV ANTSPATH=/opt/conda/bin
# ENV PATH=$ANTSPATH:$PATH
ENV ANTSPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PYTHONPATH /opt/conda/envs/$CONDA_ENV/bin
ENV PATH $ANTSPATH:$PATH
ENV LD_LIBRARY_PATH /opt/conda/envs/$CONDA_ENV/lib:$LD_LIBRARY_PATH

# Make dipy.viz (fury/vtk) happy
RUN /bin/bash -c "ln -s /opt/conda/envs/$CONDA_ENV/lib/libnetcdf.so.15 /opt/conda/envs/$CONDA_ENV/lib/libnetcdf.so.13"

# Create entrypoint script that simulated a X server - required by traitsui?
# try to change freesurfer home permission to copy the license
#RUN echo '#! /bin/bash \n chown "$(id -u):$(id -g)" /opt/freesurfer \n . activate $CONDA_ENV \n xvfb-run -a python /app/connectomemapper3/run.py $@ \n rm -f -R /tmp/.X99-lock /tmp/.X11-unix /tmp/.xvfb-run.*' > /app/run_connectomemapper3.sh

#Previous for Docker
#RUN echo '#! /bin/bash \n . activate $CONDA_ENV \n xvfb-run -a python /app/connectomemapper3/run.py $@ \n rm -f -R /tmp/.X99-lock /tmp/.X11-unix /tmp/.xvfb-run.*' > /app/run_connectomemapper3.sh

#Current for singularity

# Create content of entrypoint script
ENV content="#! /bin/bash\n"
ENV content="${content}echo User: \$(id -un \$USER) && echo Group: \$(id -gn \$USER) &&"
ENV content="$content . \"$FSLDIR/etc/fslconf/fsl.sh\" &&"
ENV content="$content . activate \"${CONDA_ENV}\" &&"
ENV content="$content xvfb-run -s \"-screen 0 900x900x24 -ac +extension GLX -noreset\" \
-a python /app/connectomemapper3/run.py \$@"

# Write content to BIDSapp entrypoint script
RUN printf "$content" > /app/run_cmp3.sh
RUN cat /app/run_cmp3.sh

# Create content of entrypoint script with coverage
ENV content_cov="#! /bin/bash\n"
ENV content_cov="${content_cov}echo User: \$(id -un \$USER) && echo Group: \$(id -gn \$USER) &&"
ENV content_cov="${content_cov} . \"$FSLDIR/etc/fslconf/fsl.sh\" &&"
ENV content_cov="${content_cov} . activate \"${CONDA_ENV}\" &&"
ENV content_cov="${content_cov} xvfb-run -s \"-screen 0 900x900x24 -ac +extension GLX -noreset\" \
-a coverage run --source=cmp,cmtklib --omit=*/bidsappmanager/*,*/viz/* /app/connectomemapper3/run.py \$@ &&"
# ENV content_cov="${content_cov} xvfb-run -s \"-screen 0 900x900x24 -ac +extension GLX -noreset\" \
# -a coverage run --source=/opt/conda/envs/${CONDA_ENV}/lib/python3.7/site-packages/cmp,/opt/conda/envs/py27cmp-core/lib/python3.7/site-packages/cmtklib --omit=*/bidsappmanager/*,*/viz/* /app/connectomemapper3/run.py \$@ &&"

ENV content_cov="${content_cov} coverage html -d /bids_dir/code/coverage_html &&"
ENV content_cov="${content_cov} coverage xml -o /bids_dir/code/coverage.xml &&"
ENV content_cov="${content_cov} coverage json -o /bids_dir/code/coverage.json"

# Write content to BIDSapp entrypoint script
RUN printf "$content_cov" > /app/run_coverage_cmp3.sh
RUN cat /app/run_coverage_cmp3.sh

# Set the working directory back to /app
# Acquire script to be executed
RUN chmod 775 /app/connectomemapper3/run.py
RUN chmod 775 /app/run_cmp3.sh
RUN chmod 775 /app/run_coverage_cmp3.sh
RUN chmod 777 /opt/freesurfer

#Temporary tmp folder
RUN /bin/bash -c "mkdir -p /var/tmp"
ENV TMPDIR /var/tmp
ENV TMP /var/tmp
ENV TEMP /var/tmp

RUN export

#COPY version /version
RUN mkdir /bids_dir && \
    chmod -R 777 /bids_dir

RUN mkdir /output_dir && \
    chmod -R 777 /output_dir

ENV FS_LICENSE /bids_dir/code/license.txt

# Set locale settings
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# Control MRTrix random number generation (RDG) for replicatable probabilistic tractography
# See https://community.mrtrix.org/t/random-number-generator/2063 for more details
ENV MRTRIX_RNG_SEED 1234

# Control ANTs random number generation (RDG) and multithreading
# See https://github.com/ANTsX/ANTs/wiki/antsRegistration-reproducibility-issues for more details
ENV ANTS_RANDOM_SEED 1234
# ENV ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS

RUN ldconfig
WORKDIR /tmp/
ENTRYPOINT ["/app/run_cmp3.sh"]

#Metadata
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="Connectome Mapper BIDS App"
LABEL org.label-schema.description="Connectome Mapper BIDS App - the processing core of Connectome Mapper 3"
LABEL org.label-schema.url="https://connectome-mapper-3.readthedocs.io"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.vcs-url="https://github.com/connectomicslab/connectomemapper3"
LABEL org.label-schema.version=$VERSION
LABEL org.label-schema.maintainer="Sebastien Tourbier <sebastien.tourbier@alumni.epfl.ch>"
LABEL org.label-schema.vendor="Connectomics Lab, Centre Hospitalier Universitaire Vaudois (CHUV), Lausanne, Switzerland"
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.docker.cmd="docker run --rm -v ~/data/bids_dataset:/bids_dir -t sebastientourbier/connectomemapper-bidsapp:${VERSION} /bids_dir /bids_dir/derivatives participant [--participant_label PARTICIPANT_LABEL [PARTICIPANT_LABEL ...]] [-session_label SESSION_LABEL [SESSION_LABEL ...]] [--anat_pipeline_config ANAT_PIPELINE_CONFIG] [--dwi_pipeline_config DWI_PIPELINE_CONFIG] [--func_pipeline_config FUNC_PIPELINE_CONFIG]  [--number_of_participants_processed_in_parallel NUMBER_OF_PARTICIPANTS_PROCESSED_IN_PARALLEL] [--fs_license FS_LICENSE]"
