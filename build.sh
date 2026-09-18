#!/usr/bin/env bash
# ==============================================================================
# BHARATH MASALA PRODUCTS — PRODUCTION RENDER BUILD SCRIPT
# ==============================================================================
set -o errexit

echo "=================================================="
echo "==> BHARATH MASALA — PRODUCTION BACKEND BUILD"
echo "=================================================="

echo "==> Step 1: Upgrading pip and installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> Step 2: Collecting static assets via WhiteNoise..."
python manage.py collectstatic --noinput --settings=config.settings.production

echo "==> Step 3: Applying database migrations..."
python manage.py migrate --noinput --settings=config.settings.production

echo "==> Production build completed successfully!"
echo "=================================================="
