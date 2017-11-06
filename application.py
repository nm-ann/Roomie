from flask import Flask, render_template, redirect, url_for, session, request, logging, flash
from flask_sqlalchemy import SQLAlchemy 
from wtforms import Form, StringField, PasswordField, validators
from passlib.hash import sha256_crypt

from helpers import *

#the home page
@app.route('/')
def index():
	return render_template('index.html')

#this is the class for the roomate request form. It take a person's name
#and three requests
class RequestForm(Form):
	fullName = StringField('Full Name', [validators.DataRequired()])
	request1 = StringField('First Request')
	request2 = StringField('Second Request')
	request3 = StringField('Third Request')
#this is the class for the user registration form. 
class RegistrationForm(Form):
	name = StringField('Name', [validators.DataRequired()])
	email = StringField('Email', [validators.Email(message='Invalid email address')])
	username = StringField('Username', [validators.Length(min=8, max=25)])
	password = PasswordField('Password', [validators.DataRequired(), 
		validators.EqualTo('confirm', message='Passwords do not match')])
	confirm = PasswordField('Confirm Password')
#this is the class for the form creation form. 
class CreateForm(Form):
	title = StringField('title', [validators.Length(min=8, max=25)])

#the account registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegistrationForm(request.form)
	if request.method == 'POST' and form.validate():
		newUser = User(name = form.name.data, email = form.email.data, username = 
			form.username.data, password = sha256_crypt.encrypt(str(form.password.data)))
		db.session.add(newUser)
		db.session.commit()
		return redirect(url_for('login'))
	else:
		return render_template('register.html', form=form)

#the log in page
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		uname = request.form['username']
		pword = request.form['password']

		result = User.query.filter_by(username = uname).first()
		if result:
			if sha256_crypt.verify(pword, result.password):
				session['logged_in'] = True
				session['username'] = uname
				return redirect(url_for('forms'))
			else:
				error = "Invalid Login"
			return render_template('login.html', error=error)
		else:
			error = "Invalid Username"
			return render_template('login.html', error=error)
	else:
		return render_template('login.html')

#the page for a specific form
@app.route('/form_page/<string:id>', methods=['GET', 'POST'])
def form_page(id):
	form = RequestForm(request.form)
	result = FormTable.query.filter_by(id = id).first()
	if request.method == 'POST' and form.validate():
		newRequest = Request(name = form.fullName.data, request1 = form.request1.data, request2 = 
			form.request2.data, request3 = form.request3.data, userKey = result.userKey, titleKey = result.id)
		result.responses += 1
		db.session.add(newRequest)
		db.session.commit()
		if session['logged_in']:
			return redirect(url_for('forms'))
		else:
			return redirect(url_for('index'))
	else:
		return render_template('form_page.html', title=result.title, form=form)

@app.route('/forms')
@login_required
def forms():
	curUser = User.query.filter_by(username = session['username']).first()
	results = FormTable.query.filter_by(userKey = curUser.id).all()
	if results:
		return render_template('forms.html', forms=results)
	else:
		msg = 'No Forms Found'
		return render_template('forms.html', msg=msg)

@app.route('/add_form', methods=['GET', 'POST'])
@login_required
def add_form():
	form = CreateForm(request.form)
	if request.method == 'POST' and form.validate():
		curUser = User.query.filter_by(username = session['username']).first()
		newForm = FormTable(title = form.title.data, userKey = curUser.id, responses = 0)
		db.session.add(newForm)
		db.session.commit()
		return redirect(url_for('forms'))
	else:
		return render_template('add_form.html', form=form)

@app.route('/delete_form/<string:id>', methods=['POST'])
@login_required
def delete_form(id):
	result = FormTable.query.filter_by(id = id).first()
	db.session.delete(result)
	db.session.commit()

	flash("Form deleted", "success")
	return redirect(url_for('forms'))

@app.route('/form_results/<string:id>')
@login_required
def form_results(id):
	formResult = FormTable.query.filter_by(id = id).first()
	#requestResults = Request.query.filter_by(titleKey = id).all()
	#if requestResults:
	#	return render_template('form_results.html', title=formResult.title, rooms=requestResults)
	#else:
	#	msg = 'No Responses Found'
	#	return render_template('form_results.html', msg=msg)
	requestResults = requestMatches(id)
	if requestResults:
		return render_template('form_results.html', title=formResult.title, rooms=requestResults)
	else:
		msg = 'No Responses Found'
		return render_template('form_results.html', msg=msg)

@app.route('/logout')
@login_required
def logout():
	session.clear()
	return redirect(url_for('login'))

if __name__ == '__main__':
	app.run(debug = True)