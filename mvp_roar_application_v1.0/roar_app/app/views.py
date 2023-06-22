# Main application routes / test

# Import relevant python modules and define engine connection

# note can pass functions to jinja templates, in addition to data parameters.

# datetime and dateutil functions
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

# regex
import re

# import data packages
import pandas as pd
import numpy as np
import json
import plotly
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Flask
from flask import abort, flash, jsonify, make_response, redirect, render_template, request, session, send_from_directory, url_for
from flask_login import LoginManager, current_user, login_user, login_required, logout_user

# Import helper functions and init files
from app import app
from app.database import engine, userModel, candidatePatient, patientAction, patientAddress, patientPhone, patientEmail, \
	patientStation, patientProvider, patientLDL, patientGenetic, patientMedication, patientSurvey, patientRandomization, \
	patientIntervention, sta3nDim, taskDim, medicationDim, variantDim, surveyDim, questionDim
from app.helpers import calculatedAge

# Import database modules, sqlalchemy
from sqlalchemy import and_, case, literal_column, update
from sqlalchemy.orm import sessionmaker, load_only
from sqlalchemy.sql.expression import func

# set connection with mssql to session
DBsession = sessionmaker(bind=engine)
session = DBsession()


################################################################################################################################################

# Add routes for unique pages

################################################################################################################################################

# Configure login manager and credentials for login page

# Set login manager
# use @login_required decorator in all path routes to require login access
login_manager = LoginManager()

# Configure for login
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create loader function to load user into session
@login_manager.user_loader
def load_user(userid):
	
	try:
		id_value = session.query(userModel).get(int(userid)) # load id to specify completer of tasks.
	except:
		session.rollback() # if session stale, rollback
	
	# close query session - return session to pool
	session.close()
	
	return id_value
	
# Create app route for login
@app.route("/", methods=["POST", "GET"])
def login():
	
	# Check if current user is already logged in, direct 'home' if so
	if current_user.is_authenticated:
		return redirect("/home")
	
	# Get information from user login fields and check database for status
	# *Note to add user, use separate sql script - create_user.py
	if request.method == "POST":
		username = request.form.get("username")
		
		try:
			user = session.query(userModel).filter_by(username = username).first()
		except:
			session.rollback() # if session stale, rollback

			# logout user
			logout_user(user)

			# define user as None to redirect to login
			user = None
		
		# close query session - return session to pool
		session.close()
		
		# if user name is none, send back to login # need to monitor this.....
		if username is None or user is None:
			
			return render_template("login.html")
		
		# ensure query includes a row, check user password, and verify user is considered active
		elif user is not None and user.check_password(request.form.get("password")) and user.is_active():
			login_user(user)
			
			# set session permanent true for idle logout after 12 hours - see app.config in __init__.py
			session.permanent = True
			
			return redirect("/home")
		
		else:
			return redirect("/")
	
	# Get login.html as default page
	
	return render_template("login.html") 

################################################################################################################################################

# Logout function
@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect("/")

################################################################################################################################################

# Home directory / dashboard

@app.route("/home", methods=["GET"])
@login_required
def home():
	
	# query candidate patient table and return basic patient information for user selection

	participantStatus = session.query(
				case(
				(candidatePatient.deceased == 1, literal_column("'DECEASED'")),
				(candidatePatient.eligible == 0, literal_column("'NOT ELIGIBLE'")),
				(and_(candidatePatient.eligible == 1, candidatePatient.declined == 1), literal_column("'DECLINED'")),
				(and_(candidatePatient.eligible == 1, candidatePatient.utc == 1), literal_column("'UNABLE TO CONTACT'")),
				(and_(candidatePatient.eligible == 1, candidatePatient.consented == 1, candidatePatient.randomizationstatus.is_(None), 
					candidatePatient.withdrawn.is_(None), candidatePatient.losttofup.is_(None)), literal_column("'CONSENTED'")),
				(candidatePatient.randomizationstatus.is_not(None), literal_column("'RANDOMIZED'")),
				(and_(candidatePatient.consented == 1, candidatePatient.withdrawn.is_not(None), 
					candidatePatient.losttofup.is_(None)), literal_column("'WITHDRAWN'")),
				(and_(candidatePatient.consented == 1, candidatePatient.withdrawn.is_(None), candidatePatient.losttofup.is_not(None)), 
					literal_column("'LOST TO FOLLOW UP'")),
				else_ = literal_column("'PENDING'")
				)
				).filter(candidatePatient.pilotparticipant == 0, candidatePatient.istestrecord == 0
				).all()

	# participant sex breakdown 
	participantsSex = session.query(candidatePatient.sexmale
					).filter(candidatePatient.pilotparticipant == 0, candidatePatient.consented == 1, candidatePatient.istestrecord == 0
					).order_by(candidatePatient.lastname).all()
	
	# participant race breakdown						   
	participantsRace = session.query(candidatePatient.race
					).filter(candidatePatient.pilotparticipant == 0, candidatePatient.consented == 1, candidatePatient.istestrecord == 0
					).order_by(candidatePatient.lastname).all()
	
	# participant randomization arm breakdown			   
	participantsRandomized = session.query(candidatePatient.randomizationstatus
					).filter(candidatePatient.randomizationstatus != None, candidatePatient.istestrecord == 0, candidatePatient.pilotparticipant == 0
					).order_by(candidatePatient.lastname).all()

	# participation confirmation results breakdown
	confirmResult = session.query(patientGenetic.confirmresult
					).join(candidatePatient, patientGenetic.roarid == candidatePatient.roarid
					).filter(candidatePatient.pilotparticipant == 0, patientGenetic.confirmresult != None
					).order_by(patientGenetic.roarid).all()
	
	# participant confirmation test specimen type breakdown						   
	specimenType = session.query(patientGenetic.sampletype
					).join(candidatePatient, patientGenetic.roarid == candidatePatient.roarid
					).filter(candidatePatient.pilotparticipant == 0, patientGenetic.sampletype != None
					).order_by(patientGenetic.roarid).all()
	
	# breakdown of core release and letter distribution
	participantsCoreRelease = session.query(candidatePatient.corereleasedate,
					).filter(candidatePatient.pilotparticipant == 0, candidatePatient.istestrecord == 0
					).order_by(candidatePatient.lastname).all()

	# consented participant breakdown
	participantsConsented = session.query(candidatePatient.consenteddate,
					).filter(candidatePatient.pilotparticipant == 0, candidatePatient.istestrecord == 0, candidatePatient.consented == 1
					).order_by(candidatePatient.lastname).all()

	# total states, all patients
	totalState = session.query(patientAddress.state,
					).join(candidatePatient, patientAddress.roarid == candidatePatient.roarid
					).filter(candidatePatient.pilotparticipant == 0, candidatePatient.istestrecord == 0, patientAddress.activeaddress == 1
					).all()

	# enrolled states, only consented patients
	participantsState = session.query(patientAddress.state,
					).join(candidatePatient, patientAddress.roarid == candidatePatient.roarid
					).filter(candidatePatient.pilotparticipant == 0, candidatePatient.istestrecord == 0, candidatePatient.consented == 1, patientAddress.activeaddress == 1
					).all()
	
	# close query transaction
	session.close()

	# participant status
	status = [x for sublist in participantStatus for x in sublist] # list comprehension to parse list of tuples
	uniqueStatus, uniqueStatusCounts = np.unique(status, return_counts = True)
	
	# participant sex
	sexMale = [x for sublist in participantsSex for x in sublist] # list comprehension to parse list of tuples
	sexValues = { True: "MALE", False: "FEMALE" }
	sexMale = [sexValues[label] for label in sexMale]
	uniqueSex, uniqueSexCounts = np.unique(sexMale, return_counts = True)
	
	# participant race
	race = [x for sublist in participantsRace for x in sublist] # list comprehension to parse list of tuples
	race = ["Unknown" if r is None else r for r in race]
	uniqueRace, uniqueRaceCounts = np.unique(race, return_counts = True)

	# participant randomization
	randomized = [x for sublist in participantsRandomized for x in sublist] # list comprehension to parse list of tuples
	uniqueRandomized, uniqueRandomizedCounts = np.unique(randomized, return_counts = True)

	# confirmed results
	confirmResult = [x for sublist in confirmResult for x in sublist] # list comprehension to parse list of tuples
	resultValues = { True: "CONFIRMED", False: "NOT CONFIRMED" }
	confirmResult = [resultValues[label] for label in confirmResult]
	uniqueResult, uniqueResultCounts = np.unique(confirmResult, return_counts = True)
	
	# specimen type
	specimen = [x for sublist in specimenType for x in sublist] # list comprehension to parse list of tuples
	uniqueSpecimen, uniqueSpecimenCounts = np.unique(specimen, return_counts = True)
	
	# core release
	corerelease = [x for sublist in participantsCoreRelease for x in sublist] # list comprehension to parse list of tuples
	uniqueCRdates, uniqueCRcounts = np.unique(corerelease, return_counts = True)

	# state total
	totalStates = [x for sublist in totalState for x in sublist] # list comprehension to parse list of tuples
	uniqueTotalStates, uniqueTotalStateCounts = np.unique(totalStates, return_counts = True)

	# state enrolled
	states = [x for sublist in participantsState for x in sublist] # list comprehension to parse list of tuples
	uniqueStates, uniqueStateCounts = np.unique(states, return_counts = True)
	
	# cumulative enrollment
	dtrange = pd.date_range('2020-04-01', datetime.today())
	dates = np.array(dtrange.date)
	consents = [x for sublist in participantsConsented for x in sublist] # list comprehension to parse list of tuples
	uniqueConsentDates, uniqueConsentCounts = np.unique(consents, return_counts = True)
	datedict = dict(zip(uniqueConsentDates, uniqueConsentCounts))
	
	longdatacounts = []
	
	for date in dates:
		val = datedict[date] if date in datedict else 0
		longdatacounts.append(val)
	
	cumulativeenrollment = np.cumsum(np.array(longdatacounts))

	# get consent counts for past 2 weeks, 4 weeks, and 8 weeks
	
	todaysDate = date.today()
	
	twoWeekTotal = 0
	fourWeekTotal = 0
	eightWeekTotal = 0
	consentTotal = 0
	
	for consent in consents:
		if consent >= todaysDate - timedelta(days = 14):
			twoWeekTotal += 1
		if consent >= todaysDate - timedelta(days = 28):
			fourWeekTotal += 1
		if consent >= todaysDate - timedelta(days = 56):
			eightWeekTotal += 1
			
		consentTotal += 1
	
	consentedDates = [todaysDate - timedelta(days = 14), todaysDate - timedelta(days = 28), todaysDate - timedelta(days = 56), np.min(consents)]
	consentedCounts = [twoWeekTotal, fourWeekTotal, eightWeekTotal, consentTotal]

	# process data for cumulative counts table

	progressTab = pd.DataFrame([dtrange, np.array(dtrange.month), np.array(dtrange.month_name()), np.array(dtrange.year), np.array(longdatacounts)]).T
	progressTab.columns = ["date", "month", "month_name", "year", "monthenroll"]
	progressTab = progressTab[progressTab.date >= datetime(2020, 6, 1)].drop(['date'], axis=1)
	# snip out pilots / anyone before 06/01/2020 was pilot
	progressTab = progressTab.groupby(by=["year", "month", "month_name"]).sum().reset_index()
	progressTab["cumenroll"] = np.cumsum(progressTab["monthenroll"])
	progressTab = progressTab.loc[18:,:] # select only those rows beginning December 2021 (first push since variant curation issues solved
	monthtarget = relativedelta(datetime(2022, 9, 30), datetime(2021, 11, 30)) # specify dates of 'enrollment' 06/01/2020 thru 09/30/2022
	progressTab["monthtarget"] = int(np.ceil(244 / (monthtarget.months + monthtarget.years * 12)))
	progressTab["studytarget"] = np.cumsum(progressTab["monthtarget"])
	

	# make plots

	fig = make_subplots(
			rows = 2, cols = 5,
			specs = [[{"type": "bar", "colspan": 2}, None, {"type": "domain"}, {"type": "xy", "colspan": 2}, None],
			[{"type": "domain"}, {"type": "domain"}, {"type": "domain"}, {"type": "domain"}, {"type": "domain"}]],
			subplot_titles = ("Letters by core release date", "Recruitment status", "Cumulative enrollment", "Participant sex", 
				"Participant race", "Randomization", "Genetic result confirmation", "Genetic specimen type")
				)
	
	fig.add_trace(go.Bar(x=uniqueCRdates, y=uniqueCRcounts), row = 1, col = 1)
	fig.add_trace(go.Pie(labels = uniqueStatus, values = uniqueStatusCounts, textinfo='label+percent+value', textposition='inside', insidetextorientation='horizontal'), row = 1, col = 3)	
	fig.add_trace(go.Scatter(x=dates, y=cumulativeenrollment), row = 1, col = 4)
	fig.add_trace(go.Pie(labels = uniqueSex, values = uniqueSexCounts, textinfo='label+percent+value', textposition='inside', insidetextorientation='horizontal'), row = 2, col = 1)
	fig.add_trace(go.Pie(labels = uniqueRace, values = uniqueRaceCounts, textinfo='label+percent+value', textposition='inside', insidetextorientation='horizontal'), row = 2, col = 2)
	fig.add_trace(go.Pie(labels = uniqueRandomized, values = uniqueRandomizedCounts, textinfo='label+percent+value', textposition='inside', insidetextorientation='horizontal'), row = 2, col = 3)
	fig.add_trace(go.Pie(labels = uniqueResult, values = uniqueResultCounts, textinfo='label+percent+value', textposition='inside', insidetextorientation='horizontal'), row = 2, col = 4)
	fig.add_trace(go.Pie(labels = uniqueSpecimen, values = uniqueSpecimenCounts, textinfo='label+percent+value', textposition='inside', insidetextorientation='horizontal'), row = 2, col = 5)


	fig.update_annotations(font_size = 22)
	fig.update_layout(height = 900, showlegend = False, font_size = 22, uniformtext_mode='hide', uniformtext_minsize=12, template="seaborn")
	graphJSON = json.dumps(fig, cls = plotly.utils.PlotlyJSONEncoder)


	# add choropleth by state - having some issues adding it to subplot
	
	# eligible

	roarmap = go.Figure(data=go.Choropleth(
						locations=uniqueTotalStates,
						z=uniqueTotalStateCounts,
						locationmode='USA-states',
						colorscale = "Mint",
						colorbar_title="Total released",
						colorbar_len = 0.7
					))
	
	roarmap.update_layout(
				title_text = 'Core release participants by state',
				title = {'y':0.95, 'x':0.5, 'xanchor':'center'},
				geo_scope = 'usa',
				height = 500,
				width = 940, 
				font_size = 16,
				margin = {"r":0, "t":0, "l":0, "b":0},
				dragmode = False,
				template = "seaborn"
					  )

	mapJSON = json.dumps(roarmap, cls = plotly.utils.PlotlyJSONEncoder)

	# enrolled
	
	roarmap2 = go.Figure(data=go.Choropleth(
						locations=uniqueStates,
						z=uniqueStateCounts,
						locationmode='USA-states',
						colorscale = "Mint",
						colorbar_title="Total enrolled",
						colorbar_len = 0.7
					))
	
	roarmap2.update_layout(
				title_text = 'MVP-ROAR participants by state',
				title = {'y':0.95, 'x':0.5, 'xanchor':'center'},
				geo_scope = 'usa',
				height = 500,
				width = 940, 
				font_size = 16,
				margin = {"r":0, "t":0, "l":0, "b":0},
				dragmode = False,
				template = "seaborn"
					  )

	mapJSON2 = json.dumps(roarmap2, cls = plotly.utils.PlotlyJSONEncoder)

	# wrap response using make_response - set headers to allow access-control-allow-oring
	response = make_response(render_template("home.html", graphJSON=graphJSON, mapJSON=mapJSON, mapJSON2=mapJSON2, consentedCounts=consentedCounts, 
							consentedDates=consentedDates, progressTab=progressTab.to_dict("records"),
							today = date.today, strftime=datetime.strftime))
							
	response.headers['Access-Control-Allow-Origin'] = ['http://127.0.0.1:8080', 'http://localhost:8080', 'http://127.0.0.1:8080/', 'http://localhost:8080/'] #required to get topojson map data / app does not have internet access
	
	return response

