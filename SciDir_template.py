from bs4 import BeautifulSoup
from StringIO import StringIO
from selenium import webdriver
from pymongo import Connection
from pyvirtualdisplay import Display
import urllib2
import chardet
import os, sys, gzip, re, random, gc

# template for Science Direct journals

def get_html(init_page):
   req = urllib2.Request(init_page, headers={'User-Agent' : "Magic Browser"}) 
   html_init = urllib2.urlopen( req )
   if html_init.info().get('Content-Encoding') == 'gzip': #get gnuzipped page
      buf = StringIO( html_init.read())
      f = gzip.GzipFile(fileobj=buf)
      data_html = f.read()
   else:
      data_html = html_init.read()
   code = chardet.detect(data_html) #detect encode of page
   charset = code.get('encoding')
   if charset == None:
      init_soup = BeautifulSoup(data_html)
   else:
      init_soup = BeautifulSoup(data_html, from_encoding= charset)
   return init_soup

def get_link_by_text(html_soup, link_text):
   link = html_soup.find('a', text= link_text)
   url = link.get('href')
   return url

def get_current_volume(soup_html, head_tag):
   header = soup_html.find(head_tag)
   items = []
   for i in str(header).split(' '):
      items.append(i)
   volume = [items[1].replace(',',''), items[-2], items[-1][:4]]
   return volume

def get_article_links(init_soup, block_name):  #get links to articles from issue page
   main_block = init_soup.find('div', {'id' : block_name})
   article_refs = {}
   for article_header in main_block.findAll('li', {'class' : "title "}): 
     try:
        art_type =  article_header.find('span', {'class' : "articleTypeLabel"}).getText()
        ref = article_header.find('a', {'class' : "cLink artTitle S_C_artTitle "}).get('href')
        article_refs.update({ref:art_type})
     except:
        continue
   return article_refs

def get_js_html(link_a):
   display = Display(visible=0, size=(800, 600))  #virtual display
   display.start()
   drivers = [webdriver.PhantomJS, webdriver.Firefox, webdriver.Chrome]  #choise of random webdriver 
   drive_eng = random.choice(drivers)()
   drive_eng.set_page_load_timeout(100)  #timeout against webdriver freeze
   drive_eng.get(link_a)
   data_html = drive_eng.page_source
   js_soup = BeautifulSoup(data_html)
   drive_eng.close()
   display.stop()
   return js_soup


connection = Connection('localhost', 27017) #connection to database
db = connection.journal
articles = db.articles

basedomain = 'http://www.sciencedirect.com'
Vol = 2014                                                                  #current year, initialisation
nextvolume = 'http://www.sciencedirect.com/science/journal/09680896/19/18'  # start page for web crowling (from last issue to stop year)

while not Vol == 2009:                                                      #stop year
   bashCommand = "rm -rf /tmp/*"
   os.system(bashCommand)
   os.system("kill $(ps aux | grep 'chrom' | awk '{print $2}')")
   os.system("kill $(ps aux | grep 'phantomjs' | awk '{print $2}')")
   os.system("kill $(ps aux | grep 'firefox' | awk '{print $2}')")          #kill webdrivers process
   for _ in range(3):
      try:
         html_e = get_html(nextvolume)
         first_page_e = html_e.find(attrs={'class' : 'volumeHeader'})
         Volumer = get_current_volume(first_page_e, 'h2')
         prev_vol_block = html_e.find(id="volumeIssueData")
         articles_vol = get_article_links(html_e, 'bodyMainResults')        #get link to previous volume
         Vol = int(Volumer[-1])
         print Volumer                                                      #volume info print
         for article_ref, atype in articles_vol.items():
            for _ in range(3):                                              #several attempts to get article soup if fail occurs
               try:
                  Art_type = atype
                  html_art = get_js_html(article_ref)
                  Article_title = html_art.find('h1', attrs={'class' : "svTitle"}).getText()
                  DOI = html_art.find('span', attrs={'class' : "S_C_ddDoi"}).getText().replace('DOI: ', '')
                  abst = html_art.find('div', attrs={'data-etype' : "ab"}).get_text(strip=True).replace('Abstract', '')
                  sh = re.compile(r'<[^>]+>')
                  Abstract = sh.sub('', abst)       #remove html tags from abstract text
                  break
               except: 
                  print 'Error article'
                  pass
            try:         #author info
               Authors = []
               Corr_author = {}
               for it in html_art.findAll('li', attrs={'class' : "smh5"}): #find all authors in article
                  if it.find('a', attrs={'class' : "auth_mail"}) is not None: #find corresponding authors
                     authors_info = []
                     corr_mail = it.find('a', attrs={'class' : "auth_mail"}).get('href').replace('mailto:', '') #get mail
                     if corr_mail is None:
                        authors_info.append('no_mail')
                     else:
                        authors_info.append(corr_mail)
                     aff = it.find('a', attrs={'class' : "intra_ref auth_aff"}) #case1 - affilation link
                     if aff is None:
                        aff = it.find('a', attrs={'class' : "intra_ref auth_corr"}) #case2 - affilaton link
                     link_aff = aff.get('href')[1:]
                     if link_aff == 'cor1': #if one affilation
                        link_aff = 'aff1'
                     affilation = html_art.find('ul', attrs={'class' : "affiliation authAffil smh"}).find('li', attrs={'id' : link_aff}) #case1 affilation
                     if affilation is None:
                        affilation = html_art.find('ul', attrs={'class' : "affiliation authAffil smh"}) #case2 - affilation
                     if affilation.getText()[0] == " ": #remove first space
                        affilat = affilation.getText()[0:]
                     elif affilation.getText()[0] in ["a", "b", "c", "d"]: #remove first sup
                        affilat = affilation.getText()[1:]
                     authors_info.append(affilat)
                     country = affilat.split(",")[-1]
                     if country is None:
                        authors_info.append('no_country')
                     else:
                        if country[0] == " ":
                           country = country[1:]
                     authors_info.append(country)
                     Corr_author.update({it.find('a', attrs={'class' : "authorName"}).getText().replace('.', ''):authors_info})
                  Authors.append(it.find('a', attrs={'class' : "authorName"}).getText().replace('.', '').encode("utf-8"))
               Volume = html_art.find('p', attrs={'class' : "volIssue"}).getText()
               print Article_title   #activity monitoring
               keyword = html_art.find('ul', attrs={'class' : "keyword"}).getText().split("; ")
               db.articles.insert( { 'Type': Art_type, 'Journal': 'Bioorganic & Medicinal Chemistry', 'Link':article_ref, 'Volume':Volume, 'Title':Article_title, 'DOI':DOI, 'Abstract':Abstract, 'Authors':Authors, 'corresponding_authors_info':Corr_author, 'keywords':keyword } )#database update
            except Exception, ex:
               print repr(ex)
               continue
         nextvolume = basedomain+get_link_by_text(prev_vol_block, re.compile('Previous vol/iss')) #next volume link
         break
      except Exception, ex: 
         print repr(ex)
         pass
