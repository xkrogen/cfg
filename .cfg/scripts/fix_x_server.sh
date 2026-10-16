#!/bin/bash
# The following should fix up X servers to work properly on a unix machine
user="$(id -un)" || exit "$?"
sudo env DISPLAY=:0 xhost "+SI:localuser:$user"
