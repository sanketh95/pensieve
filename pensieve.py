import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2
import jinja2
from datetime import datetime
import calendar

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

DEFAULT_NAME = 'default_pensieve'

def unix_to_datetime(unix):
	return datetime.utcfromtimestamp(float(unix))

def datetime_to_unix(dtime):
	return calendar.timegm(dtime.timetuple())

def pensieve_key():
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Pensieve', DEFAULT_NAME)

class Memory(ndb.Model):
	title = ndb.StringProperty()
	date = ndb.StringProperty()
	description = ndb.StringProperty(indexed=False)
	location = ndb.StringProperty()
	datetime = ndb.DateTimeProperty(auto_now_add=True)

class MainPage(webapp2.RequestHandler):
    def get(self):
        memory_query= Memory.query(
        	ancestor=pensieve_key()).order(-Memory.date)
        memories = memory_query.fetch(10)
        assortedmem = {}
        for memory in memories:
        	if assortedmem.has_key(memory.date):
        		#print datetime_to_unix(memory.datetime)
        		assortedmem[memory.date].append((memory,datetime_to_unix(memory.datetime)))
        	else:
        		assortedmem[memory.date] = [(memory, datetime_to_unix(memory.datetime))]
        		print datetime_to_unix(memory.datetime)

        memory_dict = {
        	'assortedmem' : assortedmem,
        	'host_url' : self.request.host_url
        }
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(memory_dict))

class AddtoPensieve(webapp2.RequestHandler):
	"""docstring for Pensieve"""
	def post(self):
		memory = Memory(parent=pensieve_key())
		memory.title = self.request.get('title')
		memory.date = self.request.get('date')
		memory.description = self.request.get('description')		
		memory.location = self.request.get('location')

		memory.put()
		self.redirect('/')

	def get(self):
		self.redirect('/')

class RemovefromPensieve(webapp2.RequestHandler):
	def post(self):
		memories = Memory.query(Memory.datetime==datetime.strptime(self.request.get('datetime'), '%Y-%m-%d %H:%M:%S.%f')).fetch()
		for memory in memories:
			memory.key.delete()
		self.redirect('/')

	def get(self):
		self.redirect('/')

class Form(webapp2.RequestHandler):
	def get(self):
		template = JINJA_ENVIRONMENT.get_template('form.html')
		self.response.write(template.render())

class MemoryPermalink(webapp2.RequestHandler):
	def get(self):
		dtime = self.request.get('dtime')
		if dtime is None:
			self.redirect('/')
		memories = Memory.query(Memory.datetime==unix_to_datetime(dtime)).fetch()

		template = JINJA_ENVIRONMENT.get_template('memory.html')
		self.response.write(template.render({'memories': memories}))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/index.html', MainPage),
    ('/form', Form ),
    ('/form.html', Form),
    ('/add', AddtoPensieve),
    ('/remove', RemovefromPensieve),
    ('/memory', MemoryPermalink),
], debug=True)