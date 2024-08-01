#!/bin/bash
# The following should fix up X servers to work properly on a unix machine
sudo su - root bash -c 'DISPLAY=:0 xhost +SI:localuser:ekrogen'
