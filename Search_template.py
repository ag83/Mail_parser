from pymongo import Connection
import re

connection = Connection('localhost', 27017)
db = connection.journal

f = open("bromodomain.csv", "w") #file result

search = db.command("text", 'articles', search='bromodomain') #search key
result = search['results']
for res in result:
   if res['score'] > 0.8:   #score cutoff
      item = res['obj']
      title = item['Title']
      mails = item['corresponding_authors_info']
      for author, aff in mails.items():
         print title #activity monitor
         f.write("{0}; {1}; {2}; {3}".format(author.encode("UTF-8"), aff[0].encode("UTF-8"), aff[2].encode("UTF-8"), title.encode("UTF-8")))
f.close()

