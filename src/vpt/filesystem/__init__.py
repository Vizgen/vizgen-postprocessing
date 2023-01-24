from .vzgfs import vzg_open, filesystem_path_split, initialize_filesystem

# Prevent import from being removed as "unused"
assert vzg_open
assert filesystem_path_split
assert initialize_filesystem
