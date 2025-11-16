#!/bin/bash

echo "🚀 Starting Project Setup..."

# 1. System Update and Core Dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nodejs npm git

# 2. Clone the Repository (assuming you run this script manually)
# git clone <your-repo-url>
# cd <your-repo-name>

# 3. Setup ChatAI Backend
echo "📦 Setting up ChatAI Backend..."
	
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../../

# 4. Setup ChatAI Frontend
echo "📦 Setting up ChatAI Frontend..."
cd chatai/frontend
npm install
npm run build # Build the static files for production
cd ../../

# 5. Setup DataLab Environment
echo "🧪 Setting up DataLab..."
cd datalab
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
echo "To run ChatAI: cd chatai/backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0"
echo "To run DataLab: cd datalab && source venv/bin/activate && jupyter-lab --ip=0.0.0.0"