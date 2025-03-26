启动混元3D-2的全部流程：

1、项目主页：git clone https://github.com/Tencent/Hunyuan3D-2

2、下载图生3D（可以单独找个目录下载权重）：
git lfs install # 这是git large file，大权重下载模式，放心执行，只影响当前session
git clone https://huggingface.co/tencent/Hunyuan3D-2    # 115G
# 有个迷你版本：git clone https://huggingface.co/tencent/Hunyuan3D-2mini    # 46G

3、下载文生图权重（可以单独找个目录下载权重）
git lfs install
git clone https://huggingface.co/Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers-Distilled    # 27G

4、进入Hunyuan3D-2目录
建议新建conda环境：
conda create -n Hunyuan3D python=3.11
conda activate Hunyuan3D
到官网安装torch：pip3 install torch torchvision torchaudio
安装官方依赖：
pip install -r requirements.txt
pip install -e .
# for texture
cd hy3dgen/texgen/custom_rasterizer
python3 setup.py install
cd ../../..
cd hy3dgen/texgen/differentiable_renderer
python3 setup.py install

5、将api_server.py文件替换为这里的：hunyuan\api_server.py
（官方server没有文生图功能，新的api_server.py上标明了需要替换的路径位置的地方为TODO）

6、启动server：python api_server.py