################################################################################################################################################

# serve data files for read behind firewall:

@app.route("/data", methods=["POST", "GET"])
@login_required
def data():
	return render_template('data.html') # required for plotly/app to access topojson map data, application does not have internet access

################################################################################################################################################

# aggregate view of patients

@app.route("/participants", methods=["POST", "GET"])
@login_required
def participants():
	
	# check if user selected individual participant
	if request.method == "POST":
		roar_id = request.form["userIdSelect"]
		
		# redirect to participant detail
		return redirect(url_for("participant_detail", roar_id=roar_id))
		
	# query candidate patient table and return basic patient information for user selection 
	participants = session.query(candidatePatient).order_by(candidatePatient.lastname).all()
	
	# close query transaction
	session.close()
	
	# render participant list view
	return render_template("participants.html", cpts = participants)

################################################################################################################################################

# participant detail view

@app.route("/participant_detail/<roar_id>", methods=["POST", "GET"])
@login_required
def participant_detail(roar_id):
		
	# query required data for participant detail page and render
	participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    candidatePatient.dob,
								    candidatePatient.sexmale,
								    candidatePatient.race,
								    candidatePatient.ethnicity,
								    candidatePatient.deceased,
								    candidatePatient.deceaseddate,
								    candidatePatient.eligible,
								    candidatePatient.eligibledate,
								    candidatePatient.declined,
								    candidatePatient.declineddate,
								    candidatePatient.losttofup,
								    candidatePatient.losttofupdate,
								    candidatePatient.consented,
								    candidatePatient.consenteddate,
								    candidatePatient.randomizationstatus,
								    candidatePatient.randomizationdate,
								    candidatePatient.withdrawn,
								    candidatePatient.withdrawndate,
								    candidatePatient.corereleasedate,
								    candidatePatient.pilotparticipant,
								    patientAddress.street1,
								    patientAddress.street2,
								    patientAddress.street3,
								    patientAddress.city,
								    patientAddress.state,
								    patientAddress.zipcode
								).join(patientAddress, candidatePatient.roarid == patientAddress.roarid
								).filter(candidatePatient.roarid == roar_id, patientAddress.activeaddress == 1
								).first()
		
	# query for list of active phone numbers
	participantphone = session.query(patientPhone.patientphone,
								patientPhone.primaryphone
								).filter(patientPhone.roarid == roar_id, patientPhone.activephone == 1
								).order_by(patientPhone.primaryphone.desc()
								).all()
		
	# query for list of active emails
	participantemail = session.query(patientEmail.patientemail
								).filter(patientEmail.roarid == roar_id, patientEmail.activeemail == 1
								).all()
		
	# query for active VA
	participantVA = session.query(patientStation.sta3n,
								sta3nDim.sta3nname
								).join(sta3nDim, patientStation.sta3n == sta3nDim.sta3n
								).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1
								).first()
		
	# query for active providers
	participantproviders = session.query(patientProvider.provider,
								patientProvider.vaprovider
								).filter(patientProvider.roarid == roar_id, patientProvider.currentprovider == 1
								).all()
											 
	# query for LDL information
	participantLDL = session.query(patientLDL.LDLtype,
								patientLDL.value,
								patientLDL.unit,
								patientLDL.valuedate
								).filter(patientLDL.roarid == roar_id
								).all()
		
	# query for active medications
	participantmeds = session.query(patientMedication.medname,
								patientMedication.dose,
								patientMedication.unit,
								patientMedication.medstartdate,
								patientMedication.medenddate
								).filter(patientMedication.roarid == roar_id
								).order_by(patientMedication.medenddate, patientMedication.medname
								).all()
		
	# query for genetic information
	participantgenetic = session.query(patientGenetic.molecdiagnosis,
								patientGenetic.confirmtesting,
								patientGenetic.confirmtestingdate,
								patientGenetic.confirmresult,
								patientGenetic.confirmsource,
								variantDim.cdot,
								variantDim.rsID,
								variantDim.axID
								).join(variantDim, patientGenetic.variantid == variantDim.variantid
								).filter(patientGenetic.roarid == roar_id
								).first()
										  
	# action log
	participantlog = session.query(patientAction.taskid,
								taskDim.taskname,
								patientAction.taskdate,
								patientAction.mode,
								patientAction.outcome,
								patientAction.note
								).join(taskDim, patientAction.taskid == taskDim.taskid
								).filter(patientAction.roarid == roar_id
								).order_by(patientAction.actiondate.desc()
								).all()
		
	# helper calculate age
	ptAge = calculatedAge(participant.dob)
	
	# close query transaction
	session.close()
	
	# render participant list, pass relevant data and functions.	
	return render_template("participant_detail.html", 
									
								# data
								pt = participant, ptAge = ptAge, ptPhone = participantphone, \
								ptEmail = participantemail, ptVA = participantVA, ptProv = participantproviders, \
								ptLDL = participantLDL, ptGen = participantgenetic, ptMeds = participantmeds, \
								ptLog = participantlog, 
									
								# functions
								today = date.today, timedelta = timedelta, strptime=datetime.strptime, relativedelta=relativedelta, max=np.max, min=np.min)


################################################################################################################################################

# record chart_review

@app.route("/chart_review", methods=["POST"])
@login_required
def chart_review():
	
	if request.method == "POST":
		
		# Participant information
		roar_id = request.form["chartReviewID"]
		
		# to do join health data
		
		# query required data for participant detail
		participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    candidatePatient.dob,
								    candidatePatient.sexmale,
								    patientAddress.street1,
								    patientAddress.street2,
								    patientAddress.street3,
								    patientAddress.city,
								    patientAddress.state,
								    patientAddress.zipcode
								).join(patientAddress, candidatePatient.roarid == patientAddress.roarid
								).filter(candidatePatient.roarid == roar_id, patientAddress.activeaddress == 1
								).first()
		
		ptAge = calculatedAge(participant.dob)
		
		# VA Station Data
		vaSta3ns = session.query(sta3nDim.sta3nname).order_by(sta3nDim.location).all()
	
		# Variant data
		susV = session.query(variantDim).order_by(variantDim.cdot).all()
		
		# Medication data
		meds = session.query(medicationDim).order_by(medicationDim.medname).all()
		
		# close query transaction
		session.close()
	
	# render chart review page
	return render_template("chart_review.html", pt = participant, ptAge = ptAge, vaSta3ns = vaSta3ns, susV = susV, meds = meds)

################################################################################################################################################

# get data from chart review template and commit to study database

