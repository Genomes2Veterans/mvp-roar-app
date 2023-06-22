# Script to setup / connect to databases (ENTER DATABASE NAME)

# for creating mapper code
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Date, DateTime, Identity

# for configuration class code
from sqlalchemy.ext.declarative import declarative_base

# for creating foreign key relationships
from sqlalchemy.orm import relationship

# for configuration -engine querying table setup
from sqlalchemy import create_engine

# for user model - store and check hashed passwords
from werkzeug.security import generate_password_hash, check_password_hash

# create declarative base instance
Base = declarative_base()

# creat engine instance, connection to database
DRIVER='ODBC+Driver+17+for+SQL+Server'
SERVER='{ENTER SERVER}'
DATABASE='{ENTER DATABASE}'
#USERNAME='{ENTER USERNAME}' if UID and passward required
#PASSWORD='{ENTER USERNAME}' if UID and passward required

engine = create_engine('mssql+pyodbc://' + SERVER + '/' + DATABASE + '?trusted_connection=yes&driver=' + DRIVER, pool_pre_ping=True) # check connection, if stale/disconnected, recycle

#different cnxn string if username and password required

#engine = create_engine('mssql+pyodbc://' + USERNAME + ':' + PASSWORD + '@' + SERVER + '/' + DATABASE + '?&driver=' + DRIVER, pool_pre_ping=True) 

################################################################################################################################################

# APP USER TABLE

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create user table for individuals to login and record task actions

class userModel(Base):
	__tablename__ = 'users'
	__table_args__ = {'schema':'roar_app'} # w/ sql server autogenerates roar_app schema and tables
	
	userid = Column(Integer(), primary_key=True, autoincrement=False)
	username = Column(String(50), nullable=False)
	password_hash = Column(String(), nullable=False)
	activeuser = Column(Boolean(), nullable=False)
	role = Column(String(50), nullable=False)
	dateadded = Column(DateTime, nullable=False)
	dateremoved = Column(DateTime, nullable=True)
	
	def set_password(self, password):
		self.password_hash=generate_password_hash(password)
	
	def check_password(self, password):
		return check_password_hash(self.password_hash, password)
	
	def is_authenticated(self):
		return True
	
	def is_active(self):
		return self.activeuser
	
	def is_anonymous(self):
		return False
	
	def get_id(self):
		return self.userid

################################################################################################################################################

# PATIENT TABLES

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create candidate patient table 

