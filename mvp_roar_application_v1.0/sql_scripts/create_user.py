# import relevant modules to create new user for roar_app

# for password hashing
from werkzeug.security import generate_password_hash, check_password_hash

# import datetime
from datetime import datetime

# for sql db connection
import pyodbc

# set connection credentials to add user to roar_app.user table
DRIVER='ODBC Driver 17 for SQL Server'
SERVER='{ENTER SERVER}'
DATABASE='{ENTER DATABASE}'
#USERNAME='{ENTER USERNAME}' if UID and passward required
#PASSWORD='{ENTER USERNAME}' if UID and passward required

# create connection string and define cursor
conn_str = 'DRIVER={%s};SERVER=%s;DATABASE=%s;Trusted_Connection=yes;'
# if UID and passward required: 
    #conn_str = 'DRIVER={%s};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s'
conn = pyodbc.connect(conn_str % (DRIVER, SERVER, DATABASE)) #, USERNAME, PASSWORD))
conn = pyodbc.connect(conn_str % (DRIVER, SERVER, DATABASE))
cursor = conn.cursor()

########################################################################

# specify user information

# get username - default = VA NT account 
username = input('Enter username: ')

# random password - will hash to save in user table 
password = input('Enter user password: ')

# user role - user, admin
role = input('Enter user role (admin or user): ')

# add user, is_active, default to True
activeuser = True

# create first user id or assign new one based on existing users

cursor.execute("SELECT username, userid FROM roar_app.users ORDER BY userid DESC;")
rows = cursor.fetchall()

# assign id

if rows == []:
	userid = 1000

else:
	userid = rows[0][1] + 1
	
# hash password for saving in tables
password_hash = generate_password_hash(password)

# add a datetime for when user was added to application
dateadded = datetime.now()

# insert values into table and commit, use ? method to prevent injection
cursor.execute("""INSERT INTO roar_app.users(userid, username, password_hash, activeuser, role, dateadded, dateremoved) VALUES (?, ?, ?, ?, ?, ?, ?)""",
userid, username, password_hash, activeuser, role, dateadded, None)
conn.commit()

print(username + ' created successfully.')
