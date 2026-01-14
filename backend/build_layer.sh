#!/bin/bash

echo "Building Lambda layer for Python 3.12 with correct architecture..."

# Clean up previous builds
rm -rf lambda_layer
rm -f lambda_layer.zip

# Create layer directory structure
mkdir -p lambda_layer/python

# Install dependencies with correct Python version and architecture
pip install -r lambda/requirements.txt \
  --python-version 3.12 \
  --platform manylinux2014_x86_64 \
  --target lambda_layer/python \
  --only-binary=:all: \
  --upgrade

echo "✓ Lambda layer built successfully!"
echo "Layer size:"
du -sh lambda_layer/