@app.route("/commit_chart_review", methods=["POST"])
@login_required
def commit_chart_review():
	
	if request.method == "POST":
		
		# collect elements here for committing to databases
		
		chartdata = request.form.to_dict()
		
		# validate input data - if suspicious or empty data return error
		
		# check eligibility data, if conflicting return error
		if chartdata["eligible"] == "Yes" and (chartdata["deceased"] == "Yes" or chartdata["fh"] == "Yes"):
			
				errormsg = "Some conflicting eligibility information was entered, check deceased and/or molecular diagnosis data."
				
				return render_template("error.html", errormsg = errormsg)		
		
		
		# check rest of data inputs if not deceased:
		if chartdata["eligible"] == "Yes":
		
			# set iterator to check total # of empties for first medication field
			firstmedvaluecount = 0
		
			for key in chartdata.keys():
		
				# check format of va station
				if key == "vaStation" and not re.findall('[(][0-9]{3}[)][a-zA-Z,() ]+', chartdata[key]):
				
					errormsg = "VA Station format is incorrect: (3 Digit Station Number) Station Name"
				
					return render_template("error.html", errormsg = errormsg)
			
			
				# check provider name format
				if key == "vaPCP" and not re.findall('[a-zA-Z]+[ ][a-zA-Z-,]+[ ][a-zA-Z]+', chartdata[key]):
				
					errormsg = "VA PCP format is incorrect: First Name (Space) Last Name, Degree"
				
					return render_template("error.html", errormsg = errormsg)
			
			
				# check telephone format
				if key == "tel1" and not re.findall('[0-9]{3}[-][0-9]{3}[-][0-9]{4}', chartdata[key]):
				
					errormsg = "Telephone number format was not correct: ###-###-####"
				
					return render_template("error.html", errormsg = errormsg)
			
			
				# check telephone format (2)
				if key == "tel2" and not chartdata[key].strip() == '' and not re.findall('[0-9]{3}[-][0-9]{3}[-][0-9]{4}', chartdata[key]):
				
					errormsg = "Telephone number format was not correct: ###-###-####"
				
					return render_template("error.html", errormsg = errormsg)
				
				
				# check if outcome date is in the future
				if (key == "maxLDLdate" or key == "recentLDLdate" or key == "dateCompleted" or (key.startswith("meddate") and chartdata[key].strip() != '')):
					
					if datetime.strptime(chartdata[key], '%Y-%m-%d') > datetime.today():
			
						errormsg = "Entered LDL, medication, completed chart review dates are in the future."
				
						return render_template("error.html", errormsg = errormsg)		
		
		
				# med, tel2, and notes are "optional"

				# TEMP CHANGE TO ALLOW FOR ENTRY OF NOSUSPECT VARIANT: CB 2021-11-15 -- key != "suspectVariant" and

				if not key.startswith("med") and key != "tel2" and key != "notes" and chartdata[key].strip() == '': 
			
					errormsg = "A required entry was not made - check drop down, numeric, and date elements for accuracy."
				
					return render_template("error.html", errormsg = errormsg)
			
			
				# count medication fields that are empty (first box)
				if key.startswith("med") and re.findall('[0-9]', key) == []:
				
					if chartdata[key].strip() == '':
					
						firstmedvaluecount += 1
					
					
				# check if any medication fields are empty (other than first)
				if key.startswith("med") and re.findall('[0-9]', key) != []:
				
					if chartdata[key].strip() == '':
					
						errormsg = "Some medication data was missing or multiple empty medication entries were submitted."
				
						return render_template("error.html", errormsg = errormsg)
		
		
			# should be 3 empties for first med option, if entered any partial data return error
			if firstmedvaluecount > 0 and firstmedvaluecount < 3:
			
				errormsg = "Some medication data was missing or multiple empty medication entries were submitted."
				
				return render_template("error.html", errormsg = errormsg)
		
				
		#----------------------------------------------------------------------------------------------------------
		
		# create new patient action (chartreview, taskid = 10)
		
		taskentry = patientAction(roarid = chartdata["submitChartDataID"],
									taskid = 10,
									taskdate = chartdata["dateCompleted"],
									mode = "JLV",
									outcome = "Completed chart review",
									timespent = chartdata["timeSpent"],
									note = re.sub("[<][a-zA-Z/]+[>]", "", chartdata["notes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(taskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (chart review) id
		newactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 10, patientAction.roarid == chartdata["submitChartDataID"]).order_by(patientAction.actiondate.desc()).first()
		
		# if participant deceased - update deceased and eligibility information in candidate patient table
		
		if chartdata["deceased"] == "Yes" and chartdata["eligible"] == "No":
		
			updatepatientdeceased = update(candidatePatient
									   ).where(candidatePatient.roarid == chartdata["submitChartDataID"]
									   ).values(deceased = 1,
									            deceaseddate = chartdata["dateCompleted"],
									            deceasedid = newactionid[0],
									            eligible = 0,
									            eligibledate = chartdata["dateCompleted"],
									            eligibleid = newactionid[0]
									            )
									            
			session.execute(updatepatientdeceased)
		
		# if participant not deceased
		
		if chartdata["deceased"] == "No":
		
			# extract station data
			stationentry = patientStation(roarid = chartdata["submitChartDataID"],
										sta3n = int(re.findall('[0-9]{3}', chartdata["vaStation"])[0]),
										activesta3n = 1,
										actionid = newactionid[0]
									  )
		
			session.add(stationentry)
		
		
			# extract provider data
		
			providerentry = patientProvider(roarid = chartdata["submitChartDataID"],
											provider = chartdata["vaPCP"].upper(),
											vaprovider = 1,
											vaprovidersta3n = int(re.findall('[0-9]{3}', chartdata["vaStation"])[0]),
											currentprovider = 1,
											actionid = newactionid[0]
										)
										
			session.add(providerentry)
		
		
			# extract phone data
		
			phoneentry1 = patientPhone(roarid = chartdata["submitChartDataID"],
									patientphone = chartdata["tel1"],
									activephone = 1,
									primaryphone = 1,
									actionid = newactionid[0]
								  )
		
			session.add(phoneentry1)
		
			# if secondary phone entered - add object
		
			if chartdata["tel2"] != '':
				phoneentry2 = patientPhone(roarid = chartdata["submitChartDataID"],
											patientphone = chartdata["tel2"],
											activephone = 1,
											primaryphone = 0,
											actionid = newactionid[0]
								          )
		
				session.add(phoneentry2)
		
		
			# extract LDL data
		
			maxldlentry = patientLDL(roarid = chartdata["submitChartDataID"],
									LDLtype = "maximum LDL",
									source = "JLV",
									value = chartdata["maxLDL"],
									unit = "mg/dL",
									valuedate = chartdata["maxLDLdate"],
									actionid = newactionid[0]
								  )
		
			session.add(maxldlentry)
		
			recentldlentry = patientLDL(roarid = chartdata["submitChartDataID"],
									LDLtype = "most recent LDL",
									source = "JLV",
									value = chartdata["recentLDL"],
									unit = "mg/dL",
									valuedate = chartdata["recentLDLdate"],
									actionid = newactionid[0]
								  )
									
			session.add(recentldlentry)
		
		
			# extract genetic data
		
			# get variant id information
		
			variantID = session.query(variantDim.variantid).filter(variantDim.cdot == chartdata["suspectVariant"]).first()
		
			# set molecular diagnosis variable
	
			geneticdataentry = patientGenetic(roarid = chartdata["submitChartDataID"],
											variantid = variantID[0], #TEMP CHANGE FOR CHART REVIEWS 12/7/2021 RETURNED / 0 if variantID == None else 
											molecdiagnosis = 0 if chartdata["fh"] == "No" else 1,
											molecdiagnosisid = newactionid[0])
											
			session.add(geneticdataentry)
		
		
			# extract medication data / use session.bulk_insert_mappings
		
			counter = 0
			meds = [chartdata["submitChartDataID"]]
			med_dicts = []
			key_values = ['roarid', 'medname', 'dose', 'unit', 'medstartdate', 'medstartsource', 'medstartdateid']
		
			for key in chartdata.keys():
		
				if key.startswith("med") and chartdata[key].strip() != '' and counter < 4: 
				
					if chartdata[key] == 'mg' and counter == 0: # this accounts for empty submission 
					
						continue
				
					meds.append(chartdata[key])
				
					counter += 1
			
				if counter == 4:
				
					meds.append("JLV")
					meds.append(newactionid[0])
				
					med_dicts.append(dict(zip(key_values, meds)))
				
					counter = 0
					meds = [chartdata["submitChartDataID"]]
					
			#session.bulk_insert_mappings for medications
		
			session.bulk_insert_mappings(patientMedication,
				med_dicts)
		
			# extract eligibility confirmation / eligible
			
			if chartdata["deceased"] == "No" and chartdata["eligible"] == "No":
		
				updatepatientnoteligible = ( update(candidatePatient
									   ).where(candidatePatient.roarid == chartdata["submitChartDataID"]
									   ).values(eligible = 0,
									            eligibledate = chartdata["dateCompleted"],
									            eligibleid = newactionid[0]
									            )
									   )
			
				session.execute(updatepatientnoteligible)


			if chartdata["deceased"] == "No" and chartdata["eligible"] == "Yes":
		
				updatepatienteligible = ( update(candidatePatient
									   ).where(candidatePatient.roarid == chartdata["submitChartDataID"]
									   ).values(eligible = 1,
									            eligibledate = chartdata["dateCompleted"],
									            eligibleid = newactionid[0]
									            )
										)
									        
				session.execute(updatepatienteligible)
		
			# commit values
		
			session.commit()

			# close any empty query transaction
			
			session.close()

			# return to patient detail

		# redirect to participant detail
		return redirect(url_for("participant_detail", roar_id=chartdata["submitChartDataID"]))
		
	# render chart review entry form	
	return render_template("chart_review.html", roarid=roar_id)


################################################################################################################################################

# commit recruitment letter data

@app.route("/record_recruitment_letter", methods=["POST"])
@login_required
def record_recruitment_letter():
	
	if request.method == "POST":
		roar_id = request.form["recletterinputID"]
		recletterdate = request.form["recletterdate"]
		
		# check if outcome date is in the future
		if datetime.strptime(recletterdate, '%Y-%m-%d') > datetime.today():
			
				errormsg = "Recruitment letter sent date is in the future."
				
				return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (recruitment letter, taskid = 11)
		
		rltaskentry = patientAction(roarid = roar_id,
									taskid = 11,
									taskdate = recletterdate,
									mode = "Mail",
									outcome = "Mailed recruitment letter",
									timespent = 2,
									note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["rlnotes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(rltaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# commit pedigree data

@app.route("/record_pedigree", methods=["POST"])
@login_required
def record_pedigree():
	
	if request.method == "POST":
		roar_id = request.form["pedigreeinputID"]
		pedigreedate = request.form["pedigreedate"]
		
		# check if outcome date is in the future
		if datetime.strptime(pedigreedate, '%Y-%m-%d') > datetime.today():
			
				errormsg = "Pedigree collection date is in the future."
				
				return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (pedigree, taskid = 25)
		
		pedigreetaskentry = patientAction(roarid = roar_id,
									taskid = 25,
									taskdate = pedigreedate,
									mode = request.form["collectMode"],
									outcome = "Pedigree collected",
									timespent = request.form["timeSpent"],
									note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["pednotes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(pedigreetaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# administer survey baseline reroute

@app.route("/baseline_survey", methods=["POST"])
@login_required
def baseline_survey():
	
	if request.method == "POST" and request.form["baselineSurveyID"] != None :
		roar_id = request.form["baselineSurveyID"]
		survey_type = "baseline"
		
		# redirect to participant detail
		return redirect(url_for("administer_survey", roar_id=roar_id, survey_type=survey_type))

################################################################################################################################################

# administer survey end of study survey reroute

@app.route("/eos_survey", methods=["POST"])
@login_required
def eos_survey():
	
	if request.method == "POST" and request.form["eosSurveyID"] != None:
		roar_id = request.form["eosSurveyID"]
		survey_type = "eos"
			
	# redirect to participant detail
	return redirect(url_for("administer_survey", roar_id=roar_id, survey_type=survey_type))

################################################################################################################################################

# administer survey 

@app.route("/administer_survey/<roar_id>/<survey_type>", methods=["GET", "POST"])
@login_required
def administer_survey(roar_id, survey_type):
	
	if request.method == "GET" and survey_type == "baseline":
		
		# set randStatus variable
		randStatus = ["BASELINE"]
		
		# get baseline survey questions
		baselineSurveyItems = session.query(surveyDim.item
								,questionDim.qshortname
								,questionDim.qfull
								,questionDim.itemresponseoptions
								).where(surveyDim.questionid == questionDim.questionid, surveyDim.surveyname == "baseline"
								).order_by(surveyDim.item).all()
			
		# redirect to participant detail
		return render_template("administer_survey.html", roar_id=roar_id, survey_type=survey_type, surveyItems=baselineSurveyItems, randStatus=randStatus)

	if request.method == "GET" and survey_type == "eos":
		
		# get randomization status of participant (delayed or immediate to obtain questions)
		randStatus = session.query(candidatePatient.randomizationstatus
								  ).where(candidatePatient.roarid == roar_id
								  ).first()
		
		# check if participant has been randomized
		if randStatus[0] == None:
			
			errormsg = "Participant has not been randomized yet or has no current randomization status."
				
			return render_template("error.html", errormsg = errormsg)	
		
		surveyName = "eos-immediate" if randStatus[0] == "IMMEDIATE" or randStatus[0] == "PILOT" else "eos-delayed"
			
		# get baseline survey questions
		eosSurveyItems = session.query(surveyDim.item
							,questionDim.qshortname
							,questionDim.qfull
							,questionDim.itemresponseoptions
							).where(surveyDim.questionid == questionDim.questionid, 
								surveyDim.surveyname == surveyName
							).order_by(surveyDim.item).all()
	
		# redirect to participant detail
		return render_template("administer_survey.html", roar_id=roar_id, survey_type=survey_type, surveyItems=eosSurveyItems, randStatus=randStatus)


################################################################################################################################################

# commit survey information

@app.route("/commit_survey_data", methods=["POST"])
@login_required
def commit_survey_data():
	
	if request.method == "POST":
		
		# collect elements here for committing to databases
		
		surveydata = request.form.to_dict()
		
		# create new patient action (record survey, baseline -> taskid = 15, follow-up -> = )
		roar_id = surveydata["submitSurveyDataID"]
		survey_type = surveydata["surveyType"]
		survey_date = surveydata["surveyDate"]
		time_spent = surveydata["timeSpent"]
		notes = surveydata["notes"]
		task_id = 13 if survey_type == "baseline" else 19
		
		surveytaskentry = patientAction(roarid = roar_id,
									taskid = task_id,
									taskdate = survey_date,
									mode = "Phone/Video",
									outcome = "Survey completed",
									timespent = time_spent,
									note = re.sub("[<][a-zA-Z/]+[>]", "", notes), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(surveytaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (chart review) id
		surveyactionid = session.query(patientAction.actionid).filter(patientAction.taskid == task_id,
									patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()

		# convert dictionary to pandas dataframe for cleanup
		surveyDataDF = pd.DataFrame.from_dict(surveydata, orient="index")
		
		# clean up uneeded and empty rows
		drop_idx = ["submitSurveyDataID", "surveyType", "surveyDate", "timeSpent", "notes"]
		surveyDataDF = surveyDataDF.drop(index=drop_idx)
		
		# add relevant column information for conversion back to dict for mapping
		surveyDataDF["roarid"] = [roar_id] * surveyDataDF.shape[0]
		surveyDataDF["actionid"] = [str(surveyactionid[0])] * surveyDataDF.shape[0]	
		
		# reset index
		surveyDataDF = surveyDataDF.reset_index()
		
		# rename columns
		surveyDataDF.columns = ["qshortname", "response", "roarid", "actionid"]	
		
		# clear out empty responses
		surveyDataDF = surveyDataDF[surveyDataDF.response != ''].reset_index(drop=True)
		
		# create list of dicts 
		survey_dicts = [dict(surveyDataDF.iloc[i,:]) for i in range(surveyDataDF.shape[0])]

		#session.bulk_insert_mappings for medications
		session.bulk_insert_mappings(patientSurvey, survey_dicts)
		
		# commit mappings
		session.commit()

	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=request.form["submitSurveyDataID"]))


################################################################################################################################################

# commit baseline specimen information

@app.route("/record_baseline_specimen", methods=["POST"])
@login_required
def record_baseline_specimen():
	
	if request.method == "POST":
		roar_id = request.form["baselinespecID"]
		blspecdate = request.form["baselinespecdate"]

		# check if outcome date is in the future
		if datetime.strptime(blspecdate, '%Y-%m-%d') > datetime.today():
			
			errormsg = "Baseline specimen collection receipt date is in the future."
				
			return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (baseline specimen collection, taskid = 14)
		
		blspectaskentry = patientAction(roarid = roar_id,
									taskid = 14,
									taskdate = blspecdate,
									mode = request.form["blspecmode"],
									outcome = "Baseline specimen received",
									timespent = 2,
									note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["blspecnotes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(blspectaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))

################################################################################################################################################

# commit baseline LDL information

@app.route("/record_baseline_LDL", methods=["POST"])
@login_required
def record_baseline_LDL():
	
	if request.method == "POST":
		roar_id = request.form["baselineLDLID"]
		blldldate = request.form["baselineLDLdate"]
		blldlmode = request.form["baselineLDLmode"]
		blldl = request.form["baselineLDL"]

		# check if data fields are empty
		if blldldate == '' or blldlmode == '' or blldl == '' :
			
			errormsg = "Required baseline LDL fields were not completed."
				
			return render_template("error.html", errormsg = errormsg)

		# check if outcome date is in the future
		if datetime.strptime(blldldate, '%Y-%m-%d') > datetime.today():
			
			errormsg = "Baseline LDL date is in the future."
				
			return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (record LDL, taskid = 15)
		
		blldltaskentry = patientAction(roarid = roar_id,
									taskid = 15,
									taskdate = blldldate,
									mode = blldlmode,
									outcome = "Baseline LDL recorded",
									timespent = 2,
									note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["blLDLnotes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(blldltaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (chart review) id
		blLDLactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 15, patientAction.outcome == "Baseline LDL Recorded", 
									patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()

		# extract LDL data
		
		blldlentry = patientLDL(roarid = roar_id,
								LDLtype = "baseline LDL",
								source = blldlmode,
								value = request.form["baselineLDL"],
								unit = "mg/dL",
								valuedate = request.form["baselineLDLdate"],
								actionid = blLDLactionid[0]
							  )
		
		# add to ldl table
		session.add(blldlentry)
		
		# commit to ldl table
		session.commit()
		
		# close session
		session.close()
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# commit end-of-study LDL information

@app.route("/record_eos_LDL", methods=["POST"])
@login_required
def record_eos_LDL():
	
	if request.method == "POST":
		roar_id = request.form["eosLDLID"]
		eosldldate = request.form["eosLDLdate"]
		eosldlmode = request.form["eosLDLmode"]
		eosldl = request.form["eosLDL"]

		# check if data fields are empty
		if eosldldate == '' or eosldlmode == '' or eosldl == '' :
			
			errormsg = "Required end-of-study  LDL fields were not completed."
				
			return render_template("error.html", errormsg = errormsg)

		# check if outcome date is in the future
		if datetime.strptime(eosldldate, '%Y-%m-%d') > datetime.today():
			
			errormsg = "End-of-study LDL date is in the future."
				
			return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (record LDL, taskid = 15)
		
		eosldltaskentry = patientAction(roarid = roar_id,
									taskid = 15,
									taskdate = eosldldate,
									mode = eosldlmode,
									outcome = "End-of-study LDL recorded",
									timespent = 2,
									note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["eosLDLnotes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(eosldltaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (chart review) id
		eosLDLactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 15, patientAction.outcome == "End-of-study LDL recorded", 
									patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()

		# extract LDL data
		
		eosldlentry = patientLDL(roarid = roar_id,
								LDLtype = "end-of-study LDL",
								source = eosldlmode,
								value = request.form["eosLDL"],
								unit = "mg/dL",
								valuedate = request.form["eosLDLdate"],
								actionid = eosLDLactionid[0]
							  )
		
		# add to ldl table
		session.add(eosldlentry)
		
		# commit to ldl table
		session.commit()
		
		# close session
		session.close()
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))



################################################################################################################################################

# randomization -

@app.route("/randomization", methods=["POST"])
@login_required
def randomization():
	
	if request.method == "POST" and request.form["randomizationID"] != None :
		roar_id = request.form["randomizationID"]
		
		# query required data for participant detail page and render
		participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    candidatePatient.dob,
								    candidatePatient.sexmale,
								    candidatePatient.race,
								    candidatePatient.ethnicity,
								    candidatePatient.deceased,
								    candidatePatient.deceaseddate,
								    candidatePatient.eligible,
								    candidatePatient.eligibledate,
								    candidatePatient.declined,
								    candidatePatient.declineddate,
								    candidatePatient.losttofup,
								    candidatePatient.losttofupdate,
								    candidatePatient.consented,
								    candidatePatient.consenteddate,
								    candidatePatient.randomizationstatus,
								    candidatePatient.randomizationdate,
								    candidatePatient.withdrawn,
								    candidatePatient.withdrawndate,
								    candidatePatient.corereleasedate,
								    candidatePatient.pilotparticipant,
								    patientAddress.street1,
								    patientAddress.street2,
								    patientAddress.street3,
								    patientAddress.city,
								    patientAddress.state,
								    patientAddress.zipcode
								).join(patientAddress, candidatePatient.roarid == patientAddress.roarid
								).filter(candidatePatient.roarid == roar_id, patientAddress.activeaddress == 1
								).first()

		
		# query for active VA
		participantVA = session.query(patientStation.sta3n,
								sta3nDim.sta3nname
								).join(sta3nDim, patientStation.sta3n == sta3nDim.sta3n
								).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1
								).first()
		
		# query for active providers
		participantproviders = session.query(patientProvider.provider,
									patientProvider.vaprovider
									).filter(patientProvider.roarid == roar_id, patientProvider.currentprovider == 1
									).all()
		
		# helper calculate age
		ptAge = calculatedAge(participant.dob)
	
		# close query transaction
		session.close()
		
		return render_template("randomization.html", 
							pt = participant, ptAge = ptAge, ptVA = participantVA, ptProv = participantproviders
							  )

################################################################################################################################################

# randomization -

@app.route("/randomize_participant", methods=["GET", "POST"])
@login_required
def randomize_participant():

	if request.method == "POST":
		
		# collect elements from form here and validate before randomizing
		
		randomizationdata = request.form.to_dict()
		
		# get id
		roar_id = randomizationdata["submitRandomizationID"]
		
		# validate participant meets criteria for randomization

		consented = session.query(candidatePatient.consented).filter(candidatePatient.roarid == roar_id).first()
		baselineSurvey = session.query(patientAction.taskid).filter(patientAction.roarid == roar_id, patientAction.taskid == 13).first()
		baselineSpecimen = session.query(patientAction.taskid).filter(patientAction.roarid == roar_id, patientAction.taskid == 14).first()
		baselineLDL = session.query(patientAction.taskid).filter(patientAction.roarid == roar_id, patientAction.taskid == 15).first()
		alreadyrandomized = session.query(candidatePatient.randomizationstatus).filter(candidatePatient.roarid == roar_id).first()
		
		# render specific error if any queries return None
		
		if consented[0] is None: # index, this query returns a tuple

			errormsg = "Participant has not been consented."
				
			return render_template("error.html", errormsg = errormsg)
			
		if baselineSurvey is None:
			
			errormsg = "Baseline survey data has not been collected."
				
			return render_template("error.html", errormsg = errormsg)
				
		if baselineSpecimen is None:

			errormsg = "Baseline genetic specimen has not been recieved."
				
			return render_template("error.html", errormsg = errormsg)
							
		if baselineLDL is None:
			
			errormsg = "A valid baseline LDL has not been recorded."
				
			return render_template("error.html", errormsg = errormsg)

		if alreadyrandomized[0] is not None:
			
			errormsg = "Participant has already been randomized to the " + alreadyrandomized[0] + " arm."
				
			return render_template("error.html", errormsg = errormsg)

		# check if randomization date is in the future
		if datetime.strptime(randomizationdata["dateRandomized"], '%Y-%m-%d') > datetime.today():
			
				errormsg = "Specified randomization date is in the future."
				
				return render_template("error.html", errormsg = errormsg)	
			
		# if no errors reference randomized list and randomization table (offset 1) - # randomized + 1
		
		# read from roar.randomization source table
		randTable = session.execute('SELECT {ENTER COLUMN WITH RANDOMIZATION STATUS} FROM {ENTER RANDOMIZATION TABLE}')
		
		# convert to dict
		randTable = randTable.mappings().all()
		
		# get total count of rows in patientRandomization table
		numRandomized = session.query(func.count(patientRandomization.roarid)).all()[0][0]
		
		# get total # randomized - originally set up with offset +1 -> numRandomized + 2 to get slot for current participant 
		randStatus = "IMMEDIATE" if [slot for slot in randTable if slot["serialno"] == numRandomized + 2][0]["arm"] == 1.0 else "DELAYED"

		# create patient action entry
		randomizationtaskentry = patientAction(roarid = roar_id,
									taskid = 16,
									taskdate = randomizationdata["dateRandomized"],
									mode = "Staff ID: " + str(current_user.userid),
									outcome = "Participant randomized",
									timespent = 2,
									note = "Participant " + roar_id + " randomized to the " + randStatus + " group.",
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(randomizationtaskentry )
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (chart review) id
		randomizationactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 16,
									patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()
	
		# commit updates -
		
		# commit data to randomization table
		randomizationentry = patientRandomization(roarid = roar_id,
								queueorder = numRandomized + 1,
								randomizationid = randomizationactionid[0]
							  )
		
		# add to patientRandomization table
		session.add(randomizationentry)
		
		
		updatepatientrandomization = ( update(candidatePatient
									).where(candidatePatient.roarid == roar_id
									).values(randomizationstatus = randStatus,
									randomizationdate = randomizationdata["dateRandomized"],
									randomizationid = randomizationactionid[0]
									)
								)
									        
		session.execute(updatepatientrandomization)
	
		# commit to patientRandomization / candidatePatient tables
		session.commit()

		# ensure session closed - return open session to pool
		session.close()
	
		return render_template("randomization_result.html", roar_id = roar_id, randStatus = randStatus)
	

################################################################################################################################################

# commit delayed results letter data

@app.route("/record_delresletter", methods=["POST"])
@login_required
def record_delresletter():
	
	if request.method == "POST":
		roar_id = request.form["delresletterinputID"]
		delresletterdate = request.form["delresletterdate"]
		
		# check if outcome date is in the future
		if datetime.strptime(delresletterdate, '%Y-%m-%d') > datetime.today():
			
				errormsg = "Delayed results letter date is in the future."
				
				return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (delayed results letter, taskid = 27)
		
		delreslettertaskentry = patientAction(roarid = roar_id,
									taskid = 27,
									taskdate = delresletterdate,
									mode = "Staff ID: " + str(current_user.userid),
									outcome = "Delayed results letter sent.",
									timespent = request.form["timeSpent"],
									note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["delresletternotes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(delreslettertaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))

################################################################################################################################################

# genetic report -

@app.route("/genetic_report", methods=["POST"])
@login_required
def genetic_report():
	
	if request.method == "POST" and request.form["geneticReportID"] != None:
		roar_id = request.form["geneticReportID"]
		
		participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    candidatePatient.dob,
								    candidatePatient.sexmale,
								    candidatePatient.race,
								    candidatePatient.ethnicity,
								    candidatePatient.deceased,
								    candidatePatient.deceaseddate,
								    candidatePatient.eligible,
								    candidatePatient.eligibledate,
								    candidatePatient.declined,
								    candidatePatient.declineddate,
								    candidatePatient.losttofup,
								    candidatePatient.losttofupdate,
								    candidatePatient.consented,
								    candidatePatient.consenteddate,
								    candidatePatient.randomizationstatus,
								    candidatePatient.randomizationdate,
								    candidatePatient.withdrawn,
								    candidatePatient.withdrawndate,
								    candidatePatient.corereleasedate,
								    candidatePatient.pilotparticipant,
								).filter(candidatePatient.roarid == roar_id
								).first()

		# query for genetic information
		participantgenetic = session.query(patientGenetic.molecdiagnosis,
										   patientGenetic.confirmtesting,
										   patientGenetic.confirmresult,
										   patientGenetic.confirmsource,
										   patientGenetic.confirmtestingdate,
										   variantDim.cdot,
										   variantDim.rsID,
										   variantDim.axID
										  ).join(variantDim, patientGenetic.variantid == variantDim.variantid
										  ).filter(patientGenetic.roarid == roar_id
										  ).first()
										  
		# Variant data
		susV = session.query(variantDim).order_by(variantDim.cdot).all()
		
		# helper calculate age
		ptAge = calculatedAge(participant.dob)
		
		# redirect to participant detail
		return render_template("report.html", pt=participant, ptAge=ptAge, ptGen=participantgenetic, susV=susV)


################################################################################################################################################

# commit genetic report data

@app.route("/commit_genetic_report", methods=["POST"])
@login_required
def commit_genetic_report():
	
	if request.method == "POST":

		# collect genetic report elements here for committing to databases
		reportdata = request.form.to_dict()
		
		# get roar_id
		roar_id = reportdata["submitRerportDataID"]
		
		# loop through data for validation
		for key in reportdata.keys():
		
			# check for empties
			if key != "notes" and reportdata[key].strip() == '':

				errormsg = "Some genetic report data is missing."
	
				return render_template("error.html", errormsg = errormsg)	
				
			# check if outcome date is in the future
			if "Date" in key and datetime.strptime(reportdata[key], '%Y-%m-%d') > datetime.today():
			
				errormsg = "Some genetic report dates are in the future."
				
				return render_template("error.html", errormsg = errormsg)
		
		# check if entry exists and if so generate error
		if session.query(patientAction.actionid).filter(patientAction.taskid == 17, patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first() is not None:
			
			errormsg = "Genetic report data has already been entered."
				
			return render_template("error.html", errormsg = errormsg)
		
		# create new patient action (genetic report, taskid = 17)
		
		geneticreporttaskentry = patientAction(roarid = roar_id,
									taskid = 17,
									taskdate = reportdata["sampleReportDate"],
									mode = "Genetic report",
									outcome = "Genetic report, received and recorded",
									timespent = reportdata["timeSpent"],
									note = "Genetic report received. " + \
									"Research result confirmed: " + reportdata["confirmation"] + ".\n" \
									"Confirmed variant: " + reportdata["confirmVariant"] +  ".\n" \
									"Variant classification status (as of report): " + reportdata["variantStatus"] +  ".\n" \
									"Specimen type: " + reportdata["sampleType"] +  ".\n" \
									"Sample collection date: " + reportdata["sampleCollectionDate"] + ".\n" \
									"Sample report date: " + reportdata["sampleReportDate"] + ".\n" \
									"Report number: " + reportdata["reportID"] + ".\n" \
									"Notes: " + re.sub("[<][a-zA-Z/]+[>]", "", reportdata["notes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(geneticreporttaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (genetic report) id
		geneticreportactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 17,
									patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()
		
		# get suspected variant id
		if "c." in reportdata["confirmVariant"]:
			variantID = session.query(variantDim.variantid).filter(variantDim.cdot == reportdata["confirmVariant"]).first()
		
		else:
			variantID = None
	
		# commit updates -
			
		updatepatientgenetic = ( update(patientGenetic
							).where(patientGenetic.roarid == roar_id
							).values(confirmtesting = 1,
							confirmtestingdate = reportdata["sampleReportDate"],
							sampletype = reportdata["sampleType"],
							confirmresult = 1 if reportdata["confirmation"] == "Yes" else 0,
							resultclassification = "DNC" if variantID is None else variantID[0],
							confirmsource = "INVITAE",
							confirmtestingid = geneticreportactionid[0] 
							)
						)
									        
		session.execute(updatepatientgenetic)
	
		# commit to patientGenetic table
		session.commit()

		# ensure session closed - return open session to pool
		session.close() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# intervention delivery -

@app.route("/intervention", methods=["POST"])
@login_required
def intervention():
	
	if request.method == "POST" and request.form["interventionID"] != None :
		roar_id = request.form["interventionID"]
		
		# query required data for participant detail page and render
		participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    candidatePatient.dob,
								    candidatePatient.sexmale,
								    candidatePatient.race,
								    candidatePatient.ethnicity,
								    candidatePatient.deceased,
								    candidatePatient.deceaseddate,
								    candidatePatient.eligible,
								    candidatePatient.eligibledate,
								    candidatePatient.declined,
								    candidatePatient.declineddate,
								    candidatePatient.consented,
								    candidatePatient.consenteddate,
								    candidatePatient.losttofup,
								    candidatePatient.losttofupdate,
								    candidatePatient.randomizationstatus,
								    candidatePatient.randomizationdate,
								    candidatePatient.withdrawn,
								    candidatePatient.withdrawndate,
								    candidatePatient.corereleasedate,
								    candidatePatient.pilotparticipant,
								).filter(candidatePatient.roarid == roar_id
								).first()
		
		# query for active VA
		participantVA = session.query(patientStation.sta3n,
								sta3nDim.sta3nname
								).join(sta3nDim, patientStation.sta3n == sta3nDim.sta3n
								).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1
								).first()
		
		# query for active providers
		participantproviders = session.query(patientProvider.provider,
									patientProvider.vaprovider
									).filter(patientProvider.roarid == roar_id, patientProvider.currentprovider == 1
									).all()
											 
		# query for LDL information
		participantLDL = session.query(patientLDL.LDLtype,
								patientLDL.value,
								patientLDL.unit,
								patientLDL.valuedate
								).filter(patientLDL.roarid == roar_id
								).all()
		
		# query for genetic information
		participantgenetic = session.query(patientGenetic.molecdiagnosis,
										   patientGenetic.confirmtesting,
										   patientGenetic.confirmtestingdate,
										   patientGenetic.confirmresult,
										   patientGenetic.confirmsource,
										   variantDim.cdot,
										   variantDim.rsID,
										   variantDim.axID
										  ).join(variantDim, patientGenetic.variantid == variantDim.variantid
										  ).filter(patientGenetic.roarid == roar_id
										  ).first()
										  
		
		# helper calculate age
		ptAge = calculatedAge(participant.dob)
		
		# redirect to participant detail
		return render_template("intervention.html", pt=participant, ptAge=ptAge, ptVA=participantVA, ptGen=participantgenetic,
						ptProv=participantproviders, ptLDL=participantLDL)

################################################################################################################################################

# commit intervention delivery data

@app.route("/commit_intervention", methods=["POST"])
@login_required
def commit_intervention():
	
	if request.method == "POST":

		# collect genetic report elements here for committing to databases
		interventiondata = request.form.to_dict()
		
		# check data validity
		roar_id = interventiondata["submitInterventionID"]
		
		# loop through data for validation
		for key in interventiondata.keys():
		
			# check for empties
			if key != "notes" and interventiondata[key].strip() == '':

				errormsg = "Some intervention data is missing."
	
				return render_template("error.html", errormsg = errormsg)	
				
			# check if outcome date is in the future
			if "Date" in key and datetime.strptime(interventiondata[key], '%Y-%m-%d') > datetime.today():
			
				errormsg = "Some intervention dates are in the future."
				
				return render_template("error.html", errormsg = errormsg)
		
		# check if entry exists and if so generate error
		if session.query(patientAction.actionid).filter(patientAction.taskid == 18, patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first() is not None:
			
			errormsg = "Intervention delivery data has already been entered."
				
			return render_template("error.html", errormsg = errormsg)
		
		# create new patient action (intervention, taskid = 18)
		
		interventiontaskentry = patientAction(roarid = roar_id,
									taskid = 18,
									taskdate = interventiondata["interventionDate"],
									mode = interventiondata["interventionType"],
									outcome = "Return of results delivery completed",
									timespent = interventiondata["timeSpent"],
									note = re.sub("[<][a-zA-Z/]+[>]", "", interventiondata["notes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(interventiontaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (genetic report) id
		interventionactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 18,
									patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()
		
		# commit updates -
		
		patientinterventiondelivery = update(patientGenetic
									  ).where(patientGenetic.roarid == roar_id
									  ).values(interventiondelivered = 1,
											   interventiondeliveredid = interventionactionid[0]
											   )
									    
		session.execute(patientinterventiondelivery)
	
		# commit to patientGenetic table
		session.commit()

		# ensure session closed - return open session to pool
		session.close() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# intervention documentation -

@app.route("/intervention_documentation", methods=["POST"])
@login_required
def intervention_documentation():
	
	if request.method == "POST" and request.form["interventionID"] != None :
		roar_id = request.form["interventionID"]
		
		# query required data for participant detail page and render
		participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    candidatePatient.dob,
								    candidatePatient.sexmale,
								    candidatePatient.race,
								    candidatePatient.ethnicity,
								    candidatePatient.deceased,
								    candidatePatient.deceaseddate,
								    candidatePatient.eligible,
								    candidatePatient.eligibledate,
								    candidatePatient.declined,
								    candidatePatient.declineddate,
								    candidatePatient.consented,
								    candidatePatient.consenteddate,
								    candidatePatient.losttofup,
								    candidatePatient.losttofupdate,
								    candidatePatient.randomizationstatus,
								    candidatePatient.randomizationdate,
								    candidatePatient.withdrawn,
								    candidatePatient.withdrawndate,
								    candidatePatient.corereleasedate,
								    candidatePatient.pilotparticipant,
								).filter(candidatePatient.roarid == roar_id
								).first()
		
		# query for active VA
		participantVA = session.query(patientStation.sta3n,
								sta3nDim.sta3nname
								).join(sta3nDim, patientStation.sta3n == sta3nDim.sta3n
								).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1
								).first()
		
		# query for active providers
		participantproviders = session.query(patientProvider.provider,
								patientProvider.vaprovider
								).filter(patientProvider.roarid == roar_id, patientProvider.currentprovider == 1
								).all()
											 
		# query for LDL information
		participantLDL = session.query(patientLDL.LDLtype,
								patientLDL.value,
								patientLDL.unit,
								patientLDL.valuedate
								).filter(patientLDL.roarid == roar_id
								).all()
		
		# query for genetic information
		participantgenetic = session.query(patientGenetic.molecdiagnosis,
								patientGenetic.confirmtesting,
								patientGenetic.confirmtestingdate,
								patientGenetic.confirmresult,
								patientGenetic.confirmsource,
								variantDim.cdot,
								variantDim.rsID,
								variantDim.axID
								).join(variantDim, patientGenetic.variantid == variantDim.variantid
								).filter(patientGenetic.roarid == roar_id
								).first()
										  
		
		# helper calculate age
		ptAge = calculatedAge(participant.dob)
		
		# redirect to participant detail
		return render_template("intervention_documentation.html", pt=participant, ptAge=ptAge, ptVA=participantVA, ptGen=participantgenetic,
													ptProv=participantproviders, ptLDL=participantLDL)

################################################################################################################################################

# commit intervention documentation data

@app.route("/commit_intervention_documentation", methods=["POST"])
@login_required
def commit_intervention_documentation():
	
	if request.method == "POST":

		# collect genetic report elements here for committing to databases
		documentationdata = request.form.to_dict()
		
		# check data validity
		roar_id = documentationdata["submitDocumentationID"]
		
		# loop through data for validation
		for key in documentationdata.keys():
		
			# check for empties
			if key != "notes" and documentationdata[key].strip() == '':

				errormsg = "Some intervention data is missing."
	
				return render_template("error.html", errormsg = errormsg)	
				
			# check if outcome date is in the future
			if "Date" in key and datetime.strptime(documentationdata[key], '%Y-%m-%d') > datetime.today():
			
				errormsg = "Some intervention dates are in the future."
				
				return render_template("error.html", errormsg = errormsg)
		
		# check if entry exists and if so generate error
		if session.query(patientAction.actionid).filter(patientAction.taskid == 26, patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first() is not None:
			
			errormsg = "Intervention documentation data has already been entered."
				
			return render_template("error.html", errormsg = errormsg)
		
		# create new patient action (intervention, taskid = 26)
		
		documentationtaskentry = patientAction(roarid = roar_id,
									taskid = 26,
									taskdate = documentationdata["documentationDate"],
									mode = "Staff ID: " + str(current_user.userid),
									outcome = "Return of results documentation completed",
									timespent = documentationdata["timeSpent"],
									note = re.sub("[<][a-zA-Z/]+[>]", "", documentationdata["notes"]), #clear any html/script tags for cross scripting (not likely)
									staffid = current_user.userid,
									actiondate = datetime.now()
								 )	
		
		# add task entry object						 
		session.add(documentationtaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (genetic report) id
		documentationactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 26,
									patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()
		
		# commit updates -
			
		patientinterventiondocumentation = patientIntervention(roarid = roar_id,
										    patientlettersent = 1 if documentationdata["patientLetter"] == "Yes" else 0,
									            familylettersent = 1 if documentationdata["familyLetter"] == "Yes" else 0,
									            familyletters = documentationdata["numFamLetter"],
									            providerlettersent = 1 if documentationdata["providerLetter"] == "Yes" else 0,
									            vaproviderletters = documentationdata["numVAprovLetters"],
									            nonvaproviderletters = documentationdata["numNonVAprovLetters"],
									            cprsnoteupload = 1 if documentationdata["cprsNote"] == "Yes" else 0,
										    interventionid = documentationactionid[0] 
									            )
									        
		session.add(patientinterventiondocumentation)
	
		# commit to patientGenetic table
		session.commit()

		# ensure session closed - return open session to pool
		session.close() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# commit eos specimen information

@app.route("/record_eos_specimen", methods=["POST"])
@login_required
def record_eos_specimen():
	
	if request.method == "POST":
		roar_id = request.form["eosspecID"]
		eosspecdate = request.form["eosspecdate"]
		
		# check if outcome date is in the future
		if datetime.strptime(eosspecdate, '%Y-%m-%d') > datetime.today():
			
			errormsg = "End-of-study specimen collection receipt date is in the future."
				
			return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (baseline specimen collection, taskid = 14)
		
		eosspectaskentry = patientAction(roarid = roar_id,
								taskid = 14,
								taskdate = eosspecdate,
								mode = request.form["eosspecmode"],
								outcome = "End-of-study specimen received",
								timespent = 2,
								note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["eosspecnotes"]), #clear any html/script tags for cross scripting (not likely)
								staffid = current_user.userid,
								actiondate = datetime.now()
								)	
		
		# add task entry object						 
		session.add(eosspectaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))
	

################################################################################################################################################

# commit incentive information

@app.route("/record_incentive", methods=["POST"])
@login_required
def record_incentive():
	
	if request.method == "POST":
		roar_id = request.form["incentiveID"]
		incentivedate = request.form["incentiveDate"]
		
		# check if outcome date is in the future
		if datetime.strptime(incentivedate, '%Y-%m-%d') > datetime.today():
			
			errormsg = "Incentive date is in the future."
				
			return render_template("error.html", errormsg = errormsg)	
		
		# create new patient action (baseline specimen collection, taskid = 14)
		
		incentivetaskentry = patientAction(roarid = roar_id,
								taskid = 20,
								taskdate = date.today(),
								mode = "Staff ID: " + str(current_user.userid),
								outcome = "Incentive paid" if request.form["incentiveMode"] else "Incentive payment not made",
								timespent = 2,
								note = re.sub("[<][a-zA-Z/]+[>]", "", request.form["incentiveNotes"]), #clear any html/script tags for cross scripting (not likely)
								staffid = current_user.userid,
								actiondate = datetime.now()
								)	
		
		# add task entry object						 
		session.add(incentivetaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
	# redirect to participant detail
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# record contact - from workflow template participant detail

@app.route("/record_consent", methods=["POST"])
@login_required
def record_consent():
	
	if request.method == "POST":
		roar_id = request.form["consentDateID"]
		
	return redirect(url_for("contact_form", roar_id=roar_id))
	
################################################################################################################################################

# record contact - main button

@app.route("/record_contact", methods=["POST"])
@login_required
def record_contact():
	
	if request.method == "POST":
		roar_id = request.form["recordContactID"]
		
	return redirect(url_for("contact_form", roar_id=roar_id))

################################################################################################################################################

# record contact - from workflow or main button

@app.route("/contact_form/<roar_id>", methods=["GET", "POST"])
@login_required
def contact_form(roar_id):
		
	# query required data for participant detail page and render
	participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    candidatePatient.dob,
								    candidatePatient.sexmale,
								    candidatePatient.race,
								    candidatePatient.ethnicity,
								    candidatePatient.deceased,
								    candidatePatient.deceaseddate,
								    candidatePatient.eligible,
								    candidatePatient.eligibledate,
								    candidatePatient.declined,
								    candidatePatient.declineddate,
								    candidatePatient.losttofup,
								    candidatePatient.losttofupdate,
								    candidatePatient.consented,
								    candidatePatient.consenteddate,
								    candidatePatient.randomizationstatus,
								    candidatePatient.randomizationdate,
								    candidatePatient.withdrawn,
								    candidatePatient.withdrawndate,
								    candidatePatient.corereleasedate,
								    candidatePatient.pilotparticipant,
								    patientAddress.street1,
								    patientAddress.street2,
								    patientAddress.street3,
								    patientAddress.city,
								    patientAddress.state,
								    patientAddress.zipcode
								).join(patientAddress, candidatePatient.roarid == patientAddress.roarid
								).filter(candidatePatient.roarid == roar_id, patientAddress.activeaddress == 1
								).first()
		
	# query for list of active phone numbers
	participantphone = session.query(patientPhone.patientphone,
								patientPhone.primaryphone
								).filter(patientPhone.roarid == roar_id, patientPhone.activephone == 1
								).order_by(patientPhone.primaryphone.desc()
								).all()
		
	# query for list of active emails
	participantemail = session.query(patientEmail.patientemail
								).filter(patientEmail.roarid == roar_id, patientEmail.activeemail == 1
								).all()
		
	# query for active VA
	participantVA = session.query(patientStation.sta3n,
								sta3nDim.sta3nname
								).join(sta3nDim, patientStation.sta3n == sta3nDim.sta3n
								).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1
								).first()
		
	# query for active providers
	participantproviders = session.query(patientProvider.provider,
								patientProvider.vaprovider
								).filter(patientProvider.roarid == roar_id, patientProvider.currentprovider == 1
								).all()
		
	# helper calculate age
	ptAge = calculatedAge(participant.dob)
	
	# close query transaction
	session.close()
		
	return render_template("contact_form.html", 
						pt = participant, ptAge = ptAge, ptPhone = participantphone, \
						ptEmail = participantemail, ptVA = participantVA, ptProv = participantproviders
						)

################################################################################################################################################

# commit contact or note information to database

@app.route("/commit_contact_data", methods=["POST"])
@login_required
def commit_contact_data():
	
	if request.method == "POST":
		
		# collect elements here for committing to databases
		
		contactdata = request.form.to_dict()
		
		# check data validity
		
		# check for empty required fields
		if contactdata["contactType"] == "" or contactdata["contactReason"] == "" or contactdata["contactOutcome"] == "" or contactdata["contactDate"] == "" \
			or contactdata["timeSpentContact"] == "":
			
				errormsg = "Required fields were not completed."
				
				return render_template("error.html", errormsg = errormsg)

		# check if outcome date is in the future
		if datetime.strptime(contactdata["contactDate"], '%Y-%m-%d') > datetime.today():
			
				errormsg = "Entered action date is in the future."
				
				return render_template("error.html", errormsg = errormsg)				
		
		# check consent data, if conflicting return error
		if contactdata["contactReason"] == "Consent call" and not (contactdata["contactType"] == "Phone call" or contactdata["contactType"] == "Video call"):
			
				errormsg = "Some conflicting consent information was entered, check action type and reason."
				
				return render_template("error.html", errormsg = errormsg)

		# check consent date, if not entered return error
		if contactdata["contactReason"] == "Consent call" and contactdata["consentOutcome"] != "Pending" and \
			(contactdata["consentDate"] == "" or datetime.strptime(contactdata["consentDate"], '%Y-%m-%d') > datetime.today()):
			
				errormsg = "No consent date was entered or consent date entered was in the future."
				
				return render_template("error.html", errormsg = errormsg)

		
		# define roar_id for committing and redirecting
		roar_id = contactdata["submitContactDataID"]
		
		# create task entry
		if contactdata["contactReason"] == "Consent call":
		
			consenttaskentry = patientAction(roarid = roar_id,
									taskid = 12,
									taskdate = contactdata["consentDate"] if contactdata["consentOutcome"] != "Pending" else contactdata["contactDate"],
									mode = contactdata["contactType"],
									outcome = contactdata["contactOutcome"] + ' / ' + contactdata["consentOutcome"],
									timespent = contactdata["timeSpentContact"],
									note = re.sub("[<][a-zA-Z/]+[>]", "", contactdata["contactNotes"]) if contactdata["contactTime"] == "" \
											else re.sub("[<][a-zA-Z/]+[>]", "", contactdata["contactNotes"]) + ' Contact completed: ' + \
											contactdata["contactDate"] + ' | ' + contactdata["contactTime"] + ' ET.',
									staffid = current_user.userid,
									actiondate = datetime.now()
									)	
		
			# add task entry object						 
			session.add(consenttaskentry)
		
			# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
			session.commit()
			
			
			# get taskid and update candidate patient consent/decline
			
			# query to retrieve patient action (chart review) id
			consentactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 12, 
								patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()
			
			if contactdata["consentOutcome"] == "Declined":
			
				# update consent / decline
				updatepatientdeclined = update(candidatePatient
									   ).where(candidatePatient.roarid == roar_id
									   ).values(declined = 1,
									            declineddate = contactdata["consentDate"],
									            declinedid = consentactionid[0],
									            consented = 0,
									            )
									            
				session.execute(updatepatientdeclined)
			
			if contactdata["consentOutcome"] == "Consented":
			
				# update consent / decline
				updatepatientconsented = update(candidatePatient
									   ).where(candidatePatient.roarid == roar_id
									   ).values(consented = 1,
									            consenteddate = contactdata["consentDate"],
									            consentedid = consentactionid[0], 
									            )
									            
				session.execute(updatepatientconsented)

				# update consented for core comms table - core uses this table to grant us access to participant data (CB 12/15/2021):
				
				# check if already in comms table - foe use by MVP Core
				commscheck = session.execute("SELECT roarid \
							      FROM {ENTER COMMUNICATIONS TABLE} \
							      WHERE roarid = :roar_id",
							      {"roar_id": roar_id})
				
				commscheck_res = commscheck.first()
				
				# if query returns none - insert information into comms table
				if commscheck_res is None:
					
					# get mvpcoreid 
					coreid = session.query(candidatePatient.mvpcoreid
								).filter(candidatePatient.roarid == roar_id
								).first()
								
					# update core comms	
					session.execute("INSERT INTO roar.ConsentedForCoreCommsTemp ( \
							roarid, MVPCore_ID, DateConsentedInRoar) \
							VALUES (:roar_id, :core_id, :consentDate)",
							{"roar_id": roar_id, "core_id": coreid[0], 'consentDate': contactdata["consentDate"]})

		# add additional commit information for contact and other factors
		if contactdata["contactReason"] == "Participant contact" or contactdata["contactReason"] == "Other":
			
			contacttaskentry = patientAction(roarid = roar_id,
									taskid = 23 if contactdata["contactOutcome"] == "VA Form 10-5345 received (release of information)" else 21,
									taskdate = contactdata["contactDate"],
									mode = contactdata["contactType"],
									outcome = contactdata["contactOutcome"],
									timespent = contactdata["timeSpentContact"],
									note = re.sub("[<][a-zA-Z/]+[>]", "", contactdata["contactNotes"]) if contactdata["contactTime"] == "" \
											else re.sub("[<][a-zA-Z/]+[>]", "", contactdata["contactNotes"]) + ' Contact completed: ' + \
											contactdata["contactDate"] + ' | ' + contactdata["contactTime"] + ' ET.',
									staffid = current_user.userid,
									actiondate = datetime.now()
									)	
		
			# add task entry object						 
			session.add(contacttaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit()
		
		session.close()
		
	return redirect(url_for("participant_detail", roar_id=roar_id))


################################################################################################################################################

# update participant contact or provider information

@app.route("/update_contact", methods=["POST"])
@login_required
def update_contact():
	
	if request.method == "POST":
		roar_id = request.form["updateContactID"]
		
		# query required data for update contact page and render
		participant = session.query(candidatePatient.roarid,
								    candidatePatient.mvpcoreid,
								    candidatePatient.ssn,
								    candidatePatient.firstname,
								    candidatePatient.lastname,
								    patientAddress.street1,
								    patientAddress.street2,
								    patientAddress.street3,
								    patientAddress.city,
								    patientAddress.state,
								    patientAddress.zipcode,
								    candidatePatient.deceased,
								    candidatePatient.deceaseddate,
								    candidatePatient.eligible,
								    candidatePatient.eligibledate,
								    candidatePatient.declined,
								    candidatePatient.declineddate,
								    candidatePatient.losttofup,
								    candidatePatient.losttofupdate,
								    candidatePatient.consented,
								    candidatePatient.consenteddate,
								    candidatePatient.randomizationstatus,
								    candidatePatient.randomizationdate,
								    candidatePatient.withdrawn,
								    candidatePatient.withdrawndate
								).join(patientAddress, candidatePatient.roarid == patientAddress.roarid
								).filter(candidatePatient.roarid == roar_id, patientAddress.activeaddress == 1
								).first()
		
		# query for list of active phone numbers
		participantphone = session.query(patientPhone.patientphone,
									patientPhone.primaryphone
								).filter(patientPhone.roarid == roar_id, patientPhone.activephone == 1
								).order_by(patientPhone.primaryphone.desc()
								).all()
		
		# query for list of active emails
		participantemail = session.query(patientEmail.patientemail
								).filter(patientEmail.roarid == roar_id, patientEmail.activeemail == 1
								).all()
		
		# query for active VA
		participantVA = session.query(patientStation.sta3n,
								sta3nDim.sta3nname
								).join(sta3nDim, patientStation.sta3n == sta3nDim.sta3n
								).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1
								).first()
		
		# query for active providers
		participantproviders = session.query(patientProvider.provider,
								patientProvider.vaprovider
								).filter(patientProvider.roarid == roar_id, patientProvider.currentprovider == 1
								).all()
		
		# VA Station Data - if need to change
		vaSta3ns = session.query(sta3nDim.sta3nname).order_by(sta3nDim.location).all()
		
		# states - pull from csv file - easier implementation of datalist
		states = pd.read_csv("app/static/data/states.csv")["abbr"]

		# close query transaction
		session.close()
		
	return render_template("update_contact.html", pt = participant, ptPhone = participantphone, ptEmail = participantemail,
							ptVA = participantVA, ptProv = participantproviders, vaSta3ns = vaSta3ns, states = states)


################################################################################################################################################

# get data from update contact or dem information form and commit to study database

@app.route("/commit_update_contact", methods=["POST"])
@login_required
def commit_update_contact():
	
	if request.method == "POST":
		
		# collect elements here for committing to databases
		
		updatedata = request.form.to_dict()
		
		# check data validity
		
		# check update data, if all fields empty return error
		if updatedata["vaStation"].strip() == "" and updatedata["street1"].strip() == "" and updatedata["street2"].strip() == "" \
			and updatedata["street2"].strip() == "" and updatedata["street3"].strip() == "" and updatedata["city"].strip() == "" \
			and updatedata["state"].strip() == "" and updatedata["zipcode"].strip() == "" and updatedata["teltype"].strip() == "" \
			and updatedata["tel"].strip() == "" and updatedata["removetel"].strip() == "" and updatedata["emailtype"].strip() == "" \
			and updatedata["email"].strip() == "" and updatedata["removeemail"].strip() == "" and updatedata["providertype"].strip() == "" \
			and updatedata["provider"].strip() == "" and updatedata["removeprovider"].strip() == "" and updatedata["statustype"].strip() == "" \
			and updatedata["statusdate"].strip() == "":
			
				errormsg = "No valid update data entered."
				
				return render_template("error.html", errormsg = errormsg)		
		
		# iterate through keys and validate individual elements
		for key in updatedata.keys():
		
			# check format of va station
			if (key == "vaStation" and not updatedata[key].strip() == "") and not re.findall('[(][0-9]{3}[)][a-zA-Z,() ]+', updatedata[key]):
				
				errormsg = "VA Station format is incorrect: (3 Digit Station Number) Station Name"
				
				return render_template("error.html", errormsg = errormsg)

			# check format of address (state)
			if (key == "state" and not updatedata[key].strip() == "") and not re.findall('[A-Z]{2}', updatedata[key]):
				
				errormsg = "State format incorrect: two letter abbreviation required (e.g. MA)"
				
				return render_template("error.html", errormsg = errormsg)

			# check format of address (zipcode)
			if (key == "zipcode" and not updatedata[key].strip() == "") and not re.findall('[0-9]{5}', updatedata[key]):
				
				errormsg = "Zip code format incorrect: five number format required (e.g. 02130)"
				
				return render_template("error.html", errormsg = errormsg)
			
			# check telephone format
			if (key == "tel" and not updatedata[key].strip() == "") and not re.findall('[0-9]{3}[-][0-9]{3}[-][0-9]{4}', updatedata[key]):
				
				errormsg = "Telephone number format was not correct: ###-###-####"
				
				return render_template("error.html", errormsg = errormsg)

			# check email format
			if (key == "email" and not updatedata[key].strip() == "") and not re.findall('[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$', updatedata[key]):
				
				errormsg = "Email address format was not correct: example@email.com"
				
				return render_template("error.html", errormsg = errormsg)
						
			
			# check provider name format
			if (key == "provider" and not updatedata[key].strip() == "") and not re.findall('[a-zA-Z]+[ ][a-zA-Z-,]+[ ][a-zA-Z]+', updatedata[key]):
				
				errormsg = "Provider format is incorrect: First Name (Space) Last Name, Degree"
				
				return render_template("error.html", errormsg = errormsg)
				
		#----------------------------------------------------------------------------------------------------------
		
		# create new patient action (update contact, taskid = 22)
		
		# set roar_id variable
		roar_id = updatedata["submitUpdateContactID"]
		
		#update task entry
		updatetaskentry = patientAction(roarid = roar_id,
								taskid = 22,
								taskdate = date.today(),
								mode = updatedata["updatemode"],
								outcome = "Update participant contact, provider, status",
								timespent = 2,
								note = re.sub("[<][a-zA-Z/]+[>]", "", updatedata["notes"]), #clear any html/script tags for cross scripting (not likely)
								staffid = current_user.userid,
								actiondate = datetime.now()
								)	
		
		# add task entry object						 
		session.add(updatetaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# query to retrieve patient action (update data) id (should be most recent commit)
		updateactionid = session.query(patientAction.actionid).filter(patientAction.taskid == 22, patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
		
		# extract updated VA station data
		if updatedata["vaStation"].strip() != "":
			
			# get current station information
			currentstationid = session.query(patientStation.patientstationid).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1).first()
			
			# remove active station designation from database
			updatecurrentstation = update(patientStation
								).where(patientStation.roarid == roar_id, patientStation.patientstationid == currentstationid[0]
								).values(activesta3n = 0)
			
			session.execute(updatecurrentstation)
			
			# insert updated data
			stationupdateentry = patientStation(roarid = roar_id,
									sta3n = int(re.findall('[0-9]{3}', updatedata["vaStation"])[0]),
									activesta3n = 1,
									actionid = updateactionid[0]
									)
			
			session.add(stationupdateentry)
			
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------
	
		# extract updated address data
		if updatedata["street1"].strip() != "" and updatedata["city"].strip() != "" and updatedata["state"].strip() != "" and updatedata["zipcode"].strip() != "":

			# get current address information
			currentaddressid = session.query(patientAddress.addressid).filter(patientAddress.roarid == roar_id, patientAddress.activeaddress == 1).first()
			
			# remove active station designation from database
			updatecurrentaddress = update(patientAddress
								).where(patientAddress.roarid == roar_id, patientAddress.addressid == currentaddressid[0]
								).values(activeaddress = 0)
			
			session.execute(updatecurrentaddress)
			
			# insert updated data
			addressupdateentry = patientAddress(roarid = roar_id,
									street1 = re.sub("[<][a-zA-Z/]+[>]", "", updatedata["street1"]).upper(),
									street2 = None if updatedata["street2"].strip() == "" else re.sub("[<][a-zA-Z/]+[>]", "", updatedata["street2"]).upper(),
									street3 = None if updatedata["street3"].strip() == "" else re.sub("[<][a-zA-Z/]+[>]", "", updatedata["street3"]).upper(),
									city = re.sub("[<][a-zA-Z/]+[>]", "", updatedata["city"]).upper(),
									state = updatedata["state"],
									zipcode = updatedata["zipcode"],
									activeaddress = 1,
									actionid = updateactionid[0]
									)
			
			session.add(addressupdateentry)
		
		#-----------------------------------------------------------------------------------------------------------------------------------------------------------

		# extract updated phone data
		if updatedata["teltype"].strip() != "" and updatedata["tel"].strip() != "" and updatedata["removetel"].strip() != "":

			# remove phone if indicated
			if updatedata["removetel"] != "Do not remove or replace existing phone numbers":
				
				# get current phone information
				currentphoneid = session.query(patientPhone.phoneid).filter(patientPhone.roarid == roar_id, patientPhone.patientphone == updatedata["removetel"]).first()
			
				# remove active phone designation from database
				removecurrentphone = update(patientPhone
								).where(patientPhone.roarid == roar_id, patientPhone.phoneid == currentphoneid[0]
								).values(activephone = 0,
								primaryphone = 0)
			
				session.execute(removecurrentphone)

			# demote current primary phone number to secondary phone number
			if updatedata["teltype"] == "Add primary phone number" and updatedata["removetel"] == "Do not remove or replace existing phone numbers":
		
				# get current phone information
				currentphoneid = session.query(patientPhone.phoneid).filter(patientPhone.roarid == roar_id, patientPhone.primaryphone == 1).first()
			
				# remove parimary phone designation from current primary phone
				updatecurrentphone = update(patientPhone
								).where(patientPhone.roarid == roar_id, patientPhone.phoneid == currentphoneid[0]
								).values(primaryphone = 0)
			
				session.execute(updatecurrentphone)
			
			
			# insert updated data / primary phone - move current number to secondary number
			phoneupdateentry = patientPhone(roarid = roar_id,
									patientphone = updatedata["tel"],
									activephone = 1,
									primaryphone = 1 if updatedata["teltype"] == "Add primary phone number" else 0,
									actionid = updateactionid[0]
									)
			
			session.add(phoneupdateentry)

		#-----------------------------------------------------------------------------------------------------------------------------------------------------------

		# extract updated email data

		# email information
		if updatedata["emailtype"] == "Add email address" and updatedata["email"].strip() != "":
		
			if re.findall('[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$', updatedata["removeemail"]):
			
				# get current phone information
				currentemailid = session.query(patientEmail.emailid).filter(patientEmail.roarid == roar_id, patientEmail.patientemail == updatedata["removeemail"].upper()).first()
			
				# remove active phone designation from database
				updatecurrentemail = update(patientEmail
									).where(patientEmail.roarid == roar_id, patientEmail.emailid == currentemailid[0]
									).values(activeemail = 0)
			
				session.execute(updatecurrentemail)
		
			# insert updated data / primary phone - move current number to secondary number
			emailentry = patientEmail(roarid = roar_id,
								patientemail = re.sub("[<][a-zA-Z/]+[>]", "", updatedata["email"]).upper(),
								activeemail = 1,
								actionid = updateactionid[0]
								)
			
			session.add(emailentry)

		#-----------------------------------------------------------------------------------------------------------------------------------------------------------

		# extract updated provider information - add provider, no removals
		if updatedata["providertype"].strip() != "" and updatedata["provider"].strip() != "" and updatedata["removeprovider"].strip() != "":
			
			# if remove provider - deactivate selected provider
			if updatedata["removeprovider"].strip() != "Do not remove or replace existing providers":
				
				# get current provider patient ID
				currentpatientproviderid = session.query(patientProvider.patientproviderid).filter(patientProvider.roarid == roar_id, patientProvider.provider == updatedata["removeprovider"]).first()
				
				# remove active provider designation from database
				updatecurrentprovider = update(patientProvider
									).where(patientProvider.roarid == roar_id, patientProvider.patientproviderid == currentpatientproviderid[0]
									).values(currentprovider = 0)
				
				session.execute(updatecurrentprovider)
			
			# assumes new va provider is at current va
			if updatedata["vaStation"].strip() == "" and updatedata["providertype"] == "Add new VA provider":
				
				providerSta3n = session.query(patientStation.sta3n
								).filter(patientStation.roarid == roar_id, patientStation.activesta3n == 1
								).first()[0]
			
			# assumes new va provider is at new va
			if updatedata["vaStation"].strip() != "" and updatedata["providertype"] == "Add new VA provider":
				
				providerSta3n = int(re.findall('[0-9]{3}', updatedata["vaStation"])[0])
			
			# create new provider entry
			providerupdateentry = patientProvider(roarid = roar_id,
									provider = updatedata["provider"].upper(),
									vaprovider = 1 if updatedata["providertype"] == "Add new VA provider" else 0,
									vaprovidersta3n = None if updatedata["providertype"] == "Add new NON-VA provider" else providerSta3n,
									currentprovider = 1,
									actionid = updateactionid[0]
									)
										
			session.add(providerupdateentry)
		
		
		# extract updated status data
		if updatedata["statustype"].strip() != "" and updatedata["statusdate"].strip() != "":

			# if unable to contact
			if updatedata["statustype"] == "Participant unable to contact":
			
				# update patient withdraw
				updatepatientutc = update(candidatePatient
									   ).where(candidatePatient.roarid == roar_id
									   ).values(utc = 1,
									            utcdate = updatedata["statusdate"],
									            utcid = updateactionid[0],
									            )
									            
				session.execute(updatepatientutc)

			# if lost to follow up
			if updatedata["statustype"] == "Participant lost to follow up":
			
				# update patient withdraw
				updatepatientlosttofup = update(candidatePatient
									   ).where(candidatePatient.roarid == roar_id
									   ).values(losttofup = 1,
									            losttofupdate = updatedata["statusdate"],
									            losttofupid = updateactionid[0],
									            )
									            
				session.execute(updatepatientlosttofup)

			# if withdraw from study
			if updatedata["statustype"] == "Participant has withdrawn":
			
				# update patient withdraw
				updatepatientwithdraw = update(candidatePatient
									   ).where(candidatePatient.roarid == roar_id
									   ).values(withdrawn = 1,
									            withdrawndate = updatedata["statusdate"],
									            withdrawnid = updateactionid[0],
									            )
									            
				session.execute(updatepatientwithdraw)
			
			
			# if deceased
			if updatedata["statustype"] == "Participant is deceased":
				
				# update patient death
				updatepatientdeath = update(candidatePatient
									   ).where(candidatePatient.roarid == roar_id
									   ).values(deceased = 1,
									            deceaseddate = updatedata["statusdate"],
									            deceasedid = updateactionid[0],
									            )
									            
				session.execute(updatepatientdeath)
		
		
		# commit added inserts / updates to respective tables
		session.commit()
		
		# ensure session is closed, may be redundant
		session.close()
		
		return redirect(url_for("participant_detail", roar_id=roar_id))
	

################################################################################################################################################

# update medication

@app.route("/update_medication", methods=["POST"])
@login_required
def update_medication():
	
	if request.method == "POST":
		roar_id = request.form["updateMedicationID"]
	
		# query for active medications
		participantmeds = session.query(patientMedication.patientmedid,
									patientMedication.medname,
									patientMedication.dose,
									patientMedication.unit,
									patientMedication.medstartdate,
									patientMedication.medenddate
									).filter(patientMedication.roarid == roar_id, patientMedication.medenddate == None
									).order_by(patientMedication.medenddate, patientMedication.medname
									).all()

		# medication data
		meds = session.query(medicationDim).order_by(medicationDim.medname).all()
										
	# ensure session is closed
	session.close()
		
	return render_template("update_medication.html", roarid=roar_id, ptMeds = participantmeds, meds = meds)


################################################################################################################################################

# get data from update medication form and commit to study database

@app.route("/commit_update_medications", methods=["POST"])
@login_required
def commit_update_medications():
	
	if request.method == "POST":
		
		# collect elements here for committing to databases
		
		updatemeddata = request.form.to_dict()
		
		# check data validity
		
		# set iterator to check total # of empties for first medication field
		firstmedvaluecount = 0
		
		for key in updatemeddata.keys():
				
			# count medication fields that are empty (first box)
			if key.startswith("med") and re.findall('[0-9]', key) == []:
				
				if updatemeddata[key].strip() == '':
					
					firstmedvaluecount += 1
			
			# count medication fields that are empty (first box)
			if key.startswith("updateMed") and updatemeddata[key].strip() == '':
					
				errormsg = "No end date provided for updated medication."
				
				return render_template("error.html", errormsg = errormsg)
				
		# should be 3 empties for first med option, if entered any partial data return error
		if firstmedvaluecount > 0 and firstmedvaluecount < 3:
			
			errormsg = "Some medication data was missing or multiple empty medication entries were submitted."
				
			return render_template("error.html", errormsg = errormsg)

		# create task entry

		# create new patient action (update contact, taskid = 24)
		
		# set roar_id variable
		roar_id = updatemeddata["submitUpdateMedicationID"]
		
		#update task entry
		updatemedtaskentry = patientAction(roarid = roar_id,
								taskid = 24,
								taskdate = date.today(),
								mode = updatemeddata["medupdatemode"],
								outcome = "Update participant medication",
								timespent = 2,
								note = re.sub("[<][a-zA-Z/]+[>]", "", updatemeddata["notes"]), #clear any html/script tags for cross scripting (not likely)
								staffid = current_user.userid,
								actiondate = datetime.now()
								)	
		
		# add task entry object						 
		session.add(updatemedtaskentry)
		
		# commit new patient action, commit to obtain automatically generated id - requery to get action id number to write to remaining tables
		session.commit() 

		# query to retrieve patient action (update data) id (should be most recent commit)
		updatemedid = session.query(patientAction.actionid).filter(patientAction.taskid == 24, patientAction.roarid == roar_id).order_by(patientAction.actiondate.desc()).first()
		
		#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

		# update enddates if any / session.bulk_update_mappings

		counter = 0
		medends = []
		medends_dicts = []
		key_values_end = ['medenddate', 'patientmedid', 'medendsource', 'medenddateid']

		for key in updatemeddata.keys():
			
			if key.startswith("updateMed") and updatemeddata[key].strip() != '':
				
				medends.append(updatemeddata[key])
				
				counter += 1
			
			if counter == 2:
				
				medends.append(updatemeddata["medupdatemode"])
				medends.append(updatemedid[0])
				
				medends_dicts.append(dict(zip(key_values_end, medends)))
				
				counter = 0
				medends = []
			
		#session.bulk_update_mappings for medications
		session.bulk_update_mappings(patientMedication, medends_dicts)


		# extract medication data / use session.bulk_insert_mappings
		
		counter = 0
		meds = [roar_id]
		med_dicts = []
		key_values = ['roarid', 'medname', 'dose', 'unit', 'medstartdate', 'medstartsource', 'medstartdateid']
		
		for key in updatemeddata.keys():
		
			if key.startswith("med") and updatemeddata[key].strip() != '' and counter < 4: 
				
				if updatemeddata[key] == 'mg' and counter == 0: # this accounts for empty submission 
					
					continue
				
				meds.append(updatemeddata[key])
				
				counter += 1
			
			if counter == 4:
				
				meds.append(updatemeddata["medupdatemode"])
				meds.append(updatemedid[0])
				
				med_dicts.append(dict(zip(key_values, meds)))
				
				counter = 0
				meds = [updatemeddata["submitUpdateMedicationID"]]
					
		#session.bulk_insert_mappings for medications
		session.bulk_insert_mappings(patientMedication, med_dicts)
		
		# commit mappings
		session.commit()

		return redirect(url_for("participant_detail", roar_id=updatemeddata["submitUpdateMedicationID"]))



################################################################################################################################################

# aggregate view of tasks

@app.route("/tasks")
@login_required
def tasks():
	
	if request.method == "POST":
		roar_id = request.form["userIdSelect"]
		
		# redirect to participant detail
		return redirect(url_for("participant_detail", roar_id=roar_id))
		
	tasks = session.execute("SELECT pat.roarid \
				,mvpcoreid \
				,ssn \
				,firstname \
				,lastname \
				,dob \
				,lastcontact \
				,eligible \
				,consented \
				,consenteddate \
				,randomizationstatus \
				,randomizationdate \
				,corereleasedate \
				,pilotparticipant \
				,istestrecord \
				,chartReview \
				,recruitmentLetter \
				,baselineSurvey \
				,pedigree \
				,specimen \
				,LDL \
				,geneticReport \
				,returnResults \
				,returnResultsDoc \
				,eosSurvey \
				,incentive \
				,CASE \
					WHEN randomizationstatus = 'DELAYED' THEN DATEADD(MONTH, 6, randomizationdate) \
					WHEN randomizationstatus = 'IMMEDIATE' OR randomizationstatus = 'PILOT' THEN randomizationdate \
					ELSE NULL \
				END AS genetictestdate \
				,DATEADD(MONTH, 6, randomizationdate) AS eosdate \
				FROM [{ENTER DATABASE}].[roar_app].[candidatePatient] pat \
					LEFT JOIN \
						(SELECT tasks.roarid \
							,chartReview \
							,recruitmentLetter \
							,baselineSurvey \
							,pedigree \
							,specimen \
							,LDL \
							,geneticReport \
							,returnResults \
							,returnResultsDoc \
							,eosSurvey \
							,incentive \
							,lastcontact \
						FROM (SELECT roarid \
							,[10] AS chartReview \
							,[11] AS recruitmentLetter \
							,[13] AS baselineSurvey \
							,[25] AS pedigree \
							,[14] AS specimen \
							,[15] AS LDL \
							,[17] AS geneticReport \
							,[18] AS returnResults \
							,[26] AS returnResultsDoc \
							,[19] AS eosSurvey \
							,[20] AS incentive\
						FROM \
							(SELECT roarid \
							        ,taskid \
							        ,taskdate \
							 FROM \
							 (SELECT \
								ROW_NUMBER() OVER(PARTITION BY roarid, taskid ORDER BY roarid, taskid, taskdate DESC) AS row \
								,roarid \
								,taskid \
								,taskdate \
							  FROM [{ENTER DATABASE}].[roar_app].[patientAction] \
							  ) srctab \
							  WHERE row = 1 \
							  ) tab \
							  PIVOT( \
								MAX(taskdate) \
								FOR taskid IN ( \
									[10] \
									,[11] \
									,[13] \
									,[25] \
									,[14] \
									,[15] \
									,[17] \
									,[18] \
									,[26] \
									,[19] \
									,[20] \
							)) AS pvt \
						) tasks \
						LEFT JOIN \
							(SELECT roarid \
								,MAX(taskdate) AS lastcontact \
							FROM [{ENTER DATABASE}].[roar_app].[patientAction] \
							WHERE (mode LIKE '%phone%' OR mode LIKE '%video%') \
							GROUP BY roarid) lastcontact \
						ON \
							tasks.roarid = lastcontact.roarid \
							) act \
						ON \
							pat.roarid = act.roarid \
				WHERE \
						deceased IS NULL \
					AND \
						utc IS NULL \
					AND \
						losttofup IS NULL \
					AND \
						declined IS NULL \
					AND \
						withdrawn IS NULL \
					AND \
						(eligible IS NULL OR eligible = 1) \
				ORDER BY DATEADD(MONTH, 6, randomizationdate), roarid")
	
	# convert to dictionary for jinja processing
	task_list = []
	
	for task in tasks:
		task_list.append(dict(task))

	# close query transaction
	session.close()

	return render_template("tasks.html", 
	
				# data
				tasks = task_list,
							
				# functions
				today = date.today, timedelta = timedelta, strftime=datetime.strftime, relativedelta=relativedelta, max=np.max, min=np.min)
