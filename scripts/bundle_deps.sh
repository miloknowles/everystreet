# NOTE: Must be run from top-level project directory! Make sure virtualenv is sourced.

rm -rf tmp && mkdir tmp && cd tmp
ZIP_NAME='deps_layer.zip'
DIR_NAME='deps_layer'

# Zip all of the Python libraries in virtualenv.
rm -rf $DIR_NAME
mkdir $DIR_NAME
cp -r ${VIRTUAL_ENV}/lib/python3.8/site-packages/* $DIR_NAME/
echo 'Copied site-packages to ${DIR_NAME}/'

# Clean out unnecessary files to reduce size.
rm -rf $DIR_NAME/*.dist-info
rm -rf $DIR_NAME/__pycache__
rm -rf $DIR_NAME/*.pth
rm -rf $DIR_NAME/pip*
rm -rf $DIR_NAME/wheel

# Delete the biggest libraries (scipy and numpy). We'll bundle these in their own layer.
rm -rf $DIR_NAME/scipy $DIR_NAME/numpy $DIR_NAME/scipy.libs $DIR_NAME/numpy.libs
echo 'Removed scipy and numpy'

rm -rf $DIR_NAME/flask $DIR_NAME/jinja2 $DIR_NAME/werkzeug $DIR_NAME/gunicorn

# Note: this will cause some errors, which I believe are due to walking through
# directories and deleting them at the same time.
find $DIR_NAME -type d -name "__pycache__" -exec rm -rf {} \;
echo 'Cleaned up extra files and folders'

zip -r -q ${ZIP_NAME} $DIR_NAME
echo "Zipped dependencies into ${ZIP_NAME}"

ls -lh ${ZIP_NAME}
echo "Done!"
