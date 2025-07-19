#!/bin/bash
# Install TaskMaster globally

echo "Installing TaskMaster CLI globally..."
npm install -g task-master

echo "Checking installation..."
npx task-master --version

echo "Done!"