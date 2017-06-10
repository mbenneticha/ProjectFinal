import logging
import json
import entities as ent
import controller as cntrl
import creds
from google.appengine.ext import ndb
from oauth2client import client, crypt

from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, send_file

app = Flask(__name__)


#--------------------------------------------------------------START GENERAL ROUTES-------------------------------------------------------------------------------

@app.route('/dream-catcher/v1/user/login',methods=['POST'])
def verifyToken():
	payload = request.get_json();

	if payload is None:
		abort(400)

	try:
		idinfo = client.verify_id_token(payload['token'], creds.CLIENT_ID)
		
		if idinfo['aud'] != creds.ANDROID_CLIENT_ID:
			raise crypt.AppIdentityError("Unrecognized client.")
			
		if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
			raise crypt.AppIdentityError("Wrong issuer.")
	except crypt.AppIdentityError:
		abort(500)

	accId = idinfo['sub']
	res,status = cntrl.getUser(ent.User,ent.Account,accId)

	#if new user
	if status == 204:
		payload = {'account':idinfo['sub'],'email':idinfo['email'],'fname':idinfo['given_name'],'lname':idinfo['family_name']}
		res,status = cntrl.addUser(payload)
	#if returning user
	elif status == 200:
		res,status = {'message':'Signed in as ' + idinfo['given_name'] + ' ' + idinfo['family_name'], 'email':idinfo['email'],
		'fname':idinfo['given_name'],'lname':idinfo['family_name'],'account':idinfo['sub'],'user':res['user']},200

	res = jsonify(res)
	res.headers['Status'] = status

	return res

@app.route('/dream-catcher/v1/resources',methods=['GET'])
def getEndPoints():
	'''displays all resource endpoints'''

	if request.method == 'GET':
		res,status = { 'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1',
			'resources': 
			{
			    'accounts': 
			    {
			        'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/accounts',
			        'description':'Get all accounts',
			        'method' : 'GET'
			    },
			    'users1': 
			    {
			        'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/users',
			        'description':'Get all users',
			        'method' : 'GET'
			    },
			    'users2':
			    {
			    	'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/accounts/<account id>/users',
			        'description':'Get all users by account key',
			        'method' : 'GET'
			    },
			    'users3':
			    {
			    	'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/accounts/users/queries/1',
			        'description':'Adds a user',
			        'method' : 'POST',
			        'requires':'Account and user ids in request body'
			    },
			    'users4':
			    {
			    	'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/accounts/users/queries/2',
			        'description':'Updates a user',
			        'method' : 'PUT',
			        'requires':'Account and user ids in request body'
			    },
			    'users5':
			    {
			    	'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/accounts/<account id>/users/<user id>',
			        'description':'Deletes a user',
			        'method' : 'DELETE'
			    },
			    'dreams1': 
			    {
			        'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/dreams',
			        'description':'Get all dreams',
			        'method': 'GET'
			    },
			    'dreams2': 
			    {
			        'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/dream-catcher/v1/accounts/<account id>/users/<user id>/dreams',
			        'description':'Get all dreams had by a specific user',
			        'method':'GET'
			    },
			    'dreams3': 
			    {
			        'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/dream-catcher/v1/accounts/users/dreams/queries/1',
			        'description':'Adds a user dream',
			        'method':'POST',
			        'requires':'Account and user ids in request body'
			    },
			    'dreams4': 
			    {
			        'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/dream-catcher/v1/accounts/users/dreams/queries/2',
			        'description':'Updates a user dream',
			        'method':'PUT',
			        'requires':'Account and user ids in request body'
			    },
			    'dreams5': 
			    {
			        'url': 'http://python-gae-quickstart-164103.appspot.com/dream-catcher/v1/dream-catcher/v1/accounts/<account id>/users/<user id>/dreams/<dream id>',
			        'description':'Deletes a user dream',
			        'method':'DELETE'
			    },
    		}
    	}, 200
	else:
		abort(405)

	res = jsonify(res)
	res.headers['Status'] = status
	return res

@app.route('/dream-catcher/v1/<kind>',methods=['GET'])
def getResourceAll(kind):
	'''gets all entities of a specific kind'''

	kindDict = {'accounts':ent.Account,'users':ent.User,'dreams':ent.Dream} #add to this as you go

	if kind in kindDict:
		kindVal = kindDict[kind]
	else:
		res,status = jsonify(message='Invalid url endpoint'),400 #add info key with link to homepage ->it will show all valid endpoints
		res.headers['Status'] = status
		return res

	if request.method == 'GET':
		if request.args != {}:
			res,status = cntrl.getByQueryString(kindVal,request.args.to_dict())
			res = jsonify(res)
		else:
			res,status = cntrl.getAll(kindVal)
			res = jsonify(res)

		res.headers['Status'] = status
	else:
		abort(405)
		
	return res

