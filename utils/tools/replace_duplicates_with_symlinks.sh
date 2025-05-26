#!/bin/bash

find_duplicates_and_replace_with_symlinks() {
  local target_dir="$1"

  if ! command -v fdupes &> /dev/null; then
    echo "fdupes is not installed. Please install it first."
    return 1
  fi

  if [ -z "$target_dir" ]; then
    echo "Please provide a target directory."
    return 1
  fi

  if [ ! -d "$target_dir" ]; then
    echo "Target directory '$target_dir' does not exist."
    return 1
  fi

  fdupes -r -1 "$target_dir" | while IFS= read -r line; do
    local files=($line)
    local master_file="${files[0]}"

    # Start from the second file in the list
    for ((i = 1; i < ${#files[@]}; i++)); do
      local duplicate_file="${files[$i]}"

      # Remove the duplicate file
      rm -f "$duplicate_file"

      # Create a symbolic link
      ln -s "$master_file" "$duplicate_file"
      echo "Replaced '$duplicate_file' with symlink to '$master_file'"
    done
  done
}

# Check if a directory argument is provided
if [ -n "$1" ]; then
  find_duplicates_and_replace_with_symlinks "$1"
else
  echo "Usage: $0 <target_directory>"
  exit 1
fi