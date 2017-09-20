#The MIT License (MIT)
#
#Copyright (c) 2017 Peterfdej
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

# Record_peri.py is a simple Python script for recording live Periscope scopes of users stored in a csv file.
# Put record_peri.py and the cvs file in the same directory. Recordings will also be stored in that directory.
# Advice: max 10 users in csv.
# You can run record-peri.py multiple times, when you create multiple directories, each with his own
# record_peri.py and csv file.
# It is possible te edit the csv file while record_peri.py is running.
# Use Notepad++ for editing.
# Format csv: abc123:p,johndoe:p,xyzxx:t
# p = Periscope account name (user uses Pericope to stream)
# t = Twitter account name (user uses Twitter to stream)
#
# Requirements:	- Python 3
#				- ffmpeg
#
# Usage: 	python record_peri.py (non converting to mp4)
#			python record_peri.py -c (Recordings will be converted to mp4 after ending broadcast)

from bs4 import BeautifulSoup
import sys, time, os, getopt, csv
import os.path
import subprocess
import json
import urllib.request, urllib.error

PERISCOPE_URL = 'https://www.pscp.tv/'
TOKEN_URL = 'https://api.periscope.tv/api/v2/getAccessPublic?token='
TWITTER_URL = 'https://twitter.com/'

broadcastdict = {}
deleteuser = []
p = {}
p1 = {}

convertmp4 = 1
print ("Recordings will be converted to mp4 after ending broadcast.")
username = sys.argv[1]
filename = sys.argv[2]


if os.name == 'nt':
	FFMPEG = 'ffmpeg.exe'
else:
	FFMPEG = 'ffmpeg'
	
def file_size(fname):
        statinfo = os.stat(fname)
        return statinfo.st_size

def get_live_broadcast(user, usertype):
	req = urllib.request.Request(PERISCOPE_URL + user)
	try:
		response = urllib.request.urlopen(req)
		r = response.read()
		soup = BeautifulSoup(r, 'html.parser')
		page_container = soup.find(id='page-container')
		data_store = json.loads(page_container['data-store'])
		broadcasts = data_store['BroadcastCache']['broadcasts']
		if not broadcasts:
			live_broadcast = {}
		else:
			for key in broadcasts:
				broadcast = broadcasts[key]
				if broadcast['broadcast']['state']== 'RUNNING':
					live_broadcast = broadcast['broadcast']['data']
					break
				else:
					live_broadcast = {}	
	except urllib.error.URLError as e:
		res = e.reason
		if res == 'Not Found' and usertype == 'p':
			live_broadcast = {'user_id': ['unknown']}
		elif res == 'Not Found' and usertype == 't':
			live_broadcast = {}
		else:
			#unknown error
			print('URLError: ',e.reason)
			live_broadcast = {'user_id': ['skip']}
	return live_broadcast
	
def get_HLSURL(id):
	req = urllib.request.Request(TOKEN_URL + str(id))
	try:
		response = urllib.request.urlopen(req)
		r = response.read()
		soup = BeautifulSoup(r, 'html.parser')
		data_store = json.loads(str(soup))
		get_HLSURL = data_store['https_hls_url']
	except urllib.error.URLError as e:
		print("URLError: ",e.reason)
		get_HLSURL = {}
	return get_HLSURL

def rec_ffmpeg(broadcast_id, input, output):
	command = [FFMPEG,'-i' , input,'-y','-acodec','mp3','-loglevel','0', output]
	p[broadcast_id]=subprocess.Popen(command)
	broadcastdict[broadcast_id]['recording'] = 1
	time.sleep(1)
	
def convert2mp4(broadcast_id, input):
	if convertmp4 == 1:
		output = input.replace('.mkv','.mp4')
		command = [FFMPEG,'-i' , input,'-y','-loglevel','0', output]
		p1[broadcast_id]=subprocess.Popen(command)
	
