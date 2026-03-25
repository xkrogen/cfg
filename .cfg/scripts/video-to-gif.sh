#!/bin/zsh
# video-to-gif.sh — Convert video files to GIFs using ffmpeg
# Intended for use as a macOS Shortcuts Quick Action
# Input: video file paths passed as arguments
# Output: GIF files placed next to the originals

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "Skipping (not a file): $file" >&2
        continue
    fi

    dir="$(dirname "$file")"
    base="$(basename "$file")"
    name="${base%.*}"
    output="${dir}/${name}.gif"

    # Avoid overwriting existing files
    if [ -f "$output" ]; then
        i=1
        while [ -f "${dir}/${name}_${i}.gif" ]; do
            i=$((i + 1))
        done
        output="${dir}/${name}_${i}.gif"
    fi

    # Two-pass encoding: generate optimal palette, then apply it
    palette=$(mktemp /tmp/palette_XXXXXX.png)
    ffmpeg -i "$file" -vf "fps=10,palettegen" -y "$palette" </dev/null &&
    ffmpeg -i "$file" -i "$palette" -filter_complex "fps=10[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" -y "$output" </dev/null
    rm -f "$palette"
    echo "$output"
done
