#!/bin/sh
python3 -m venv .venv-$1
source .venv-$1/bin/activate
python -m pip install --upgrade pip
pip install jupyter
pip install ipykernel
pip install -r requirements.txt
python -m ipykernel install --user --name=$1 --display-name="(!) "$1
deactivate