run = True
while run:
	print ('*--------------------------------------------------------------*')
	deleteuserbroadcast = []
	usernames = [username]
	for user in usernames:
		usershort = user
		usertype = "p"

		# Here was check Twitter/Peri

		print ((time.strftime("%H:%M:%S")),' Polling Peri account   :', usershort)
		live_broadcast = get_live_broadcast(usershort, usertype)

		if live_broadcast:
			if live_broadcast['user_id'] == ['unknown']:
				# user does not exists anymore
				# extra loop to be sure
				if user in deleteuser:
					usernames.remove(user)
					deleteuser.remove(user)
					print ('Delete user: ', usershort)
				else:
					deleteuser.append(user)
					print ('Loop delete user: ', usershort)
				run = False
			elif live_broadcast['user_id'] == ['skip']:
				#skip user loop
				print ('HTTP request error. Skip user: ', usershort)
				run = False
			else:
				broadcast_id = live_broadcast['id']
				if broadcast_id not in broadcastdict :
					print ('New scope of user: ', usershort)
					broadcastdict[broadcast_id] = {}
					broadcastdict[broadcast_id]['user'] = usershort
					broadcastdict[broadcast_id]['state']= 'RUNNING'
					broadcastdict[broadcast_id]['time']= time.time()
					broadcastdict[broadcast_id]['filename']= filename
					broadcastdict[broadcast_id]['filesize']= 0
					broadcastdict[broadcast_id]['lasttime']= 0
					broadcastdict[broadcast_id]['recording']= 0

					print ('Start recording for: ', usershort)
					URL = get_HLSURL(broadcast_id)
					rec_ffmpeg(broadcast_id, URL, broadcastdict[broadcast_id]['filename'] )
					time.sleep(1)
					if os.path.exists(broadcastdict[broadcast_id]['filename']):
						print ('Recording started for: ', usershort, '-', broadcast_id)
					else:
						p[broadcast_id].terminate()

					if not os.path.exists(broadcastdict[broadcast_id]['filename']):
						print ('No recording file created for: ', usershort, 'file: ', broadcastdict[broadcast_id]['filename'])
						deleteuserbroadcast.append(broadcast_id)
	for broadcast_id in broadcastdict:
		#check if recording is running
		if p[broadcast_id].poll() == 0:
			broadcastdict[broadcast_id]['state'] = 'ENDED'
			deleteuserbroadcast.append(broadcast_id)
			run = False
		else:
			print ('Running ',round(time.time()- broadcastdict[broadcast_id]['time']), 'seconds: ', broadcastdict[broadcast_id]['filename'])
			#compare file size every 60 seconds
			if os.path.exists(broadcastdict[broadcast_id]['filename']) and broadcastdict[broadcast_id]['state'] == 'RUNNING':
				if broadcastdict[broadcast_id]['filesize'] < file_size(broadcastdict[broadcast_id]['filename']) and (time.time() - broadcastdict[broadcast_id]['lasttime']) > 60:
					broadcastdict[broadcast_id]['filesize'] = file_size(broadcastdict[broadcast_id]['filename'])
					broadcastdict[broadcast_id]['lasttime']= time.time()
				elif file_size(broadcastdict[broadcast_id]['filename']) == broadcastdict[broadcast_id]['filesize'] and (time.time() - broadcastdict[broadcast_id]['lasttime']) > 60:
					p[broadcast_id].terminate()
					time.sleep(2)
					broadcastdict[broadcast_id]['state'] = 'ENDED'
					deleteuserbroadcast.append(broadcast_id)
	#end recording, delete entry in broadcastdict and convert mkv -> mp4
	for broadcast_id in deleteuserbroadcast:
		p[broadcast_id].terminate()
		print ('End recording for: ', broadcastdict[broadcast_id]['user'])
		if broadcast_id in broadcastdict:
			convert2mp4(broadcast_id, broadcastdict[broadcast_id]['filename'])
			del broadcastdict[broadcast_id]
	time.sleep(1)
