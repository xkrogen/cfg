#!/bin/bash

# Script to copy whatever was piped in to the remote host specified as the argument
# assumes the remote host is running OSX

# Strip trailing newline if present
perl -pe 'chomp if eof' | ssh $1 pbcopy
