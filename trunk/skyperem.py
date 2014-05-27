# encoding: utf-8
"""
skypy.py

Created by Boris Braoude on 2011-07-21.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import Skype4Py
import random
import time
import feedparser
import codecs
from bs4 import BeautifulSoup
import urllib2
import oauth2
import twitter
import sched
import httplib2
import re
import types
import MySQLdb
import datetime

sk=Skype4Py.Skype() # Initializing Skype

file_chat_hash = codecs.open(os.path.normpath('/srv/petya_cred/chat_hash'),'r')
chat_hash = file_chat_hash.readline()

file_twi_consumer_key = codecs.open(os.path.normpath('/srv/petya_cred/twi_consumer_key'),'r','utf-8')
twi_consumer_key = file_twi_consumer_key.readline()

file_twi_consumer_secret = codecs.open(os.path.normpath('/srv/petya_cred/twi_consumer_secret'),'r','utf-8')
twi_consumer_secret = file_twi_consumer_secret.readline()

file_twi_access_token_key = codecs.open(os.path.normpath('/srv/petya_cred/twi_access_token_key'),'r','utf-8')
twi_access_token_key = file_twi_access_token_key.readline()

file_twi_access_token_secret = codecs.open(os.path.normpath('/srv/petya_cred/twi_access_token_secret'),'r','utf-8')
twi_access_token_secret = file_twi_access_token_secret.readline()

file_db_password=codecs.open(os.path.normpath('/srv/petya_cred/db_password'),'r','utf-8')
db_password=file_db_password.readline()

ppisyavr = sk.CreateChatUsingBlob(chat_hash)
twi = twitter.Api(consumer_key=twi_consumer_key.strip(),
consumer_secret=twi_consumer_secret.strip(),
access_token_key=twi_access_token_key.strip(),
access_token_secret=twi_access_token_secret.strip())

db = MySQLdb.connect(host="localhost",user="root",passwd=db_password.strip(),db="petya",charset='utf8')

delimiter = '-----------'
lastquoteid=1
messagecount = 0
questioncount = 50
global _boardmessage
switch = True
cupcakes=[]
someoneleft = False
leftHandle = ''
s = sched.scheduler(time.time, time.sleep) # Initializing scheduler
random.seed()

_answer = ''

SPECIAL_CHARS = {'&lsquo;': '\'', 
		'&rsquo;': '\'', 
		'&sbquo;': '\'',
		'&ldquo;': '\"',
		 '&rdquo;': '\"', 
		'&bdquo;': '\"', 
		'&lsaquo;': '<', 
		'&rsaquo;': '>',
		'&mdash;': '-',
		'&nbsp;': ' ',}

# Special chars handling for parsed webpage texts

test = 1

def db_query(sql):
	db.ping(True)
	cur = db.cursor()
	try:
		cur.execute(sql)
		db.commit()
	except:
		db.rollback()
	return cur

def http_headers(**headers):
    """
    Rename headers from "user_agent" like notation to traditional User-Agent one
    """
    return dict((('-'.join(map(str.capitalize,i.split('_'))),j) for i,j in headers.items()))

def statistics(chat): # Chat statistics module
	ss=''
	curtotal=db_query("select sum(stats_score) as total from stats")
	total=int(curtotal.fetchone()[0])
	curstat=db_query("select * from stats order by stats_score desc")
	for row in curstat.fetchall():
		fullname=row[0]
		score=row[2]
		lastseen=row[3]
		percentage=round(float(score)/total,4)*100
		ss+=fullname+'		'+str(score)+'		'+str(percentage)+"%		"+str(lastseen)+'\n'
	chat.SendMessage(ss)

def NextGet(chat): # Chat statistics module
	nextname = ''
	nextget=0
	nextleft = sys.maxsize
	curstat=db_query("select * from stats WHERE stats_lastseen > (DATE(NOW())-INTERVAL 1 MONTH) order by stats_score desc")
	for row in curstat.fetchall():
		fullname=row[0]
		score=int(row[2])
		if score<1000:
			continue
		nearestget=int(NearestGet(score))
		if nearestget - score < nextleft:
			nextleft = nearestget - score
			nextget = nearestget
			nextname = fullname
	chat.SendMessage(u'Следующий гет ' + str(nextget) + u' у ' + nextname + u' (осталось ' + str(nextleft) + ')')

def show_recent_rss(chat,url,links):	# Recent news RSS module
	feed = feedparser.parse(url)
	paragraph = ''

	
	for i in range(5):
		news = feed['items'][i]
		if links==1:
			paragraph += news.title + '\n' + news.link + '\n' + delimiter + '\n'
		elif links==0: 
			paragraph += news.title + '\n' + delimiter + '\n'
		elif links==-1:
			paragraph += news.body + '\n' + delimiter + '\n'
	if links==2:
		news = feed['items'][random.randrange(len(feed['items'])+1)]
		paragraph += news.description + '\n'
	chat.SendMessage(paragraph)	
	
def bach(chat):	# Richard Bach quotations module
	file = codecs.open(os.path.normpath('./res/bach.txt'),'r','utf-8')
	
	quotes = file.readlines()
	
	finalquote = quotes[random.randrange(len(quotes)-1)]+'\n'+u'Ричард Бах\n'
	chat.SendMessage(finalquote)
	
	file.close()
 	

def coelho(chat):	# Coelho quotations module
	file = codecs.open(os.path.normpath('./res/coelho.txt'),'r','utf-8')
	
	quotes = file.readlines()
	
	finalquote = quotes[random.randrange(len(quotes)-1)]+'\n'+u'Коэльо "Книга воина света"\n'
	chat.SendMessage(finalquote)
	
	file.close()
 	

def fetch_recipe(chat,full):	# Random recipe module
		
	recipe = urllib2.urlopen('http://www.cookstr.com/searches/surprise')
	soup = BeautifulSoup(recipe)
	title = soup.title.string
	url = recipe.geturl()
	
	if full:
		item = soup.find(True,"recipe_structure_headnotes")
		
		desc = item.nextSibling.string
		
		for key in SPECIAL_CHARS:
			
			desc = desc.replace(key, SPECIAL_CHARS[key])
		
		chat.SendMessage(title[11:]+'\n'+delimiter+'\n'+desc+'\n'+delimiter+'\n'+url)
		
	else:
		chat.SendMessage(title[11:]+'\n'+url)
		
def post_to_twitter(message):	# Post message to twitter module
	
	status = twi.PostUpdate(message)
	
def getlasttweets(chat,person):
	
	statuses = twi.GetUserTimeline(screen_name=person)
   	list =  [s.text for s in statuses]
	
	s =''
	for l in list[:5]:
		s += l + '\n' + delimiter + '\n'
	
	if person == 'toxal':
		s += u'я уже старый и больной и вообще'
	
	chat.SendMessage(s)
	
def whoiscupcake(chat,send):	# Shows who is the current cupcake
	
	prop = u'Сегодня пирожок Петенька.'
	chat.SendMessage(prop)
			
def whoispussycat(chat):	# Shows who is the current pussycat
	
	prop = u'Сегодня кот Елена.'
	
	chat.SendMessage(prop)
	
def addquote(chat,text,author):
	text=MySQLdb.escape_string(text.encode('utf8','replace'))
	db_query("insert into quotes (quotes_author,quotes_timestamp,quotes_text,quotes_tags,quotes_active) values ('%s',NULL,'%s','',1)" % (author,text))
	chat.SendMessage(u"Цитата добавлена.")
def who_quote(chat):
	quotecursor=db_query("select * from quotes where quotes_id="+str(lastquoteid))
	row=quotecursor.fetchone()
	handle=row[1]
	timestamp=row[2]
	for user in chat.Members:
		if (handle==user.Handle):
			fullname=user.FullName
			break
	if (fullname==''):
		fullname="хз кто"
	chat.SendMessage(u"Эту цитату добавил %s (%s)" % (fullname,str(timestamp)))
	
def checkdate(sc,chat):	# Cupcake update module
	
	whoiscupcake(chat,0)
	
	sc.enter(600, 1, checkdate, (sc,chat))
	
def increment(chat,text):
	
	message = text + ' = ' + text + ' + 1;'
	chat.SendMessage(message)

def whowascupcake(chat):	# Shows previous cupcakes
	
	chat.SendMessage(u'В связи со сложной обстановкой исполняющим обязанности пирожка является Петенька.')

def chgkaccess(chat):
	
	hour = time.localtime().tm_hour
	
	if (hour>=7 and hour<12) or (hour>=18 and hour<23):
		
		chgk(chat)
	else:
		chat.SendMessage(u'Наш элитный ЧГК клуб сейчас закрыт, валите в другой чят\n\nРасписание клуба: 7-12 и 18-23 по израильскому времени')
	
def chgkenabler(message):
	
	global switch

	mogisters = ['the7111401','med-a-lion','mentalpress']
	
	args = message.Body.split(None,1)
	
	if message.Chat == ppisyavr:
		
		if len(args)>1:
	
			if args[1] == u'вкл':

				if switch:
					message.Chat.SendMessage(u'все уже работает')
				else:
					if mogisters.count(message.FromHandle):
						switch = True
						message.Chat.SendMessage(u'Слушаю и повинуюсь, могистр!')
						message.Chat.SendMessage(u'ЧГК включен.')
			elif args[1] == u'выкл':
				if switch:
					if mogisters.count(message.FromHandle):
						switch = False
						message.Chat.SendMessage(u'Слушаю и повинуюсь, могистр!')
						message.Chat.SendMessage(u'ЧГК выключен.')
				else:
						message.Chat.SendMessage(u'уже выключено')
		else:
			if switch:
				#chgkaccess(message.Chat)
				chgk(message.Chat)
			else:
				message.Chat.SendMessage(u'хуй тебе, а не чгк')
				
	else:
		
		chgk(message.Chat)			
	
	

def chgk(chat):	# Fetches chgk question


	global _answer
	global questioncount
			 
	if _answer:
	
		chat.SendMessage(u'Ответ: ' + _answer)
		_answer = ''
	
	else:
		link = 'http://db.chgk.info/random/answers/types1/584026438/limit1'
		post = 'None'
		# link = 'http://db.chgk.info/random/answers/types1/584026438/limit1'
		# soup = BeautifulSoup(urllib2.urlopen(link))
		headers = http_headers(
            user_agent    = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; ru; rv:1.9.0.13) Gecko/2009073022 Firefox/3.0.13 (.NET CLR 3.5.30729)',
            host          = 'db.chgk.info',
            referer       = 'http://db.chgk.info',
            connection    = 'close',
            pragma        = 'no-cache',
            cache_control = 'no-cache',
            )

		conn = urllib2.Request(link, post, headers)
		soup  = BeautifulSoup(urllib2.urlopen(conn).read())
		problem = soup.find('div',attrs={'class':'random_question'})
		
#		f = open("output.txt" , "w")
#		f.write(problem.text.encode("utf-8", "replace"))
		
		que = re.search(u'(?<=Вопрос\s\d:).+(?=Ответ:)', problem.text , re.S)
		question = que.group(0)
			
		if type(re.search(u'Комментарий:', problem.text, re.S)) != types.NoneType:
			ans = re.search(u'(?<=Ответ:).+(?=Комментарий:)', problem.text , re.S)
			cmt = re.search(u'(?<=Комментарий:).+', problem.text , re.S)
			commentary = u"Комментарий: " + cmt.group(0)
		else:
			ans = re.search(u'(?<=Ответ:).+', problem.text , re.S)
			commentary = ""
			
		answer = ans.group(0)
		
		_answer = answer + '\n\n' + commentary	# _answer is global (to remember its state)
		chat.SendMessage(u'Вопрос:\n'+ delimiter + '\n' + question)

def displayfriends(chat):
	
	
	message = [friend.Handle for friend in sk.Friends]	

	chat.SendMessage('\n'.join(message))
			
		
def youtubeinfo(chat,link):	# Shows info on youtube clip
	
#	link = 'http://www.youtube.com/watch?v=KWoJ9L99bZc'
	
	link = 'http://' + link
	
	video = urllib2.urlopen(link)
	soup = BeautifulSoup(video)
	
	title = soup.find('meta',attrs={'name':'title'})['content']
	# views = soup.find(True, "watch-view-count").strong.string
	
	info = title + '\n'
	
	chat.SendMessage(info)
	
def imdbinfo(chat,link):	# Shows info on IMDb entry
	
	linkre = re.search('imdb\.com\/title\S+', link , re.S)
	thelink = linkre.group(0)
	thelink = 'http://' + thelink
	raw = urllib2.urlopen(thelink)
	soup = BeautifulSoup(raw)
	
	title = soup.find('meta',attrs={'name':'title'})['content']
	desc = soup.find('meta',attrs={'name':'description'})['content']
	
	info = title + '\n' + desc
	
	chat.SendMessage(info)
	

def youporninfo(chat,link):	# Shows info on youporn clip
	
	link = 'http://' + link
	
	video = urllib2.urlopen(link)
	soup = BeautifulSoup(video)
	
	title = soup.find('meta',attrs={'name':'description'})['content']
	
	chat.SendMessage(title.replace('Watch Free Porn. ',''))

def setrole(chat,handle,flag):
	
	#print handle
	#print chat.MemberObjects.count
	
	for user in chat.MemberObjects:
		print user.Handle
		print user
		if user.Handle == handle:
			myuser =  user
			
			if flag=='L':
				myuser.Role = 'LISTENER'
			elif flag=='M':
				myuser.Role = 'MASTER'
			elif flag=='U':
				myuser.Role = 'USER'
			break
			
def kick(chat, handle):
	
	chat.Kick(handle)
			
def add(chat, handle):
	
	chat.AddMembers(sk.User(handle))

def NearestGet(number):
	inputnumber = int(number)
	if inputnumber==0:
		return(1)
	lng = len(str(inputnumber))
	botb = pow(10,lng-1)
	drumsticks = "1"*lng if lng>2 else "111"
	getsteps = [int(drumsticks),5000]
	gets = []
	for getstep in getsteps:
		nearestget = 0
		while nearestget < inputnumber:
			print(str(nearestget))
			nearestget=nearestget+getstep
		gets.append(nearestget)

	return(min(gets))


def OnUserAuthorizationRequestReceived(User):
	
#	print User.BuddyStatus
#	print Skype4Py.budFriend
	
	User.BuddyStatus = Skype4Py.budPendingAuthorization
	
	if User.BuddyStatus == Skype4Py.budFriend:
		ppisyavr.SendMessage(u'У меня новый дружок - '+  User.FullName)
#	print "ok here is a new friend"

	
def OnMessageStatus(Message, Status):	# Handles incoming messages

	global someoneleft
	global leftHandle
	if Message.Chat != ppisyavr:
		return
	if someoneleft == True:

		Message.Chat.SendMessage(u'в гробу отоспишься!')
		
		someoneleft = False
	if Status == 'SENT':
		db_query(u"update stats set stats_score=stats_score+1, stats_lastseen=NULL where stats_handle='petrophilia'")
	if Status == 'RECEIVED':
		
		if Message.Type == Skype4Py.cmeLeft:
			pass			
		
		fullname=Message.FromDisplayName if Message.FromDisplayName!='' else Message.FromHandle
		db_query(u"insert into stats (stats_fullname,stats_handle,stats_score) values ('%s','%s',1) on duplicate key update stats_score=stats_score+1,stats_fullname='%s',stats_lastseen=NULL" % (fullname,Message.FromHandle,fullname))
		statcursor=db_query("SELECT stats_score from stats where stats_handle='%s'" % (Message.FromHandle))
		getscore=statcursor.fetchone()[0]
		drumsticks = "1"*len(str(getscore)) if len(str(getscore))>2 else "111"
		if (int(getscore)%5000 == 0) or (int(getscore)%int(drumsticks) == 0):
			Message.Chat.SendMessage(u'(dance) (party) ' + Message.FromDisplayName + ' ' + str(getscore) + u' гет! (party) (dance)' )
		if Message.Body == '!stat':
			statistics(Message.Chat)
		if (Message.Body == '!nextget') or (Message.Body == '!ng'):
			NextGet(Message.Chat)
		if (Message.Body == '!mynextget') or (Message.Body == '!mng'):
			nextget=int(NearestGet(getscore))
			Message.Chat.SendMessage(u'Следующий гет ' + fullname + ': ' + str(nextget) + u' (осталось ' + str(int(nextget)-int(getscore)) + ')')
		elif Message.Body == '!lenta':
			show_recent_rss(Message.Chat,'http://lenta.ru/rss/',0)
		elif Message.Body == '!news':
			show_recent_rss(Message.Chat,'http://static.feed.rbc.ru/rbc/internal/rss.rbc.ru/rbc.ru/newsline.rss',1)
		elif Message.Body == '!bash':
			show_recent_rss(Message.Chat,'http://bash.org.ru/rss/',-1)
		elif Message.Body == '!apple':
			show_recent_rss(Message.Chat,'http://feeds.macrumors.com/MacRumors-All',0)
		elif Message.Body == '!who':
			who_quote(Message.Chat)
		elif Message.Body == '!cook':
			fetch_recipe(Message.Chat,0)
		elif Message.Body == '!coook':
			fetch_recipe(Message.Chat,1)
		elif Message.Body == '!cupcake':
			whoiscupcake(Message.Chat,1)
		elif Message.Body == '!cupcakes':
			whowascupcake(Message.Chat)
		elif Message.Body.count('!quote'):
			addquote(Message.Chat,Message.Body[7:],Message.FromHandle)
		elif Message.Body.count('++'):
			increment(Message.Chat,Message.Body[:Message.Body.index('++')])
		elif Message.Body == '!pussycat':
			whoispussycat(Message.Chat)
		elif Message.Body.count(u'!чгк'):
			chgkenabler(Message)
		elif Message.Body == '!chess':
			global _boardmessage
			_boardmessage = chess.game(Message.Chat)
		elif Message.Body == '!undo':
			chess.undoturn(_boardmessage)
		elif Message.Body.count('!move'):
			chess.movepiece(_boardmessage,Message.Body[6:])
		elif Message.Body.count('!stfu'):
			setrole(Message.Chat,Message.Body[6:].split(None,1)[0],'L')
		elif Message.Body == '!friends':
			displayfriends(Message.Chat)
		elif Message.Body.count('!overthrow'):
			setrole(Message.Chat,Message.Body[11:].split(None,1)[0],'U')
		elif Message.Body.count('!promote'):
			setrole(Message.Chat,Message.Body[9:].split(None,1)[0],'M')
		elif Message.Body.count('!kick'):
			kick(Message.Chat, Message.Body[6:].split(None,1)[0])
		elif Message.Body.count('!add'):
			add(Message.Chat, Message.Body[5:].split(None,1)[0])
		elif Message.Body.count('!twi'):
			getlasttweets(Message.Chat,Message.Body[5:])
		elif (Message.Body.count('youtube.com/watch') or Message.Body.count('youtu.be/')):
			
			link1 = Message.Body.find('tube')
			link2 = Message.Body.find('tu.be')
			
			if link1 != -1:
				youtubeinfo(Message.Chat,Message.Body[link1-3:link1+28])
			else: 
				youtubeinfo(Message.Chat,Message.Body[link2-3:link2+17])
		
		elif Message.Body.count('youporn.com/watch'):
			
			link = Message.Body.find('youporn')
			
			youporninfo(Message.Chat,Message.Body[link:link+25])
		
		elif Message.Body.count('imdb.com/title'):
			
			imdbinfo(Message.Chat,Message.Body)
		
		elif ((Message.Body.count('[x]') or Message.Body.count(u'[х]')) and len(Message.Body.split())>1):
			post_to_twitter(Message.Body[:-3])
		
#		elif (Message.Body.count(u'искусств') or Message.Body.count(u'дискурс') or Message.Body == ')'):
#			Message.Chat.SendMessage(u'Ссу тебе в рот, ' + Message.FromDisplayName)
		
		elif (Message.Body.count(u'озвуч')):
			theword = re.search(u'озвуч\S+', Message.Body , re.S)
			thewordone = theword.group(0)
			Message.Chat.SendMessage(re.sub(u'озвуч', u'хуюч', thewordone))
		else: 
			
			global messagecount
			global lastquoteid
			if (messagecount == 50) or type(re.search(u'[Пп]ет.н', Message.Body, re.I|re.M)) != types.NoneType or type(re.search(u'[Пп]ет[яю]', Message.Body , re.I|re.M)) != types.NoneType:
				messagecount = 0
				quotecursor=db_query("SELECT quotes_id, quotes_text from quotes where quotes_active=1 order by rand() limit 1")
				row=quotecursor.fetchone()
				quoteid=row[0]
				quotetext=row[1]
				finalquote=quotetext.replace('username',Message.FromDisplayName)
				Message.Chat.SendMessage(finalquote)
				lastquoteid=quoteid
			else:
				messagecount+=1

def main():
	
	sk.Attach()	# Attaching to Skype client
	
	print 'Full Name: %s' % sk.CurrentUser.FullName
	print 'Skype Status:n %s' % sk.CurrentUser.OnlineStatus
	

	# ppisyavr.SendMessage('1')	

	sk.OnMessageStatus = OnMessageStatus
	sk.OnUserAuthorizationRequestReceived = OnUserAuthorizationRequestReceived
	
	
	# s.enter(600, 1, checkdate, (s,ppisyavr))	# Cupcake update scheduling
	s.run()
	

	
	while (True):		# Performs script execution every 2 seconds
			
			time.sleep(2)


if __name__ == '__main__':
	main()
	
	
