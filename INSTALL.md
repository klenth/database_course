Steps needed to set up SQL Lab
==============================

1. Copy distributed files to their home
    
   a. `db.sqlite3.dist` to `db.sqlite3`
   
   b. `sql_lab/settings.py.dist` to `sql_lab/settings.py`

2. Make any desired configuration changes in `sql_lab/settings.py`
   
   a. `ALLOWED_HOSTS`

   b. `STATIC_URL`

   c. `UPLOAD_DIR`

   d. `CLASS_TIMEZONE`
   
3. Generate a secret key

   a. `python generate_key.py > key.secret && chmod 600 key.secret`

4. Use the admin site to set up your user

   a. `python manage.py createsuperuser`

   b. With the web application running, open `/admin` and login with
      your superuser account.
   
