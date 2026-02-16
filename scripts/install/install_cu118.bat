@echo off
chcp 65001 > nul

:: install torch 2.1.2
:: or conda install pytorch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 pytorch-cuda=12.1 -c pytorch -c nvidia
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

:: install dependencies
pip install -r requirements.txt

echo 所有命令执行完成！
pause