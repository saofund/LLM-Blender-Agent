# Complete Installation Guide for Hunyuan3D-2

## 1. Clone the Repository
```bash
git clone https://github.com/Tencent/Hunyuan3D-2
```

## 2. Download the Image-to-3D Model
Create a separate directory for weights if desired:
```bash
git lfs install  # Enables Git Large File Storage for the current session
git clone https://huggingface.co/tencent/Hunyuan3D-2    # 115GB
# Lighter version available:
# git clone https://huggingface.co/tencent/Hunyuan3D-2mini    # 46GB
```

## 3. Download the Text-to-Image Model
```bash
git lfs install
git clone https://huggingface.co/Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers-Distilled    # 27GB
```

## 4. Setup Environment
Navigate to the Hunyuan3D-2 directory:
```bash
# Create and activate conda environment (recommended)
conda create -n Hunyuan3D python=3.11
conda activate Hunyuan3D

# Install PyTorch from official website
pip3 install torch torchvision torchaudio

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install texture components
cd hy3dgen/texgen/custom_rasterizer
python3 setup.py install
cd ../../..
cd hy3dgen/texgen/differentiable_renderer
python3 setup.py install
```

## 5. Replace the API Server File
Replace the original `api_server.py` with the modified version from `hunyuan/api_server.py` 
(The official server lacks text-to-image functionality; the new file indicates required path replacements marked as "TODO")

## 6. Start the Server
```bash
python api_server.py
```