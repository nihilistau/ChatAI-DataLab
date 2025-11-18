Tag + push steps (PowerShell):

git tag -a v1.0.2-control-capsules.20251116 -m "Control Capsule bootstrap"
git push origin main
git push origin v1.0.2-control-capsules.20251116
`powershell
cd "D:/Files/Code 3/ChatAI-DataLab"
git status
git tag -a v1.0.3-control-capsules.20251118 -m "Kitchen notebooks + Parquet artifacts"
git push origin main
git push origin v1.0.3-control-capsules.20251118
`

After GitHub release is published and artifacts are uploaded, you can remove the local 
`release_artifacts` folder or keep it for future reference (it is currently untracked).
