#!/bin/bash
F="${SRC:?set SRC=/path/to/raw.MP4}"
D=$(dirname "$0")
ffmpeg -v error -ss $2 -t $3 -i "$F" -an -vf "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,eq=brightness=0.025:contrast=1.045:saturation=1.04:gamma=1.03,unsharp=5:5:0.45:5:5:0" -c:v libx264 -crf 11 -preset fast -pix_fmt yuv420p -y "$D/$1.mp4" && echo done $1
