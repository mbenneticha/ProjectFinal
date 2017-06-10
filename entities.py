from google.appengine.ext import ndb

class Model(ndb.Model):
	def to_dict(self):
		dictionary = super(Model,self).to_dict()
		dictionary['key'] = self.key.id()
		return dictionary

class Account(ndb.Model):
	pass

class User(ndb.Model):

	fname = ndb.StringProperty(required=True,indexed=True)
	lname = ndb.StringProperty(required=True,indexed=True)
	email = ndb.StringProperty(required=True,indexed=True)
	

class Dream(ndb.Model):
	summary = ndb.TextProperty(required=True,indexed=False,default="None")
	date = ndb.DateProperty(required=True,indexed=True,auto_now_add=True)
	mood = ndb.StringProperty(indexed=True,repeated=True)
	title = ndb.StringProperty(required=True,indexed=True,default="None")
	#tags = ndb.StringProperty(indexed=True,repeated=True)
	dreamType = ndb.StringProperty(required=True,indexed=True,choices=['Epic','Lucid','Nightmare','Recurring','False Awakening','Precognitive','Mundane','None'],default='None')

class Interpretation(ndb.Model):
	method = ndb.StringProperty(required=True,indexed=True,choices=['Psychoanalysis','Jungian Analysis','Gestalt Analysis'])
	content = ndb.TextProperty(required=True,indexed=False)

class Thread(ndb.Model):
	poster = ndb.StringProperty(required=True,indexed=True)
	title = ndb.StringProperty(required=True,indexed=True)
	content = ndb.TextProperty(required=True,indexed=False)
	date = ndb.DateProperty(required=True,indexed=True)
	tags = ndb.StringProperty(indexed=True,repeated=True)

class Comment(ndb.Model):
	commentor = ndb.StringProperty(required=True,indexed=False)
	content = ndb.TextProperty(required=True,indexed=False)
	date = ndb.DateTimeProperty(required=True,indexed=True,auto_now_add=True)
	userId = ndb.KeyProperty(kind=User,required=True,indexed=True)

#---------------------------------------------------------------------------------------------------------------------------------------------------
def createAccount(id):
	return Account(id=id)

def createUser(parentKey,fields):
	return User(parent=parentKey,fname=str(fields['fname']),lname=str(fields['lname']),email=str(fields['email']))
	#return User(parent=parentKey,fname=str(fields['fname']),lname=str(fields['lname']),email=str(fields['email']),
	#	username=str(fields['username']),gender=str(fields['gender']),age=int(fields['age']))

def createDream(parentKey,fields):
	dream = Dream(parent=parentKey)

	if 'summary' in fields:
		dream.summary = str(fields['summary'])

	if 'mood' in fields:
		dream.mood = fields['mood']

	if 'title' in fields:
		dream.title = str(fields['title'])

	if 'desc' in fields:
		dream.desc = str(fields['desc'])

	if 'tags' in fields:
		dream.tags = fields['tags']

	if 'type' in fields:
		dream.dreamType = str(fields['type'])

	return dream

def saveEntity(entity):
	return entity.put()

def saveEntityAsync(entity):
	return entity.put_async()