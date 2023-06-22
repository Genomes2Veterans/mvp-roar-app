# import relevant modules to create test participant for roar_app

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
cursor = conn.cursor()

########################################################################

# specify participant information information for candidate patient table

roarid = 'ABCD'
mvpcoreid = 'A00000'
ssn = 'XXXXX0000'
firstname = 'Grumpy'
lastname = 'Dwarf'
dob = '1950-01-01'
sexmale = 1
race = 'White'
ethnicity = 'Not Hispanic or Latino'
corereleasedate = '2023-01-01'
pilotparticipant = 0
istestrecord = 1

# insert values into table and commit, use ? method to prevent injection
cursor.execute("""
	INSERT INTO roar_app.candidatePatient(roarid, mvpcoreid, ssn, firstname, lastname, dob, sexmale, race, ethnicity, corereleasedate, pilotparticipant, istestrecord) 
	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
roarid, mvpcoreid, ssn, firstname, lastname, dob, sexmale, race, ethnicity, corereleasedate, pilotparticipant, istestrecord)
conn.commit()

# address
street1 = '123 Main St'
city = 'New York'
state = 'NY'
zipcode = 12345
activeaddress = 1
actionid = 0

# insert values into table and commit, use ? method to prevent injection
cursor.execute("""
	INSERT INTO roar_app.patientAddress(roarid, street1, city, state, zipcode, activeaddress, actionid) 
	VALUES (?, ?, ?, ?, ?, ?, ?)""",
roarid, street1, city, state, zipcode, activeaddress, actionid) 
conn.commit()

print(firstname + ' ' + lastname + ' test participant created successfully.')
