from flask import Flask, render_template, redirect, url_for, session, request, logging, flash
from flask_sqlalchemy import SQLAlchemy 
from functools import wraps
from collections import Counter

app = Flask(__name__)
#configure SQLAlchemy to work with the roomie.db database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///roomie.db'
db = SQLAlchemy(app)

#construct the class for the user table in the database
class User(db.Model):
	__tablename__ = 'users'
	id = db.Column('id', db.Integer, nullable = False, primary_key = True, unique = True)
	name = db.Column('name', db.String(), nullable = False)
	email = db.Column('email', db.String(), nullable = False, unique = True)
	username = db.Column('username', db.String(), nullable = False, unique = True)
	password = db.Column('password', db.String(), nullable = False)
#construct the class for the request table in the database
class Request(db.Model):
	__tablename__ = 'requests'
	id = db.Column('id', db.Integer, nullable = False, primary_key = True, unique = True)
	name = db.Column('name', db.String(), nullable = False, unique = True)
	request1 = db.Column('request1', db.String(), nullable = False)
	request2 = db.Column('request2', db.String(), nullable = False)
	request3 = db.Column('request3', db.String(), nullable = False)
	userKey = db.Column('userKey', db.Integer, nullable = False)
	titleKey = db.Column('titleKey', db.Integer, nullable = False)
#construct the class for the form table in the database
class FormTable(db.Model):
	__tablename__ = 'forms'
	id = db.Column('id', db.Integer, nullable = False, primary_key = True, unique = True)
	title = db.Column('title', db.String(), nullable = False, unique = False)
	userKey = db.Column('userKey', db.Integer, nullable = False)
	responses = db.Column('responses', db.Integer)

#this creates a list of you, the people you requested, and the people who requested you
def requestMatches(id):
	requestResults = Request.query.filter_by(titleKey = id).all()
	requestedMeList = []
	for result in requestResults:
		tempName = result.name
		tempList = []
		tempList.extend([tempName, result.request1, result.request2, result.request3])
		for other in requestResults:
			if tempName == other.request1:
				tempList.append(other.name)
			elif tempName == other.request2:
				tempList.append(other.name)
			elif tempName == other.request3:
				tempList.append(other.name)
		#now remove any empty strings
		if "" in tempList:
			tempList.remove("")
		uniqueList = []
		#remove duplicates by making a new list and only adding things to it if they aren't already in it
		#that way, when a duplicate comes up, it won't be added because it's already there
		for t in tempList:
			if t not in uniqueList:
				uniqueList.append(t)

		requestedMeList.append(uniqueList)
	return closeMatches(requestedMeList, id)

#this creates the lists of those who are closest to eachother
#they're basically individualized rooms, which don't work on a global level
#because two people who are on other eachother's lists may have different lists
def closeMatches(requestedMeList, id):
	#the list of rooms is initialized here, but won't be used until later
	closeList = []
	#this goes through each entry of the requestedMeList (which is basically just the old uniqueTempList)
	#each entry is a list of people connected to 'me' by either my requests or 
	#by theirs
	for requestedMe in requestedMeList:
		personsRequests = []
		#store the requester's name in a variable
		me = requestedMe[0]
		#this goes through each person in the list of people connected to 'me'
		for person in requestedMe:
			#get that person and their requests from the database
			temp = Request.query.filter_by(name = person, titleKey = id).first()
			#ensure the query returned something
			if not temp:
				continue
			#sort their name and requests and put the sorted list of requests into a list
			deleteEmpty = [temp.name, temp.request1, temp.request2, temp.request3]
			if "" in deleteEmpty:
				deleteEmpty.remove("")

			personsRequests.extend(sorted([deleteEmpty]))
		#compare each group of requests to the original person's requests
		indexes = []
		#this returns the number of matches there are between 'me' and everyone else
		for person in personsRequests:
			indexes.append(len(set(personsRequests[0]).intersection(set(person))))
		#now pick the 4 highest values (the first match will be 100%, as it'll match 'me' with itself)
		tempCloseList = []
		for i in range(0, 4):
			highestIndex = indexes.index(max(indexes))
			if(indexes[highestIndex] <= 0):
				continue
			tempCloseList.append(personsRequests[highestIndex][0])
			indexes[highestIndex] = -1
			highestIndex = indexes.index(max(indexes))
		closeList.append(tempCloseList)
	return makeRooms(closeList, id)

def makeRooms(closeList, id):
	#go through each person's proposed room and search for others that have that person
	roomList = []
	matchList = []
	#this will be used later if one person is put in two rooms
	commonScores = []
	for person in closeList:
		personMatchList = []
		for others in closeList:
			if person[0] in others:
				#add each person who had you's name to this list
				personMatchList.append(others[0])
		matchList.append(personMatchList)
	for person in matchList:
		#find the others who have you and store them in the tempList
		tempList = []
		for others in matchList:
			if person[0] in others:
				#get the top 4 people
				tempList.append(others)
		#now flatten the list and select the 4 most common names. Then add them to the room list
		flattened = sum(tempList, [])
		common = [word for word, word_count in Counter(flattened).most_common(4)]
		commonScores.append(Counter(flattened).most_common(4))
		roomList.append(common)
	#now remove redundant rooms
	uniqueList = []
	for room in roomList:
		if room not in uniqueList:
			uniqueList.append(room)
	roomList = uniqueList
	#remove redundant scores
	uniqueList = []
	for score in commonScores:
		if score not in uniqueList:
			uniqueList.append(score)

	roomList = removeDoubles(roomList, commonScores)
	roomList = consolidate(roomList, commonScores)
	return roomList

def removeDoubles(roomList, commonScores):
	for i in range(len(roomList)):
		#go through each person in each room
		for j in range(len(roomList[i])):
			# see if they're also in another room
			for k in range(len(roomList)):
				for l in range(len(roomList[k])):
					if roomList[i][j] == roomList[k][l]:
						#now compare their scores in each room and delete the one with
						#the lower score
						if commonScores[i][j][1] > commonScores[k][l][1]:
							roomList[i][j] = ''
						elif commonScores[i][j][1] < commonScores[k][l][1]:
							roomList[k][l] = ''
	return roomList

#this will ensure no one is in a room by themselves people
def consolidate(roomList, commonScores):
	#so it can remove empty rooms later
	deleteIndex = []
	for i in range(len(roomList)):
		#if someone is by themselves, see if others requested them and have an open spot
		counter = 0
		for j in range(len(roomList[i])):
			#see how many people are missing from the room
			if not roomList[i][j]:
				counter += 1
			#if 3 are missing, i.e. only one perso is there, try to find anothe room to put them in
			if counter == 3:
				for k in range (len(roomList)):
					otherCounter = 0
					#check to see if another room has an open spot in it
					for l in range (len(roomList[k])):
						if not roomList[k][l]:
							otherCounter += 1
					#if it does, check to see that they atleast have some connection to the othe room
					#if they do, add them, and add their room's index to the delete index, so the empty
					#room can be removed
					if otherCounter > 0 and otherCounter < 3:
						for l in range (len(roomList[k])):
							if commonScores[k][l][0] == roomList[i][j]:
								roomList[k][l] = roomList[i][j]
								roomList[i][j] = ''
								deleteIndex.append(i)
	for i in range(len(deleteIndex)):
		del roomList[deleteIndex[i]]
	return roomList






#ensure that the user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not 'logged_in' in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function