#--------------------------------------------------------------END GENERAL ROUTES-------------------------------------------------------------------------------




#---------------------------------------------------------------START USER ROUTES-------------------------------------------------------------------------------

@app.route('/dream-catcher/v1/accounts/<int:accId>/users',methods=['GET'])
def returnUserByAccount(accId):
	'''gets user by account key'''

	if request.method == 'GET':
		res,status = cntrl.getUser(ent.User,ent.Account,int(accId))
		res = jsonify(res)
		res.headers['Status'] = status
	else:
		abort(405)

	return res

@app.route('/dream-catcher/v1/accounts/users/queries/<queryNum>',methods=['POST','PUT'])
def queryUser(queryNum):

	'''adds or updates a user entity'''
	payload = request.get_json()

	if(payload is None):
		abort(400)

	if(queryNum == '1'):
		if request.method == 'POST':
			res,status = cntrl.addUser(payload)
		else:
			abort(405)
	elif(queryNum == '2'):
		if request.method == 'PUT':
			res,status = cntrl.updateUser(payload)
		else:
			abort(405)
	else:
		res,status = {'message':'Invalid query number.','post':1,'put':2},400

	res = jsonify(res)
	res.headers['Status'] = status

	return res

@app.route('/dream-catcher/v1/accounts/<int:accId>/users/<int:userId>',methods=['DELETE'])
def removeUser(userId,accId):
	if request.method == 'DELETE':
		res,status = cntrl.deleteUser(userId,accId)
	else:
		abort(405)

	res = jsonify(res)
	res.headers['Status'] = status

	return res
#-----------------------------------------------------------------END USER ROUTES-------------------------------------------------------------------------------



#-----------------------------------------------------------------START DREAM ROUTES-------------------------------------------------------------------------------

@app.route('/dream-catcher/v1/accounts/<accId>/users/<userId>/dreams',methods=['GET'])
def returnDreamByUser(userId,accId):
	'''gets dream by user key'''

	if request.method == 'GET':
		res,status = cntrl.getDreams(ent.Account,ent.User,accId,userId)
		res = jsonify(res)
		res.headers['Status'] = status
	else:
		abort(405)

	return res

@app.route('/dream-catcher/v1/accounts/users/dreams/queries/<queryNum>',methods=['POST','PUT'])
def queryDream(queryNum):
	'''adds or updates a user entity'''

	res,status = {'message':'Something went horribly wrong...'},500
	payload = request.get_json()

	if(payload is None):
		abort(400)

	if(queryNum == '1'):
		if request.method == 'POST':
			res,status = cntrl.addDream(payload)
		else:
			abort(405)
	elif(queryNum == '2'):
		if request.method == 'PUT':
			res,status = cntrl.updateDream(payload)
		else:
			abort(405)
	else:
		res,status = {'message':'Invalid query number.','post':1,'put':2},400

	res = jsonify(res)
	res.headers['Status'] = status

	return res

@app.route('/dream-catcher/v1/accounts/<accId>/users/<userId>/dreams/<dreamId>',methods=['DELETE'])
def removeDream(userId,accId,dreamId):
	if request.method == 'DELETE':
		res,status = cntrl.deleteDream(userId,accId,dreamId)
	else:
		abort(405)

	res = jsonify(res)
	res.headers['Status'] = status

	return res

'''
@app.route('/dream-catcher/v1/accounts/<accId>/users/<userId>/dreams/clouds',methods=['GET'])
def makeWordCloud():
	if request.method == 'GET':
		res,status = cntrl.getDreams(ent.Account,ent.User,accId,userId)
		res,status = cntrl.genSummaryCloud(res)
	else:
		abort(405)
	res = jsonify(res)
	res.headers['Status'] = status
	return res
'''
#-----------------------------------------------------------------END DREAM ROUTES-------------------------------------------------------------------------------
	


@app.after_request
def after_request(response):
	response.mimetype = 'application/json'
	response.cache_control.max_age = 300
	#response.headers['Status'] = response.status_code
	response.headers['Content-Language'] = 'en'
	response.headers['Accept'] = 'application/json'
	return response


@app.errorhandler(500)
def serverError(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

@app.errorhandler(400)
def requestError(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'Bad request. Content-Type should be application/json', 400

@app.errorhandler(404)
def resourceError(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'Resource not found', 405

@app.errorhandler(405)
def methodError(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'Wrong request method was used', 405

if __name__ == '__main__':
    app.run()