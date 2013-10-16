#!/usr/bin/python
import ospi

  #### Add any new page urls here ####
ospi.urls.extend(['/c1', 'ospi_addon.custom_page_1']) # example: (['/c1', 'ospi_addon.custom_page_1', '/c2', 'ospi_addon.custom_page_2', '/c3', 'ospi_addon.custom_page_3'])

  #### add new functions and classes here ####
  ### Example custom class ###
class custom_page_1:
   """Add description here"""
   def GET(self):
      custpg = '<!DOCTYPE html>\n'
      #Insert Custom Code here.
      custpg += '<body>Hello form an ospi_addon program!</body>'
      return custpg



  
