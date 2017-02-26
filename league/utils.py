# library of useful fonctions

from bs4 import BeautifulSoup
import requests
import re
import datetime

def check_byoyomi(s):
	# check if a string is a correct byo-yomi time: at least '3x30 byo-yomi'
	# We don't have settings for that... for now
	if s.find('byo-yomi') == -1 :
		return False
	else :
		a = s.find('x')
		n = int(s[0:a])
		b =s.find(' ')
		t = int(s[a+1:b])
	return n >= 3  and t >= 30

def sum_digits(n):
	#sum the digits of a number.
	#since win grant 10 and loss 1, this sum is the # of games played between 2 oponents
	s=0
	while n!=0:
		s += n % 10
		n /= 10
	return s

def extract_players_from_url(url):
	#get players name from a kgs archive url
	#'http://files.gokgs.com/games/Year/month/day/white-black-d*.sgf'

	# first we check wether it's a kgs archive link
	#otherwise we could populate with dumb data
	#Note: I am not proud of the way I handle error/exception where the url is not proper
	# Feel free to correct me here

	if url.startswith('http://files.gokgs.com/games/'):
		start = url.rfind('/') +1
		if start !=0 : # if rfind returned -1, it's no good
			w_end = url.find('-',start)
			white = url[start:w_end]
			b_end = url.find('-',w_end+1)
			if b_end !=-1: #there is a -d at the end of the url (players play mutliples times)
				black = url[ w_end+1 : b_end]
			elif url.find('.',w_end+1) != -1:
				b_end = url.find('.',w_end+1)
				black = url[ w_end+1 : b_end]

		return {'white':white,'black':black} #if unproper url, black is not define


def ask_kgs(kgs_username,year,month):
	# return a list of dic: { urlto, game_type} of games for the selected user, year and month
	# We have to check game_type here because it's not in the sgf but only on kgs website
	# Do not perform any check on players or whatever.

	if len(str(month)):
		month='0'+str(month)
	url = 'https://www.gokgs.com/gameArchives.jsp?user=' + str(kgs_username) + '&year=' + str(year) + '&month='+ str(month)
	r = requests.get(url)
	t = r.text
	soup=BeautifulSoup(t,"html5lib")
	#old method that just get the links to games
	#we need type too to exclude reviews :(
	#la = soup.find_all(href=re.compile('^http://files.gokgs.com/games/'))

	trs=soup.table.find_all('tr')
	l=[]
	for tr in trs[1:]:
		tds=tr.find_all('td')
		if tds[0].a.get_text()=='Yes':
			url = tds[0].a.get('href')
			#crappy way to detect if a game is a review the #of row in the table... :(
			if len(tds)==6 : #it's a review !
				game_type = 'review'
			else:
				game_type = tds[5].get_text()
			l.append({'url':url,'game_type': game_type})

	return l

def parse_sgf_string(sgf_string):
	#parse a sgf from a string and return a dict:
	#bplayer,wplayer,time,byo,result,handi,komi,size,rule,date,place

	#First remove all espaces and new lines from the sgf
	sgf_string=sgf_string.replace(chr(160),'').replace(chr(10),'').replace(chr(13),'')
	prop= {
		'DT' : 'date',
		'RE' : 'result',
		'PB' : 'bplayer',
		'PW' : 'wplayer',
		'KM' : 'komi',
		'HA' : 'handicap',
		'SZ' : 'board_size',
		'TM' : 'time',
		'OT' : 'byo',
		'PC' : 'place'
	}
	out={}
	for key in prop:
		p = sgf_string.find(key+'[') #find the key and get the index
		if p != -1 :
			q = sgf_string.find(']',p) #find the end of the tag
			out[prop[key]]=sgf_string[p+3:q]
	#convert string date to date object
	if 'date' in out:
		out['date']=datetime.datetime.strptime(out['date'],"%Y-%m-%d")
	else:
		 out['date']=None
	return out
