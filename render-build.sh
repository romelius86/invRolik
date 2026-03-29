#!/usr/bin/env bash

# Exit on error
set -o errexit

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Run backend update script (e.g., database migrations)
python pagina_web/actualizar_backend.py
