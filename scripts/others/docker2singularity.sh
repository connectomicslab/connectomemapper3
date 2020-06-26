#!/usr/bin/sh

cd ~/Data/datalad_test_processed

current_date_time="$(date "+%Y-%m-%d %H:%M:%S")" 
echo "Start time : ${current_date_time}"

docker run -v /var/run/docker.sock:/var/run/docker.sock -v "${PWD}/environments":/output --privileged -t --rm singularityware/docker2singularity --name connectomemapper-bidsapp_3_0_0-beta sebastientourbier/connectomemapper-bidsapp:3.0.0-beta-singularity

current_date_time="$(date "+%Y-%m-%d %H:%M:%S")"
echo "End time : ${current_date_time}"
