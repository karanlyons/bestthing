#!/usr/bin/env python
# encoding: utf-8

import random
import string
import time

from flask import Flask, render_template, request, session

from bestthing.models import Thing, get_random_thing, get_rankings, calculate_score



app = Flask(__name__)
app.config.from_object('bestthing.config')

@app.route('/', methods=['GET', 'POST'])
def index():
	if request.method == 'POST':
		try:
			if request.form['csrf_token'] == session['csrf_token']:
				if 'add' in request.form.keys() and request.form['description'] != '':
					Thing(request.form['description']).save()
				
				elif request.form['thing1'] == session['thing1'] and request.form['thing2'] == session['thing2']:
					thing1 = Thing(session['thing1'])
					thing2 = Thing(session['thing2'])
					
					if '1' in request.form.keys():
						calculate_score(thing1, thing2)
					
					elif '2' in request.form.keys():
						calculate_score(thing2, thing1)
					
					thing1.save()
					thing2.save()
		
		except KeyError:
			pass
	
	session['thing1'] = session['thing2'] = get_random_thing()
	
	while session['thing1'] == session['thing2']:
		session['thing2'] = get_random_thing()
		
	session['csrf_token'] = ''.join(random.choice(string.letters) for i in xrange(32))
		
	return render_template('index.html', thing1=session['thing1'], thing2=session['thing2'], csrf_token=session['csrf_token'])


@app.route('/rankings/')
def rankings():
	return render_template('rankings.html', things=get_rankings())
