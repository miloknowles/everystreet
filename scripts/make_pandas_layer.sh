# https://medium.com/swlh/how-to-add-python-pandas-layer-to-aws-lambda-bab5ea7ced4f

# Run from top directory!
rm -rf tmp && mkdir -p tmp/python

# Download pre-built packages.
cd tmp/python
# wget https://files.pythonhosted.org/packages/d3/e3/d9f046b5d1c94a3aeab15f1f867aa414f8ee9d196fae6865f1d6a0ee1a0b/pytz-2021.3-py2.py3-none-any.whl
# wget https://files.pythonhosted.org/packages/62/bb/44a4fd4dfcabc2b0c737bec472531f8156ac50b1f71bea8717afd7e5c1a4/pandas-1.4.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
# wget https://files.pythonhosted.org/packages/a6/92/5ddb9aab70fcca4b35e4b0b7ba1c1f994873cb13b139f4846a621bbcc936/geopandas-0.10.2-py2.py3-none-any.whl
# wget https://files.pythonhosted.org/packages/11/24/5e84be7dedaffc2d5a94c1266fc2420813f629500da4d244b6096448a59e/Shapely-1.8.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# unzip pytz-2021.3-py2.py3-none-any.whl
# unzip geopandas-0.10.2-py2.py3-none-any.whl
# unzip Shapely-1.8.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

# Install with pip to make sure dependencies are met.
pip install --target . pandas
pip install --target . pyproj
pip install --target . geopandas
pip install --target . Shapely

# Delete pycache everywhere.
find $DIR_NAME -type d -name "__pycache__" -exec rm -rf {} \;

# Clean up folder.
rm -r *.whl *.dist-info __pycache__

# Remove numpy because it's provided by AWS layer.
rm -rf numpy numpy.libs

# Zip into one archive.
cd ..
zip -q -r python.zip python/
ls -lh python.zip

echo 'Done'
