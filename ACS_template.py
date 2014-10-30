from bs4 import BeautifulSoup
from selenium import webdriver
from pymongo import Connection
from pyvirtualdisplay import Display
import urllib2
import os, sys, random

# template for ACS journals

def get_article_links(init_soup, block_name):  #get links to articles from issue page
   main_block = init_soup.find('div', {'id' : block_name})
   article_refs = []
   for article_header in main_block.findAll('div', {'class' : "titleAndAuthor"}):
      article_refs.append(article_header.find('a').get('href'))
   return article_refs

def get_js_html(link_a):
   display = Display(visible=0, size=(800, 600)) #virtual display
   display.start()
   drivers = [webdriver.PhantomJS, webdriver.Firefox, webdriver.Chrome]  #choise of random webdriver 
   drive_eng = random.choice(drivers)()
   drive_eng.set_page_load_timeout(100) #timeout against webdriver freeze
   drive_eng.get(link_a)
   data_html = drive_eng.page_source
   js_soup = BeautifulSoup(data_html)
   drive_eng.quit()
   display.stop()
   return js_soup

connection = Connection('localhost', 27017)
db = connection.journal
articles = db.articles

basedomain = 'http://pubs.acs.org'
Vol = 2014
nextvolume = 'http://pubs.acs.org/toc/acbcct/9/9' # start page for web crowling (from last issue to stop year)

while not Vol == 2009:      #stop year
   for _ in range(2):
      try:
         os.system("kill $(ps aux | grep 'chrom' | awk '{print $2}')")
         os.system("kill $(ps aux | grep 'phantomjs' | awk '{print $2}')")
         os.system("kill $(ps aux | grep 'firefox' | awk '{print $2}')")            #kill webdrivers process
         html_e = get_js_html(nextvolume)
         Volumer = html_e.find('div', attrs={'id' : "date"}).getText()
         prev_vol_block = html_e.find('a', attrs={'class' : "previous"}).get('href')
         nextvolume = basedomain + prev_vol_block                                   #get link to previous volume
         articles_vol = get_article_links(html_e, "articleArea")
         Vol = int(Volumer.split(' ')[-1])                                          #get year of volume
         print Volumer
         for article_ref in articles_vol:
            for _ in range(3): #several attempts to get article soup if fail occurs
               try:
                  html_art = get_js_html(basedomain + article_ref)  
                  Article_title = html_art.find('h1', attrs={'class' : "articleTitle"}).getText()
                  DOI = html_art.find('div', attrs={'id' : "doi"}).getText().replace('DOI: ', '')
                  Abstract = html_art.find('p', attrs={'class' : "articleBody_abstractText"}).get_text(strip=True)
                  art_type =  html_art.find('div', attrs={'class' : "content-header series-content-header"}).find('h2').getText()      
                  break
               except: 
                  print 'Error article'
                  pass
            try:            #retriving author info block
               Authors = []
               Corr_author = {}
               auth_block = html_art.find('div', attrs={'id' : "authors"}) #list of authors
               mails = html_art.find('div', attrs={'id' : "correspondence"}).findAll('a') #list of mails
               affilations = html_art.find('div', attrs={'class' : "affiliations"}).findAll('div') #list of affilations
               for auth in auth_block.findAll('a', attrs={'id' : "authors"}):
                  Authors.append(auth.getText().replace('.', '')) #add author to list of authors
                  cor_link = auth_block.find(text=auth.getText()).findNext('a').get("href")
                  if cor_link[:4] == '#cor':  #get corresponding author
                     if auth.findNext('span', attrs={'class' : "NLM_xref-aff"}) != None: #relation between author, affilation and mail - case 1
                        auth_id = int(cor_link[-1])
                        mail_id = auth_id -1
                        corr_mail = mails[mail_id].getText()
                        aff_mark1 = auth.findNext('span', attrs={'class' : "NLM_xref-aff"}).getText()
                        for aff in affilations:
                           if aff.getText()[0] == aff_mark1:
                              corr_aff = aff.getText()[1:].replace('\n', ' ')
                              country = aff.getText().split(',')[-1].replace(' ', '', 1)
                           elif len(aff.findAll('sup')) > 1:
                              third_a = aff.find('span', attrs={'class' : "institution"}).getText() 
                              aff_list = aff.findAll(text=True)
                              country = aff.getText().split(',')[-1].replace(' ', '', 1)
                              for index, word in enumerate(aff_list):
                                 if word == aff_mark1:
                                    second_a = aff_list[index+1]
                                 if word == third_a:
                                    fourth_a = aff_list[index+1]
                              corr_aff = aff_list[0] + second_a + third_a + fourth_a
                        Corr_author.update({auth.getText().replace('.', '') : [corr_mail, corr_aff, country]})
                     elif auth.findNext('a', attrs={'href' : "#aff1"}) != None: #case 2
                        auth_id = int(cor_link[-1])
                        mail_id = auth_id -1
                        corr_mail = mails[mail_id].getText()
                        aff_mark1 = auth_block.find(text=auth.getText()).findNext('a').findNext('a').getText()
                        for aff in affilations:
                           if aff.getText()[0] == aff_mark1 and len(aff.findAll('sup')) == 1:
                              corr_aff = aff.getText()[1:].replace('\n', ' ')
                              country = aff.getText().split(',')[-1].replace(' ', '', 1)
                           elif len(aff.findAll('sup')) > 1:
                              third_a = aff.find('span', attrs={'class' : "institution"}).getText() 
                              aff_list = aff.findAll(text=True)
                              country = aff.getText().split(',')[-1].replace(' ', '', 1)
                              for index, word in enumerate(aff_list):
                                 if word == aff_mark1:
                                    second_a = aff_list[index+1]
                                 if word == third_a:
                                    fourth_a = aff_list[index+1]
                              corr_aff = aff_list[0] + second_a + third_a + fourth_a
                     elif len(mails) == 1 and len(affilations) ==1: #case3 - one corresponding author
                        corr_mail = mails[0].getText()
                        corr_aff = affilations[0].getText().replace('\n', ' ')
                        country = corr_aff.split(',')[-1].replace(' ', '', 1)       
                     Corr_author.update({auth.getText().replace('.', '') : [corr_mail, corr_aff, country]}) #update corresponding authors dict
               print Article_title #activity monitoring
               #Debug prints
               #print DOI
               #print art_type
               #print Corr_author
               #print Abstract
               #print Authors
               db.articles.insert( { 'Type':art_type, 'Journal': 'ACS Chemical Biology', 'Link':article_ref, 'Volume':Volumer, 'Title':Article_title, 'DOI':DOI, 'Abstract':Abstract, 'Authors':Authors, 'corresponding_authors_info':Corr_author, 'keywords':'none' } ) #insert article info in database
            except Exception, ex:
               print ex
               continue
         break
      except Exception, ex: 
         print ex
         pass
