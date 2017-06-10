import entities as ent
from urlparse import urlparse
from datetime import datetime
from operator import itemgetter
from google.appengine.ext import ndb
from google.appengine.api import search
from flask import jsonify


VALID_USER_KEYS = ['account','user','fname','lname','email']
VALID_DREAM_KEYS = ['account','user','dream','summary','mood','title','desc','tags','type','date']
VALID_DREAM_TYPES = ['Epic','Lucid','Nightmare','Recurring','False Awakening','Precognitive','Mundane','None']
NON_INDEXED_KEYS = ['summary','desc','content','commentor']

#------------------------------------------------------------START GENERAL USAGE METHODS---------------------------------------------------------------------------

def getAll(cls):
	'''gets all resource keys of a given model type. provides only eventual consistency'''

	results = cls.query().fetch(keys_only=True)

	if len(results) > 0:
		for i in range(len(results)):
			results[i] = {r[0].lower():r[1] for r in results[i].pairs()}
		return results,200
	else:
		return {'message':'Query returned zero results'}, 204

def getByQueryString(entity,queryString):
	'''gets a resource by its properties. property=value in query string'''

	limitResults = False
	fieldsWanted = False

	query = entity.query()

	if 'limit' in queryString:
		limitResults = True
		limit = int(queryString.pop('limit',None))

	if 'fields' in queryString:
		fieldsWanted = True
		fields = queryString.pop('fields',None)
		fields = fields.split(",")

	try:
		for k,v in queryString.items():

			if v.isdigit():
				val = int(v)
				query = query.filter(entity._properties[k] == val)
			else:
				if k == 'date':
					v = datetime.strptime(v,"%Y-%m-%d" )
				query = query.filter(entity._properties[k] == v)
	except KeyError:
		return {'message' : 'Invalid key was passed in query string' ,'valid keys' : '{}'.format([entity._properties[p]._name for p in entity._properties if entity._properties[p]._name not in NON_INDEXED_KEYS])},400
	except ValueError:
		return {'message' : 'Invalid value was passed in query string','suggestion' : 'dates should be in the following format YYYY-mm-dd'},400
	
	try:
		if limitResults and not fieldsWanted:
			res = [r.to_dict() for r in query.fetch(limit)]
		elif fieldsWanted and not limitResults:
			res = [r.to_dict() for r in query.fetch(projection=[entity._properties[f]._name for f in fields])]
		elif limitResults and fieldsWanted:
			res = [r.to_dict() for r in query.fetch(limit,projection=[entity._properties[f]._name for f in fields])]
		else:
			res = [r.to_dict() for r in query.fetch()]
	except:
		return {'message' : 'Invalid query string', 'restrictions':'1) can\'t specify unindexed properties in query string fields key. 2) a key\'s value cannot be searched for and also used in the fields key. ex: ../dreams?fname=foo&fields=fname',
		'unidexed properties':'{}'.format(NON_INDEXED_KEYS)},400

	return res,200

#------------------------------------------------------------END GENERAL USAGE METHODS---------------------------------------------------------------------------



#---------------------------------------------------------------START USER METHODS-------------------------------------------------------------------------------

def getUser(cls,kind,ancestorId):
	try:
		result = cls.query(ancestor=ndb.Key(kind,ancestorId)).fetch()
	except ValueError,e:
		return str(e), 400

	if len(result) > 0:
		res,status = result[0].to_dict(),200
		res.update({'user':result[0].key.id(),'account':ancestorId})
		return res,status
	else:
		return {'message':'No such user exists in the database. Make sure the accountID and/or userID is accurate'},204

def addUser(payload):

	accKey = None
	if _verifyRequestKeys(VALID_USER_KEYS,payload):
		return {'message':'Please include the following keys in your request -> {}'.format(VALID_USER_KEYS)},400
	
	else:
		try:	
			acc = ent.createAccount(payload['account'])
			accKey = ent.saveEntity(acc)
			user = ent.createUser(accKey,payload)
			userKey = ent.saveEntity(user)
		except KeyError:
			if accKey is not None:
				accKey.delete()
			return {'message' : 'A requried key is missing from the request body', 'required' : '{}'.format(VALID_USER_KEYS)},400
		except ValueError:
			if accKey is not None:
				accKey.delete()
			return {'message' : 'Invalid value was passed in request body'},400

		return {'message':'New user account created', 'account':accKey.id(),'user':userKey.id(),'fname':payload['fname'],'lname':payload['lname'],'email':payload['email']},201

def updateUser(payload):
	'''updates a user entity'''

	if 'account' not in payload or 'user' not in payload:
		return {'message':'This request requires both the account and user keys'},400

	if _verifyRequestKeys(VALID_USER_KEYS,payload):
		return {'message':'Please include the following keys in your request -> {}'.format(VALID_USER_KEYS)},400
		
	user = ndb.Key(ent.Account,int(payload['account']),ent.User,int(payload['user'])).get()

	if user != None:
		if 'fname' in payload:
			user.fname = payload['fname']
		if 'lname' in payload:
			user.lname = payload['lname']
		if 'email' in payload:
			user.email = payload['email']
		if 'username' in payload:
			user.username = payload['username']

		userKey = ent.saveEntity(user)
		return {'message':'User resource has been updated','user':userKey.id()},200
	else:
		return {'message':'Resource not found'},404

