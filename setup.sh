#!/bin/bash

echo "🚀 Starting Project Setup..."

# 1. System Update and Core Dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nodejs npm git

# 2. Clone the Repository (assuming you run this script manually)
# git clone <your-repo-url>
# cd <your-repo-name>

# 3. Setup Relay Backend
echo "📦 Setting up Relay Backend..."
cd relay/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../../

# 4. Setup Relay Frontend
echo "📦 Setting up Relay Frontend..."
cd relay/frontend
npm install
npm run build # Build the static files for production
cd ../../

# 5. Setup Workshop Environment
echo "🧪 Setting up Workshop..."
cd workshop
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
echo "To run Relay control center: cd relay/backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0"
echo "To run Workshop: cd workshop && source venv/bin/activate && jupyter-lab --ip=0.0.0.0"