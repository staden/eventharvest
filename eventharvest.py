import tweepy
from tweepy import OAuthHandler
import twitter
import json
import urllib2

# Enter Twitter API credentials

ckey = ''
csecret = ''
atoken = ''
asecret = ''

auth = tweepy.OAuthHandler(ckey,csecret)
auth.set_access_token(atoken,asecret)

api = tweepy.API(auth)

# get 10 most recent earthquakes
results = api.user_timeline(screen_name='USGSted',count=10)

# create csvs with headers (for GIS)
outfile = open('epicenters.csv','w')
outfile.write('severity,lat,lng,datetime,url\n')
outfile.close()

outfile = open('eqtweets.csv','w')
outfile.write('city,country,lat,lng,count,tweets\n')
outfile.close()

for result in results:
    text = result.text


    # parse post
    ptext = text.split('\n')
    pdict = {}
    pdict['severity'] = str(ptext[0]).replace(',','')
    pdict['location'] = str(ptext[1]).replace(',','')
    pdict['datetime'] = str(ptext[2]).replace(',','')
    pdict['url'] = str(ptext[4])

    print pdict
    # follow url
    sock = urllib2.urlopen(pdict['url'])
    lines = sock.readlines()
    sock.close()


    # get lat/lng of epicenter
    check = 0
    for line in lines:
        if '<div class="nearby-cities">' in line:
            nearby_cities = line
        if 'Earthquake location' in line:
            ecstring = line.split('Earthquake location')[1].split('</a><a')[0]
            check = 1
    if check == 0:
        print 'no epicenter located'

    ec = ecstring.split(',')
    for e in ec:
        ec[ec.index(e)] = e.split('&')
    for e in ec:
        e[0] = float(e[0])
        if 'S' in e[1] or 'W' in e[1]:
            e[0] = e[0]*-1
    epicenter = {}
    epicenter['lat'] = ec[0][0]
    epicenter['lng'] = ec[1][0]
    
    
    # write epicenters.csv for GIS
    outfile = open('epicenters.csv','a')
    outfile.write('{0},{1},{2},{3},{4}\n'.format(pdict['severity'],epicenter['lat'],epicenter['lng'],pdict['datetime'],pdict['url']))
    outfile.close()

    # get nearby cities
    nearby_cities = nearby_cities.split('"')[3]

    sock = urllib2.urlopen(nearby_cities)
    data = json.load(sock)
    sock.close()

    cities = []
    citydict = {}    
    
    for city in data:
        c = city['name']
        cities.append(c)
        citydict[c] = {'lat':city['latitude'],'lng':city['longitude']}


    # query twitter for earthquake-related posts in this area
    auth = twitter.oauth.OAuth(atoken,asecret,ckey,csecret)
    twitter_api = twitter.Twitter(auth=auth)

    hits = []
    for city in citydict:
        results = twitter_api.search.tweets(q='temblor',count=10,result_type='recent',geocode=str(citydict[city]['lat'])+','+str(citydict[city]['lng'])+',10mi')
        citydict[city]['hits'] = len(results['statuses'])
        statuses = []
        for result in results['statuses']:
            statuses.append(result['text'])
        citydict[city]['statuses'] = statuses
        
        # write csv (for GIS)
        outfile = open('eqtweets.csv','a')
        outfile.write('{0},{1},{2},{3}\n'.format(city,citydict[city]['lat'],citydict[city]['lng'],citydict[city]['hits']))
        
    # export kml
    import simplekml
    kml = simplekml.Kml()

    ecpnt = kml.newpoint(name=pdict['severity'])
    ecpnt.coords = [(epicenter['lng'],epicenter['lat'])]
    ecpnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/pal4/icon47.png'

    
    for city in citydict:

        pnt = kml.newpoint(name=city)
        pnt.coords = [(citydict[city]['lng'],citydict[city]['lat'])]
        pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/road_shield3.png'
        
        line = kml.newlinestring(name='')
        if citydict[city]['hits'] == 0:
            line.coords = [(epicenter['lng'],epicenter['lat'],500),(citydict[city]['lng'],citydict[city]['lat'],500)] 
        if citydict[city]['hits'] >= 1 and citydict[city]['hits'] < 3:
            pnt.style.labelstyle.color = simplekml.Color.yellow
            line.style.linestyle.color = simplekml.Color.yellow
            line.coords = [(epicenter['lng'],epicenter['lat'],500),(citydict[city]['lng'],citydict[city]['lat'],500)] 
        if citydict[city]['hits'] >= 3 and citydict[city]['hits'] < 6:
            pnt.style.labelstyle.color = simplekml.Color.orange
            line.style.linestyle.color = simplekml.Color.orange
            line.coords = [(epicenter['lng'],epicenter['lat'],500),(citydict[city]['lng'],citydict[city]['lat'],500)] 
        if citydict[city]['hits'] >= 6:
            pnt.style.labelstyle.color = simplekml.Color.red
            line.style.linestyle.color = simplekml.Color.red
            line.coords = [(epicenter['lng'],epicenter['lat'],500),(citydict[city]['lng'],citydict[city]['lat'],500)]

        line.style.linestyle.width = 10
        line.altitudemode = simplekml.AltitudeMode.clamptoground
    #    line.extrude = 1
    
    kml.save('output'+str(pdict['location'])+'.kml')





