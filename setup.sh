#!/bin/bash

echo "🚀 Starting Project Setup..."

# 1. System Update and Core Dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nodejs npm git

# 2. Clone the Repository (assuming you run this script manually)
# git clone <your-repo-url>
# cd <your-repo-name>

# 3. Setup Playground Backend
echo "📦 Setting up Playground Backend..."
cd playground/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../../

# 4. Setup Playground Frontend
echo "📦 Setting up Playground Frontend..."
cd playground/frontend
npm install
npm run build # Build the static files for production
cd ../../

# 5. Setup Kitchen Environment
echo "🧪 Setting up Kitchen..."
cd kitchen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# 6. Fetch External Assets (Optional)
echo "📂 Fetching large assets..."
./scripts/fetch_assets.sh # This script would contain gdown or git-lfs commands

# 7. Final Instructions
echo "✅ Setup Complete!"
echo "To run Playground control center: cd playground/backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0"
echo "To run Kitchen: cd kitchen && source venv/bin/activate && jupyter-lab --ip=0.0.0.0"