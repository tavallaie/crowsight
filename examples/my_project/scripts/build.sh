#!/usr/bin/env bash
# my_project/scripts/build.sh
echo "Building frontend..."
cd ../frontend || exit
npm install
npm run build
echo "Build complete."
