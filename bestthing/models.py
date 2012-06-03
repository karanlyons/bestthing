#!/usr/bin/env python
# encoding: utf-8

import random
import re

import redis

import config as _config
from typogrify import force_unicode, typogrify



class app:
	"""
	A proxy to expose app.config to modules.py.
	
	(This is silly.)
	
	"""
	config = dict()
	
	for key in dir(_config):
		if key.isupper():
			config[key] = getattr(_config, key)


class Redis:
	"""
	Exposes a connection to redis, for use with our models and helpers.
	
	"""
	server = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_SOCKET'], db=app.config['REDIS_DB'], password=app.config['REDIS_PASSWORD'], socket_timeout=app.config['REDIS_SOCKET_TIMEOUT'], connection_pool=app.config['REDIS_CONNECTION_POOL'], charset=app.config['REDIS_CHARSET'], unix_socket_path=app.config['REDIS_SOCKET'])
	pipe = server.pipeline()


def escape(text):
	"""
	Escapes input by replacing > and < with their html escape codes. Also
	removes extraneous whitespace.
	
	"""
	text = force_unicode(text)
	text = re.sub(ur'>', u'&gt;', text)
	text = re.sub(ur'<', u'&lt;', text)
	text = re.sub(ur'\s+', u' ', text)
	text = re.sub(ur'^\s*|\s*$', u'', text)
	
	return text


class Thing(object):
	"""
	A thing. Any thing. Could be your thing.
	
	"""
	def __init__(self, description):
		self.description = typogrify(escape(description[0:250])) # Well, so long as your thing takes up less than 250 bytes.
		self.key = 'thing:%s' % self.description
		
		if Redis.server.zscore('things:score', self.description) is not None:
			self.better, self.worse, self.score = Redis.pipe.hget(self.key, 'better').hget(self.key, 'worse').zscore('things:score', self.description).execute()
			
			self.better = int(self.better)
			self.worse = int(self.worse)
			self.total_votes = self.better + self.worse
			self.score = float(self.score)
			
		else:
			self.better = 0
			self.worse = 0
			self.total_votes = 0
			self.score = float(0)
			
			self.save()
	
	def save(self):
		Redis.pipe.hset(self.key, 'better', self.better)
		Redis.pipe.hset(self.key, 'worse', self.worse)
		Redis.pipe.zadd('things:score', self.score, self.description)
		
		Redis.pipe.execute()


def get_random_thing():
	"""
	Returns the description of a random thing.
	
	"""
	things_number = Redis.server.zcard('things:score')
	rank = random.randint(0, things_number)
	
	try:
		return Redis.server.zrange('things:score', rank, rank)[0]
	
	except IndexError: # You fool!
		for thing in ['Freshly baked bread', 'Petrichor', 'Kittens', 'Gummy bears', 'Puppies', 'Bill Murray', 'Glockenspiels', 'Lego', 'Space']:
			Thing(thing).save()
		
		return get_random_thing()


def calculate_score(winning_thing, losing_thing):
	"""
	Calculates new (sort of) ELO scores for things.
	
	"""
	odds = 1 / (1 + ((10 ** (winning_thing.score - losing_thing.score * -1)) / 400))
	
	if winning_thing.score >= 2400: # I really don't like that these are hardcoded.
		k_value = 16
	if winning_thing.score >= 2100:
		k_value = 24
	else:
		k_value = 32
	
	new_winning_thing_score = winning_thing.score + (k_value * (1 - odds))
	losing_thing.score = max(losing_thing.score - (new_winning_thing_score - winning_thing.score), 0)
	winning_thing.score = new_winning_thing_score


def get_rankings(number=20):
	"""
	Returns a number of things, in order from best to worst.
	
	"""
	return Redis.server.zrevrange('things:score', 0, number - 1)
