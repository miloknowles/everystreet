# NOTE: Must be run from top-level project directory! Make sure virtualenv is sourced.

ZIP_NAME='bundle.zip'

# Now add our library to the zip.
zip -g -r ${ZIP_NAME} python
echo "Added custom library in 'python'"

echo "Done!"
