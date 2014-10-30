from bs4 import BeautifulSoup
from StringIO import StringIO
from selenium import webdriver
from pymongo import Connection
import urllib2
import chardet
import os, sys, gzip, re, random

# Wiley template

def get_html(init_page):
   req = urllib2.Request(init_page, headers={'User-Agent' : "Magic Browser"}) 
   html_init = urllib2.urlopen( req )
   if html_init.info().get('Content-Encoding') == 'gzip':
      buf = StringIO( html_init.read())
      f = gzip.GzipFile(fileobj=buf)
      data_html = f.read()
   else:
      data_html = html_init.read()
   code = chardet.detect(data_html)
   charset = code.get('encoding')
   if charset == None:
      init_soup = BeautifulSoup(data_html)
   else:
      init_soup = BeautifulSoup(data_html, from_encoding= charset)
   return init_soup

def get_article_links(init_soup, block_name):
   article_refs = []
   for article_header in init_soup.findAll('div', attrs={'class' : block_name}):
      article_refs.append('http://onlinelibrary.wiley.com'+ article_header.find('a').get('href'))
   return article_refs


basedomain = 'http://onlinelibrary.wiley.com/'

connection = Connection('localhost', 27017)
db = connection.journal
articles = db.articles

volume_link ='http://onlinelibrary.wiley.com/doi/10.1002/cbic.v15.13/issuetoc'
year = 2014
while not year == 2009:
   for _ in range(2):
      try:
         html_e = get_html(volume_link)
         year = str(html_e.find('h2', attrs={'class' : "noMargin"}).getText().split(' ')[1])
         prev_link = html_e.find('a', attrs={'class' : "previous"}).get('href')
         volume_link = basedomain+prev_link
         articles = get_article_links(html_e, "citation tocArticle")
         print html_e.find('h2', attrs={'class' : "noMargin"}).getText()
         for article_ref in articles:
            for _ in range(2):
               try:
                  html_art = get_html(article_ref)
                  Article_title = html_art.find('h1', attrs={'class' : "articleTitle"}).getText()
                  Article_type = html_art.find('p', attrs={'class' : "articleCategory"}).getText()
                  if Article_type == u'Cover Picture':
                     pass
                  else:
                     DOI = html_art.find('p', attrs={'id' : "doi"}).getText().replace('DOI:', '')
                     abst = html_art.find('div', attrs={'class' : "para"}).get_text(strip=True)
                     Authors = html_art.find('p', attrs={'id' : "citation"}).getText().split('(')[0].replace('.', '').encode("utf-8")
                     email_author = html_art.find('span', attrs={'class' : "email"}).getText()
                     corr_author = email_author.split('(')[0].replace('.', '')
                     corr_mail = email_author.split('(')[1].replace(')', '')
                     corr_aff = html_art.find('p', attrs={'id' : "correspondence"}).getText().replace('*', '').replace('===', '')
                     keyword = html_art.find('ul', attrs={'class' : "keywordList"}).getText().split(";")
                     Volume = html_art.find('p', attrs={'class' : "articleDetails"}).getText()
                     country = corr_aff.split('(')[1].split(')')[0]
                     Corr_author = {corr_author: [corr_mail, corr_aff, country]}
                     print Article_title
                     db.articles.insert( { 'Type': Article_type, 'Journal': 'Chemical Biology & Drug Design', 'Link':article_ref, 'Volume':Volume, 'Title':Article_title, 'DOI':DOI, 'Abstract':abst, 'Authors':Authors, 'corresponding_authors_info':Corr_author, 'keywords':keyword } )
                  break
               except Exception, ex: 
                  print repr(ex)
                  pass
         break 
      except Exception, ex: 
         print repr(ex)
         pass



