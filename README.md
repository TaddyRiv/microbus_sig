py -3.12 -m venv .venv 
venv\Scripts\activate
pip install -r requirements.txt

pip freeze > requirements.txt 

python manage.py importar_microbuses datos/datos.xlsx
