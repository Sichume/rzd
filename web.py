#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import cgi, os

from google.appengine.api import users
from time import sleep
from httplib import HTTPException, HTTPConnection
import webapp2, httplib
import urllib, urllib2, cookielib, json
from autocomplete import getMainPage

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

def getResponse(url):
  good = False
  while not good:
    try:
      resp = opener.open(url, timeout=5)
      if resp.getcode() in [httplib.OK, httplib.CREATED, httplib.ACCEPTED]:
        good = True
    except (urllib2.HTTPError, HTTPException):
      pass
  return resp.read()

def getResponseStub(url):
  r = json.loads(getResponse(url))
  cnt = 0
  while (r['result']!='OK' and cnt < 5):
    sleep(1)
    cnt+=1
    r = json.loads(getResponse(url))
  return r

def getCityId(city, s):
  req = 'http://pass.rzd.ru/suggester?lang=ru&stationNamePart=' + urllib.quote(city.encode('utf-8'))
  respData = getResponse(req)
  rJson = json.loads(respData)
  for item in rJson:
    if item['name'].lower() == city.lower():
      s.response.out.write(u'Найден: '+item['name']+' -> '+str(item['id'])+'<br>')
      return str(item['id'])
  s.response.out.write(u'Не найден: '+city+'<br>')
  s.response.out.write(u'Выбранный вами город не найден, попробуйте найти в списке и ввести еще раз:<a href="../">Вернуться</a><br>')
  for item in rJson:
    s.response.out.write(item['name']+'<br>')
  return None

def getRidSid(st0, st1, date, s):
  username = 'user'
  password = 'pass'
  login_data = urllib.urlencode({'j_username' : username, 'j_password' : password, 'action' : 'Вход'})

  """
  good = False
  while not good:
    try:
      opener.open('https://pass.rzd.ru/ticket/j_security_check', login_data)
      good = True
    except urllib2.HTTPError, e:
      s.response.out.write('fail')
      cj.clear_session_cookies() 
  """

  id0 = getCityId(st0, s)
  id1 = getCityId(st1, s)

  st0 = urllib.quote(st0.encode('utf-8'))
  st1 = urllib.quote(st1.encode('utf-8'))

  if (not id0 or not id1):
    return
  
  req1 = 'http://pass.rzd.ru/timetable/public/ru?STRUCTURE_ID=735&layer_id=5371&dir=0&tfl=3&checkSeats=1&\
st0='+st0+'&code0='+id0+'&dt0='+date+'&st1='+st1+'&code1='+id1+'&dt1='+date

  r = json.loads(getResponse(req1))
  if (r['result']=='OK'):
    s.response.out.write(r['tp'][0]['msgList'][0]['message']) #errType
    s.response.out.write('<br>')
    #s.response.out.write(r)
    return
  sid = str(r['SESSION_ID'])
  rid = str(r['rid'])
  req2 = 'http://pass.rzd.ru/timetable/public/ru?STRUCTURE_ID=735&layer_id=5371&dir=0&tfl=3&checkSeats=1&\
st0='+st0+'&code0='+id0+'&dt0='+date+'&st1='+st1+'&code1='+id1+'&dt1='+date+'&rid='+rid+'&SESSION_ID='+sid

  r = getResponseStub(req2)
  
  out = '<html><body><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
  if ('tp' in r):
    out += r['tp'][0]['from'] + '<br>'
    out += r['tp'][0]['where'] + '<br>'
    out += r['tp'][0]['date'] + '<br>'
    l_trains = r['tp'][0]['list']
    #print l_trains
    for train in l_trains:
      out += '**************************************************<br>'
      out += u'станция отправления: ' + train['station0'] + '<br>'
      out += u'станция прибытия: ' + train['station1'] + '<br>'
      out += u'время в пути: ' + train['timeInWay'] + '<br>'
      out += u'время отправления: ' + train['time0'] + '<br>'
      out += u'время прибытия: ' + train['time1'] + '<br>'
      out += u'номер поезда: ' + train['number'] + '<br>'
      for car in train['cars']:
        out += '---------------------<br>'
        out += u'тип: ' + car['typeLoc'] + '<br>'
        out += u'свободных мест: ' + str(car['freeSeats']) + '<br>'
        out += u'цена: ' + str(car['tariff']) + '<br>'
        out += '---------------------<br>'
  else:
    out += "Some error occured: " + s.response.out.write(r)

  s.response.out.write(out)


class MainPage(webapp2.RequestHandler):
  def get(self):
    getMainPage(self)

def getProperDate(date):
  items = date.split('/')
  return ('%s.%s.%s' % (items[1], items[0], items[2]))

class TrainListPage(webapp2.RequestHandler):
    def post(self):
        self.response.out.write('<html><body>Нашли:<pre>')
        st0  = cgi.escape(self.request.get('from'))
        st1  = cgi.escape(self.request.get('to'))
        date = getProperDate(cgi.escape(self.request.get('date')))
        
        getRidSid(st0, st1, date, self)
        self.response.out.write('</pre></body></html>')

class SuggesterPage(webapp2.RequestHandler):

    def get(self):
        try:
            first = self.request.get('lang')
            station = self.request.get('stationNamePart')

            req='http://pass.rzd.ru/suggester?lang=ru&stationNamePart='+urllib.quote(station.encode('utf-8'))
            respData = getResponse(req)
            rJson = json.loads(respData)
            sOut = '['
            cnt = 1
            sStations = set()
            for item in rJson:
              if item['name'] not in sStations:
                sStations.add(item['name'])
            lStations = self.sort4Find(sStations, station.lower())
            for item in lStations:
                sOut += '{\"id\":\"'+str(cnt)+'\",\"label\":\"'+item+'\",\"value\":\"'+item+'\"},'
                cnt += 1
            sOut = sOut[:-1]
            sOut += ']'
            self.response.out.write(sOut)

        except (TypeError, ValueError):
            self.response.out.write("<html><body><p>Invalid inputs</p></body></html>")

    def sort4Find(self, sStations, suggest):
      l0 = []
      l1 = []
      for station in sStations:
        if station.lower().find(suggest) == 0:
          l0.append(station)
        else:
          l1.append(station)
      return l0 + l1


class ThemesPage(webapp2.RequestHandler):

    def get(self, name):
        try:
            self.response.out.write(open(os.getcwd()+'/themes/'+name, 'rb').read())
        except (TypeError, ValueError):
            self.response.out.write("<html><body><p>Invalid inputs</p></body></html>")

class TestPage(webapp2.RequestHandler):

    def get(self):
        resp = opener.open('http://pass.rzd.ru/suggester?lang=ru&stationNamePart=%D0%BC%D0%BE%D1%81')
        self.response.out.write(resp.read())

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/trains', TrainListPage),
    ('/suggester', SuggesterPage),
    ('/themes/(.*)', ThemesPage),
    ('/test', TestPage)
], debug=True)

def main():
    application.run()

if __name__ == "__main__":
    main()