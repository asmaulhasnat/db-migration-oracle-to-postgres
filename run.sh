# first clone the project
git clone https://github.com/asmaulhasnat/db-migration-oracle-to-postgres.git
python3 --version  or  python --version
python3 -m venv venv
source venv/Scripts/activate
source venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.txt
python manage.py migrate
python manage.py runserver