def deleteUser(userId,accId):
	'''deletes a user entity'''

	accKey = ndb.Key(ent.Account,int(accId))
	userKey = ndb.Key(ent.Account,int(accId),ent.User,int(userId))
	acc = accKey.get()
	user = userKey.get()

	if user != None:
		dreams = ent.Dream.query(ancestor=userKey).fetch()

		for d in dreams:
			d.key.delete()

		user.key.delete()
		acc.key.delete()
		return {'message':'User resource deleted'},200
	else:
		return {'message':'Resource not found'},404

#---------------------------------------------------------------END USER METHODS-------------------------------------------------------------------------------



#---------------------------------------------------------------START DREAM METHODS-------------------------------------------------------------------------------

def getDreams(accKind,userKind,accId,userId):
	query = ent.Dream.query(ancestor=ndb.Key(accKind,accId,userKind,userId)).order(-ent.Dream.date)
	results = query.fetch();

	if len(results) > 0:
		dreamIds = [{'account':accId,'user':userId,'dream':r.key.id()} for r in results]

		results = [r.to_dict() for r in results]
		results = sorted(results, key=itemgetter('date'),reverse=True)

		for i in range(len(results)):
			results[i]['date'] = str(results[i]['date'])
			results[i].update(dreamIds[i])
		return results,200
	else:
		return {'message':'No such dream exists in the database', 'help':'Make sure the accountID and/or userID is accurate. If they are accurate, the user has no dreams recorded'},204

def addDream(payload):
	
	if _verifyRequestKeys(VALID_DREAM_KEYS,payload):
		return {'message':'The following keys are valid for the request body -> {}. Only account and user are required.' +
		' Defaults values will be chosen for all other keys if not present in the request body'.format(VALID_DREAM_KEYS)},400
	
	if 'type' in payload:
		if _verifyChoices(VALID_DREAM_TYPES,payload['type']):
			return {'message':'Please use one of the following dream type values -> {}'.format(VALID_DREAM_TYPES)},400
	
	try:
		ancestorPath = ndb.Key(ent.Account,payload['account'],ent.User,payload['user'])
		dream = ent.createDream(ancestorPath,payload)
		dreamKey = ent.saveEntity(dream)
	except KeyError:
		return {'message' : 'A requried key is missing from the request body', 'required' : '[\'account\', \'user\']'},400
	except ValueError:
		return {'message' : 'An invalid value was passed in request body.'},400

	return {'message':'Dream was created and added to the database','dream':dreamKey.id()},201

def updateDream(payload):
	'''updates a dream entity'''

	if 'account' not in payload or 'user' not in payload or 'dream' not in payload:
		return {'message':'This request requires the account, user and dream keys'},400

	if _verifyRequestKeys(VALID_DREAM_KEYS,payload):
		return {'message':'Valid Keys -> {}'.format(VALID_DREAM_KEYS)},400
		
	dream = ndb.Key(ent.Account,payload['account'],ent.User,payload['user'],ent.Dream,int(payload['dream'])).get()

	if dream != None:
		if 'summary' in payload:
			dream.summary = payload['summary']
		if 'mood' in payload:
			if type(payload['mood']) is list:
				dream.mood = payload['mood']
			else:
				return {'message':'The value of the mood key must be a list'},400
		if 'title' in payload:
			dream.title = payload['title']
		if 'desc' in payload:
			dream.desc = payload['desc']
		if 'type' in payload:
			if _verifyChoices(VALID_DREAM_TYPES,payload['type']):
				return {'message':'Please use one of the following dream type values -> {}'.format(VALID_DREAM_TYPES)},400
			else:
				dream.dreamType = payload['type']
		if 'tags' in payload:
			if type(payload['tags']) is list:
				dream.tags = payload['tags']
			else:
				return {'message':'The value of the tags key must be a list'},400
		if 'date' in payload:
			dream.date = datetime.strptime(payload['date'],'%Y-%m-%d').date()

		dreamKey = ent.saveEntity(dream)
		return {'message':'Dream has been updated','dream':dreamKey.id()},200
	else:
		return {'message':'Resource not found'},404

def deleteDream(userId,accId,dreamId):
	'''deletes a user entity'''

	dream = ndb.Key(ent.Account,accId,ent.User,userId,ent.Dream,int(dreamId)).get()

	if dream != None:
		dream.key.delete()
		return {'message':'Dream deleted'},200
	else:
		return {'message':'Dream not found'},404


#---------------------------------------------------------------END DREAM METHODS-------------------------------------------------------------------------------



def _verifyRequestKeys(validKeys,payload):
	failed = False

	for k in payload:
		if k not in validKeys:
			failed = True


	return failed

def _verifyChoices(validChoices,choice):
	failed = False

	if choice not in validChoices:
		failed = True

	return failed