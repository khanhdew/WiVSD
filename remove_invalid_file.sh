#!/bin/zsh
setopt NULL_GLOB
for f in **/*.csv; do
  lines=$(wc -l < "$f")
  if [ "$lines" -ne 4001 ]; then
    rm "$f" && echo "Đã xóa: $f ($lines dòng)"
  fi
done
