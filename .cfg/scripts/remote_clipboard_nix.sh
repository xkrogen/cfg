#!/bin/bash

# Script to copy whatever was piped in to the remote host specified as the argument
# assumes the remote host is running *nix with xclip installed

# Strip trailing newline if present
perl -pe 'chomp if eof' | ssh $1 "DISPLAY=:0 xclip"
