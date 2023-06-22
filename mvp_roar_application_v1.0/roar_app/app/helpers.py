# Helper functions to calculate, process data

# Modules to import
from datetime import date

# Function to accurately calculate age from date of birth
def calculatedAge(dob):
	today = date.today()
	try:
		birthday = dob.replace(year = today.year)
	
	# raised when birthday is February 29 
	# and current year is not a leap year
	except ValueError:
		birthday = dob.replace(year = today.year,
			month = dob.month + 1, day = 1)
	
	if birthday > today:
		return today.year - dob.year - 1
	else:
		return today.year - dob.year
