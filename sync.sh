#!/usr/bin/env bash

dir=$(realpath $(dirname "$0"))
fswatch -o "$dir" | while read f; do
  rsync -a "$dir" osmc@kodi:/home/osmc/.kodi/addons/
  echo -n .
done