class candidatePatient(Base):
	__tablename__ = 'candidatePatient'
	__table_args__ = {'schema':'roar_app'}
	
	roarid = Column(String(4), primary_key=True, autoincrement=False)
	mvpcoreid = Column(String(10), nullable=False)
	ssn = Column(String(9), nullable=False)
	firstname = Column(String(100), nullable=False)
	lastname = Column(String(100), nullable=False)
	dob = Column(Date, nullable=False)
	sexmale = Column(Boolean(), nullable=False)
	race = Column(String(100), nullable=True)
	ethnicity = Column(String(50), nullable=True)
	utc = Column(Boolean(), nullable=True)
	utcdate = Column(Date, nullable=True)
	utcid = Column(Integer(), nullable=True)
	deceased = Column(Boolean(), nullable=True)
	deceaseddate = Column(Date, nullable=True)
	deceasedid = Column(Integer(), nullable=True)
	losttofup = Column(Boolean(), nullable=True)
	losttofupdate = Column(Date, nullable=True)
	losttofupid = Column(Integer(), nullable=True)
	eligible = Column(Boolean(), nullable=True)
	eligibledate = Column(Date, nullable=True)
	eligibleid = Column(Integer(), nullable=True)
	declined = Column(Boolean(), nullable=True)
	declineddate = Column(Date, nullable=True)
	declinedid = Column(Integer(), nullable=True)
	consented = Column(Boolean(), nullable=True)
	consenteddate = Column(Date, nullable=True)
	consentedid = Column(Integer(), nullable=True)
	randomizationstatus = Column(String(10), nullable=True)
	randomizationdate = Column(Date, nullable=True) 
	randomizationid = Column(Integer(), nullable=True)
	withdrawn = Column(Boolean(), nullable=True)
	withdrawndate = Column(Date, nullable=True)
	withdrawnid = Column(Integer(), nullable=True)
	corereleasedate = Column(Date, nullable=False)
	pilotparticipant = Column(Boolean(), nullable=False)
	istestrecord = Column(Boolean(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient action table

class patientAction(Base):
	__tablename__ = 'patientAction'
	__table_args__ = {'schema':'roar_app'} 

	actionid = Column(Integer(), Identity(start=10000, increment=1), primary_key=True) # see MSSQL Autoincrement / Identity
	roarid = Column(String(4), nullable=False)
	taskid = Column(Integer(), nullable=False)
	taskdate = Column(Date, nullable=False)
	mode = Column(String(50), nullable=True)
	outcome = Column(String(50), nullable=True)
	timespent = Column(Integer(), nullable=True)
	note = Column(String(), nullable=True)
	staffid = Column(Integer(), nullable=False)
	actiondate = Column(DateTime, nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient address table

class patientAddress(Base):
	__tablename__ = 'patientAddress'
	__table_args__ = {'schema':'roar_app'} 

	addressid = Column(Integer(), Identity(start=20000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)
	street1 = Column(String(255), nullable=False)
	street2 = Column(String(255), nullable=True)
	street3 = Column(String(255), nullable=True)
	city = Column(String(100), nullable=False)
	state = Column(String(2), nullable=False)
	zipcode = Column(Integer(), nullable=False)
	activeaddress = Column(Boolean(), nullable=False)
	actionid = Column(Integer(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient phone table

class patientPhone(Base):
	__tablename__ = 'patientPhone'
	__table_args__ = {'schema':'roar_app'} 

	phoneid = Column(Integer(), Identity(start=30000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	patientphone = Column(String(12), nullable=False)
	activephone = Column(Boolean(), nullable=False)
	primaryphone = Column(Boolean(), nullable=False)
	actionid = Column(Integer(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient email table

class patientEmail(Base):
	__tablename__ = 'patientEmail'
	__table_args__ = {'schema':'roar_app'} 

	emailid = Column(Integer(), Identity(start=40000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	patientemail = Column(String(100), nullable=False)
	activeemail = Column(Boolean(), nullable=False)
	actionid = Column(Integer(), nullable=False)

#---------------------------------------------------------------------------------------------------------------------------------------------

# create patient station table

class patientStation(Base):
	__tablename__ = 'patientStation'
	__table_args__ = {'schema':'roar_app'} 

	patientstationid = Column(Integer(), Identity(start=50000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	sta3n = Column(Integer(), nullable=False)	
	activesta3n = Column(Boolean(), nullable=False)
	actionid = Column(Integer(), nullable=False)

#---------------------------------------------------------------------------------------------------------------------------------------------

# create patient provider table

class patientProvider(Base):
	__tablename__ = 'patientProvider'
	__table_args__ = {'schema':'roar_app'} 

	patientproviderid = Column(Integer(), Identity(start=60000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)
	provider = Column(String(100), nullable=False)		
	vaprovider = Column(Boolean(), nullable=False)
	vaprovidersta3n = Column(Integer(), nullable=True)	
	currentprovider = Column(Boolean(), nullable=False)
	actionid = Column(Integer(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient LDL table

class patientLDL(Base):
	__tablename__ = 'patientLDL'
	__table_args__ = {'schema':'roar_app'} 

	patientLDLid = Column(Integer(), Identity(start=70000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	LDLtype = Column(String(50), nullable=False)
	source = Column(String(50), nullable=False)
	value = Column(Integer(), nullable=False)
	unit = Column(String(5), nullable=False)	
	valuedate = Column(Date, nullable=False)	
	actionid = Column(Integer(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient medication table

class patientMedication(Base):
	__tablename__ = 'patientMedication'
	__table_args__ = {'schema':'roar_app'} 

	patientmedid = Column(Integer(), Identity(start=80000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	medname = Column(String(255), nullable=False)
	dose = Column(Integer(), nullable=False)
	unit = Column(String(5), nullable=False)
	medstartsource = Column(String(50), nullable=False)	
	medstartdate = Column(Date, nullable=False)
	medstartdateid = Column(Integer(), nullable=False)
	medendsource = Column(String(50), nullable=True)	
	medenddate = Column(Date, nullable=True)		
	medenddateid = Column(Integer(), nullable=True)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient genetic table

class patientGenetic(Base):
	__tablename__ = 'patientGenetic'
	__table_args__ = {'schema':'roar_app'} 

	roarid = Column(String(4), primary_key=True, autoincrement=False)
	variantid = Column(Integer(), nullable=False)
	molecdiagnosis = Column(Boolean(), nullable=True)
	molecdiagnosisid = Column(Integer(), nullable=True)	
	confirmtesting = Column(Boolean(), nullable=True)
	confirmtestingdate = Column(Date, nullable=True)
	sampletype = Column(String(10), nullable=True)	
	confirmresult = Column(Boolean(), nullable=True)
	resultclassification = Column(String(5), nullable=True)
	confirmsource = Column(String(25), nullable=True)
	confirmtestingid = Column(Integer(), nullable=True)
	interventiondelivered = Column(Boolean(), nullable=True)
	interventiondeliveredid = Column(Integer(), nullable=True)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient survey table

class patientSurvey(Base):
	__tablename__ = 'patientSurvey'
	__table_args__ = {'schema':'roar_app'} 

	patientsurveyid = Column(Integer(), Identity(start=90000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	qshortname = Column(String(255), nullable=False)
	response = Column(String(255), nullable=False)		
	actionid = Column(Integer(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient randomization allocation table

class patientRandomization(Base):
	__tablename__ = 'patientRandomization'
	__table_args__ = {'schema':'roar_app'} 

	patientrandomizationid = Column(Integer(), Identity(start=1000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	queueorder = Column(Integer(), nullable=False)
	randomizationid = Column(Integer(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# create patient intervention table

class patientIntervention(Base):
	__tablename__ = 'patientIntervention'
	__table_args__ = {'schema':'roar_app'} 

	patientinterventionid = Column(Integer(), Identity(start=2000, increment=1), primary_key=True)
	roarid = Column(String(4), nullable=False)	
	patientlettersent = Column(Boolean(), nullable=False)
	familylettersent = Column(Boolean(), nullable=False)
	familyletters = Column(Integer(), nullable=False)
	providerlettersent = Column(Boolean(), nullable=False)
	vaproviderletters = Column(Integer(), nullable=False)
	nonvaproviderletters = Column(Integer(), nullable=False)
	cprsnoteupload = Column(Boolean(), nullable=False)
	interventionid = Column(Integer(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

################################################################################################################################################

# DIMENSION TABLES

#-----------------------------------------------------------------------------------------------------------------------------------------------

# VA sta3n dimension table

class sta3nDim(Base):
	__tablename__ = 'sta3nDim'
	__table_args__ = {'schema':'roar_app'}
	
	sta3n = Column(Integer(), primary_key=True, autoincrement=False)
	sta3nname = Column(String(255), nullable=False)
	location = Column(String(255), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# task dimension table

class taskDim(Base):
	__tablename__ = 'taskDim'
	__table_args__ = {'schema':'roar_app'}
	
	taskid = Column(Integer(), primary_key=True, autoincrement=False)
	taskname = Column(String(50), nullable=False)
	taskdescription = Column(String(255), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# medication dimension table

class medicationDim(Base):
	__tablename__ = 'medicationDim'
	__table_args__ = {'schema':'roar_app'}
	
	medid = Column(Integer(), primary_key=True, autoincrement=False)
	medname = Column(String(), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# variant dimension table

class variantDim(Base):
	__tablename__ = 'variantDim'
	__table_args__ = {'schema':'roar_app'}
	
	variantid = Column(Integer(), primary_key=True, autoincrement=False)
	cdot = Column(String(100), nullable=False)
	rsID = Column(String(100), nullable=False)
	axID = Column(String(100), nullable=False)
	variantdescription = Column(String(255), nullable=False)

#-----------------------------------------------------------------------------------------------------------------------------------------------

# survey dimension table

class surveyDim(Base):
	__tablename__ = 'surveyDim'
	__table_args__ = {'schema':'roar_app'}
	
	surveyqid = Column(Integer(), primary_key=True, autoincrement=False)
	surveyname = Column(String(100), nullable=False)
	item = Column(String(10), nullable=False)
	questionid = Column(Integer(), nullable=False)
	
# survey dimension table

class questionDim(Base):
	__tablename__ = 'questionDim'
	__table_args__ = {'schema':'roar_app'}
	
	questionid = Column(Integer(), primary_key=True, autoincrement=False)
	qshortname = Column(String(50), nullable=False)
	qfull = Column(String(), nullable=False)
	itemresponseoptions = Column(String(), nullable=False)
	itemdescription = Column(String(255), nullable=False)

################################################################################################################################################

# initialize tables (if none exist)
Base.metadata.create_all(engine)

# dim tables will need to be populated on backend with relevant data 
    # e.g. VA stations, task type information, medication information, variant data, survey and question items