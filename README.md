<h1>mvp-roar-app</h1>

---

<h2>Description</h2>

Recruitment, enrollment, and data collection application for the MVP-ROAR-FH Study (MVP030). 

Flask web application deployed in Red Hat Enterprise Linux environment with Microsoft SQL Server Database. 
- https://www.redhat.com/en/technologies/linux-platforms/enterprise-linux 
- https://www.microsoft.com/en-us/sql-server/sql-server-2019

Application also tested using CentOS Stream environment and Microsoft SQL Server Docker Container.
- https://www.centos.org/centos-stream/
- https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-ver16&pivots=cs1-bash

v1.0 of application requires prior installation of Microsoft ODBC Driver for SQL Server (v17)
- https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16

Code included here is served locally with Python Waitress. Apache or other server/proxy requires additional setup, including web server gateway interface (wsgi).
- https://flask.palletsprojects.com/en/2.0.x/deploying/

MVP-ROAR clinicaltrials.gov: https://clinicaltrials.gov/study/NCT04178122

---

<h2>Environment Setup</h2>

**Note: current mvp roar application uses Python v3.8.14; see https://www.python.org/downloads/release/python-3814/**

**Clone mvp-roar-app repository to selected location:**

`git clone https://github.com/Genomes2Veterans/mvp-roar-app.git`

**Create virtual environment for relevant package install:**

`python -m venv mvp-roar-app/roar-app-env`

**Activate environment:**

`source mvp-roar-app/roar-app-env/bin/activate`

**Install relevant packages into activated environment from requirements.txt:**

`pip install -r mvp-roar-app/mvp_roar_application_v1.0/roar_app/requirements.txt`

---

<h2>Application Setup</h2>

**Note: A database will need to be instantiated and name included in connection strings. Code will require manual updates of all database connection strings in scripts included in 'sql scripts' folder and app/database.py prior to below steps.**

**Generate tables in SQL Server Database (should generate automatically with valid connection):**

`python ./mvp-roar-app/mvp_roar_application_v1.0/roar_app/run.py`

note: An error may occur at this step due to Werkzeug package version - use pip install Werkzeug~=2.0.0 to resolve.

Check 127.0.0.1:8080 in browser to ensure local application start-up.

![app](https://github.com/Genomes2Veterans/mvp-roar-app/assets/40616838/8225275c-3cff-44bb-b07f-fc8892b833c5)

Check database that tables have been successfully created.

![database_check](https://github.com/Genomes2Veterans/mvp-roar-app/assets/40616838/b0e46094-c0ff-4b06-9f47-125ad9b97802)

**Data for the following tables will need to be populated separately with relevant data:**
- candidatePatient will require batch upload of potential participants from source.
- patientAddress will require batch upload of potential participants from source.
- patientRandomization will require reference to a separate database table including pre-generated randomization statuses (see line 1505 in views.py)
- sta3nDim will require addition of relevant facility information.
- taskDim will require addition of relevant task information. (Task data for app v1.0)
![taskDIm](https://github.com/Genomes2Veterans/mvp-roar-app/assets/40616838/ce4e95c3-c542-4061-9985-9bf3c9cd83e0)

- medicationDim will require addition of relevant medication information.
- variantDim will require addition of relevant genetic variant information.
- surveyDim will require addition of relevant survey information (e.g. baseline versus end-of-study assessment)
- questionDim will require relevant survey item information.
- See views.py lines 1505 and 2416 for additional reference table requirements. 

---

<h2>User and Test Participant Setup</h2>

**Create User for login and test participant after table generation to begin using application:**  

User:

`python ./mvp-roar-app/mvp_roar_application_v1.0/sql_scripts/create_user.py`

CLI Prompts should read as follows:

1. Enter username: {Enter username}
2. Enter password: {Enter user password}
3. Enter user role (admin or user): {Designate role}
4. {Username} created successfully.  

Test participant:

`python ./mvp-roar-app/mvp_roar_application_v1.0/sql_scripts/create_test_participant.py`

CLI Prompts should read as follows:

1. Grumpy Dwarf test participant created successfully.
