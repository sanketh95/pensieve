import os
from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2
import webapp2_extras.appengine.auth.models
from webapp2_extras import security, sessions, auth
import jinja2
from datetime import datetime
import time

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)


DEFAULT_NAME = 'default_pensieve'

def pensieve_key(name=None):
	"""Constructs a Datastore key for a Guestbook entity with guestbook_name."""
	if name is not None:
		return ndb.key('Pensieve', name);
	return ndb.Key('Pensieve', DEFAULT_NAME)

class User(webapp2_extras.appengine.auth.models.User):
	def set_password(self, raw_password):
		self.password = security.generate_password_hash(raw_password, length=12)

	@classmethod
	def get_by_auth_token(cls, user_id, token, subject='auth'):
		token_key = cls.token_model.get_key(user_id, subject, token)
		user_key = ndb.Key(cls, user_id)
		valid_token, user = ndb.get_multi([token_key, user_key])
		if valid_token and user:
			timestamp = int(time.mktime(valid_token.created.timetuple()))
			return user, timestamp
		return None, None

class Memory(ndb.Model):
	title = ndb.StringProperty(required=True)
	date = ndb.DateProperty(required=True)
	description = ndb.StringProperty(indexed=False, required=True)
	location = ndb.StringProperty(required=True)
	datetime = ndb.DateTimeProperty(auto_now_add=True, required=True)
	user_id = ndb.IntegerProperty(required=True)
	name = ndb.StringProperty(required=True)

class Basehandler(webapp2.RequestHandler):
	@webapp2.cached_property
	def auth(self):
		return auth.get_auth()

	@webapp2.cached_property
	def user_info(self):
		return self.auth.get_user_by_session()

	@webapp2.cached_property
	def user(self):
		u = self.user_info
		return self.user_model.get_by_id(u['user_id']) if u else None

	@webapp2.cached_property
	def user_model(self):
		return self.auth.store.user_model

	@webapp2.cached_property
	def session(self):
		return self.session_store.get_session(backend="datastore")

	def render_template(self, view_filename, params={}):
		user = self.user_info
		params	['user'] = user
		template = JINJA_ENVIRONMENT.get_template(view_filename)
		self.response.write(template.render(params))

	def dispatch(self):
		self.session_store = sessions.get_store(request=self.request)
		try:
			webapp2.RequestHandler.dispatch(self)
		finally:
			self.session_store.save_sessions(self.response)

def user_required(handler):
	def check_login(self, *args, **kwargs):
		auth = self.auth
		if not auth.get_user_by_session():
			self.redirect('/login')
		else:
			return handler(self, *args, **kwargs)

	return check_login

def user_redirect(handler):
	def check_login(self, *args, **kwargs):
		auth = self.auth
		if not auth.get_user_by_session():
			return handler(self, *args, **kwargs)
		else:
			self.redirect('/')

	return check_login

class MainPage(Basehandler):
	@user_required
	def get(self):
		memory_query= Memory.query(
			ancestor=pensieve_key()).order(-Memory.date)
		memories = memory_query.fetch()
		assortedmem = {}
		for memory in memories:
			if assortedmem.has_key(memory.date):
				assortedmem[memory.date].append(memory)
			else:
				assortedmem[memory.date] = [memory]

		memory_dict = {
			'assortedmem' : assortedmem,
			'host_url' : self.request.host_url
		}
		self.render_template('index.html', memory_dict)

class AddtoPensieve(Basehandler):
	@user_required
	def post(self):
		memory = Memory(parent=pensieve_key())
		memory.title = self.request.get('title')
		memory.date = datetime.strptime(self.request.get('date'), '%Y-%m-%d').date()
		memory.description = self.request.get('description')		
		memory.location = self.request.get('location')
		memory.user_id = self.user_info['user_id']
		memory.name = self.user_info['name']

		memory.put()
		self.redirect('/')

	def get(self):
		self.redirect('/')

class RemovefromPensieve(Basehandler):
	@user_required
	def post(self):
		id = self.request.get('id')
		if id is None:
			self.redirect('/')
		memory = Memory.get_by_id(int(id), parent=pensieve_key())
		memory.key.delete()
		self.redirect('/')

	def get(self):
		self.redirect('/')

class Form(Basehandler):
	@user_required
	def get(self):
		self.render_template('form.html')

class MemoryPermalink(Basehandler):
	@user_required
	def get(self):
		id = self.request.get('id')
		if id is None:
			self.redirect('/')
		memory = Memory.get_by_id(int(id), parent=pensieve_key());

		self.render_template('memory.html', {'memory': memory});

class UpdateMemory(Basehandler):
	@user_required
	def post(self):
		id = self.request.get('id');
		desc = self.request.get('desc')

		if id is None:
			self.redirect('/')
		memory = Memory.get_by_id(int(id), parent=pensieve_key());
		memory.description = str(desc)
		memory.put()
		self.redirect('/')

	def get(self):
		self.redirect('/')

class LogoutHandler(Basehandler):
	def get(self):
		self.auth.unset_session()
		self.redirect('/login')

class LoginHandler(Basehandler):
	@user_redirect
	def get(self):
		self.render_template('login.html')

	@user_redirect		
	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		print username, password
		try:
			u = self.auth.get_user_by_password(username, password, remember=True)
			self.redirect('/')
		except (auth.InvalidAuthIdError, auth.InvalidPasswordError) as e:
			self.redirect('/login')


class SignupHandler(Basehandler):
	@user_redirect
	def get(self):
		self.render_template('signup.html')

	@user_redirect
	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		name = self.request.get('name')

		unique_properties = None
		user_data = self.user_model.create_user(username,
			unique_properties,
			name=name,
			password_raw=password,
			verified=True)
		self.redirect('/login')


config = {
  'webapp2_extras.auth': {
	'user_model': 'webapp2_extras.appengine.auth.models.User',
	'user_attributes': ['name']
  },
  'webapp2_extras.sessions': {
	'secret_key': 'YOUR APPLICATION SECRET'
  }
}

application = webapp2.WSGIApplication([
	('/', MainPage),
	('/addmemory', Form),
	('/add', AddtoPensieve),
	('/remove', RemovefromPensieve),
	('/memory', MemoryPermalink),
	('/update', UpdateMemory),
	('/signup', SignupHandler),
	('/login', LoginHandler),
	('/logout', LogoutHandler),
],config=config,
 debug=False)