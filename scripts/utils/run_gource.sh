#!/bin/sh

gource -c 4 -b 000000 -1280x720 --auto-skip-seconds .1 \
		--hide mouse,progress --title "Connectome Mapper Development History" \
		--output-ppm-stream - | \
		ffmpeg -y -f 30 -r 28 -f image2pipe \
				-vcodec ppm -i - -vcodec libx264 -preset veryslow \
				-crf 28 -threads 0 -o - | \
				ffmpeg  -i - -filter_complex "[0:v]setpts=0.1*PTS[v]" -vcodec libx264 -preset veryslow \
						-crf 28 -threads 0 gource10x.mp4
