# import pytesseract
import easyocr
import pandas as pd
import numpy as np
from PIL import Image
import os 
import requests
import re
import streamlit as st 
import io
import  psycopg2

def readtext(img_list):    
    for img in img_list:
        data = Image.open(img)
        dft = np.array(data)
        reader = easyocr.Reader(['en'])
        result = reader.readtext(dft, detail=0)       
    return result,data


def extracted_info(results):  
 
  info={'Name': [], 'Designation': [], 'Company name': [], 'Contact': [], 'Email': [], 'Website': [],
                'Address': [], 'Pincode': []}
  for i in range(len(results)):
    if results[i]==results[0]:
      info['Name'].append(results[i])
    elif results[i]==results[1]:
      info['Designation'].append(results[i])
    elif results[i].startswith('+') or (results[i].replace('-', '').isdigit() and '-' in results[i]):
      info['Contact'].append(results[i])
    elif '@' in results[i] and '.com' in results[i]:
      small = results[i].lower()
      info['Email'].append(small)
    elif 'www' in results[i] or 'WWW' in results[i] or 'wwW' in results[i]or  'wWW' in results[i]:
      small = results[i].lower()
      info['Website'].append(small)
    elif 'TamilNadu' in results[i] or 'Tamil Nadu' in results[i] or results[i].isdigit():
      info['Pincode'].append(results[i])
    elif re.match(r'^[A-Za-z]', results[i]):
      info['Company name'].append(results[i])
    else:
      removed_colon = re.sub(r'[,;]', '', results[i])
      info['Address'].append(removed_colon)
  for key, value in info.items():
    if len(value) > 0:
      concatenated_string = ' '.join(value)
      info[key] = [concatenated_string]
    else:
      value = 'NA'
      info[key] = [value]
  return info


#streamlit part 

st.set_page_config(page_title= "BizCardX: Extracting Business Card Data with OCR", page_icon=':credit_card:', layout='wide')
# Title
st.title(":blue[BizCardX: Extracting Business Card Data with OCR]")
with st.sidebar:
#   file_upload = st.sidebar.file_uploader(":green[UPLOAD CARD IMAGE>>>:credit_card:]",
                            #    type=["jpg", "jpeg", "png", "tiff", "tif", "gif"])
    
# Using object notation
  add_selectbox = st.sidebar.selectbox(
        "Select the option",
        ("INSERT DATA", "Upload & Modify", "Remove")
    )
  
  

if add_selectbox=="INSERT DATA":    
    uploaded_files = st.file_uploader("Choose a CSV file", accept_multiple_files=True)
    if uploaded_files is not None:
        for uploaded_file in uploaded_files:
            st.image(uploaded_file, caption='Uploaded Image', use_column_width=True)
            test,results= readtext(uploaded_files)
            din=extracted_info(test)
            df=pd.DataFrame(din)
            image= io.BytesIO()
            results.save(image, 'PNG')
            imagebyte=image.getvalue()
            photo={'image':[imagebyte]}
            dataimg=pd.DataFrame(photo)
            concatenate_images=pd.concat([df,dataimg],axis=1)
            st.dataframe(concatenate_images)            
            button=st.button("save")
            
            
            if button:
              db=psycopg2.connect(host='localhost',user='postgres',password='11001100',database='bizcard',port=5432)
              access=db.cursor()
              table='''create table if not exists bizcard_details(name varchar(100),
                                                                      designation varchar(500),
                                                                      company_name varchar(500),
                                                                      contact VARCHAR(500),
                                                                      email varchar(500),
                                                                      website text,
                                                                      address text,
                                                                      pincode varchar(500),
                                                                      image text                                                        
                                                                      )'''
              access.execute(table)
              db.commit()             
              
              
              insert_query='''insert into bizcard_details(name,
                                            designation ,
                                            company_name ,
                                            contact ,
                                            email ,
                                            website ,
                                            address ,
                                            pincode,
                                            image                                                         
                                            )                                            
                                            values(%s,%s,%s,%s,%s,%s,%s,%s,%s)'''  
                                    
              for index, row in concatenate_images.iterrows():
                values = (row['Name'], row['Designation'], row['Company name'], row['Contact'], row['Email'], row['Website'], row['Address'], row['Pincode'], row['image'])
                access.execute(insert_query, values)                
              st.success("Data inserted to PG")
# Commit the transaction to save the changes to the database
              db.commit()             
              query="select * from bizcard_details"
              access.execute(query)
              table=access.fetchall()
              db.commit()
              t1=pd.DataFrame(table,columns=['Name', 'Designation', 'company_name', 'Contact', 'Email', 'Website', 'Address', 'Pincode','image'])
              t1                 
                 
                 
if add_selectbox=="Upload & Modify":
  db=psycopg2.connect(host='localhost',user='postgres',password='11001100',database='bizcard',port=5432)
  access=db.cursor()
  access.execute("select name from bizcard_details")    
  result = access.fetchall()
  business_cards = {}   
  for row in result:
        business_cards[row[0]] = row[0]
  select_card_name = st.selectbox("Select Card To Edit", list(business_cards.keys()))   
  access.execute("SELECT * FROM bizcard_details WHERE name=%s", (select_card_name,))
  result = access.fetchone()
  
  Name = st.text_input("Name", result[0])
  Designation = st.text_input("Designation", result[1])
  company_name = st.text_input("company_name", result[2])
  Contact = st.text_input("Contact", result[3])
  Email = st.text_input("Email", result[4])
  Website = st.text_input("Website", result[5])
  Address = st.text_input("Address", result[6])
  Pincode = st.text_input("Pincode", result[7])
  image = st.text_input("image", result[8])
  st.balloons()
                   
  if st.button("Edit Card Data"):
    # Update the information for the selected business card in the database
    access.execute(
        "UPDATE bizcard_details SET Name=%s, Designation=%s, company_name=%s, Contact=%s, Email=%s, Website=%s, Address=%s, Pincode=%s,image=%s WHERE name=%s",
        (Name, Designation, company_name, Contact, Email, Website, Address, Pincode,image, select_card_name))
    db.commit()
    st.success("Card Data Updated")  
    
if add_selectbox=="Remove":
  db=psycopg2.connect(host='localhost',user='postgres',password='11001100',database='bizcard',port=5432)
  access=db.cursor()
  access.execute("select name from bizcard_details")    
  result = access.fetchall()
  business_cards = {}   
  for row in result:
        business_cards[row[0]] = row[0]
  select_card_name = st.selectbox("Select Card To Delete", list(business_cards.keys()))   
  access.execute("SELECT * FROM bizcard_details WHERE name=%s", (select_card_name,))
  result = access.fetchone()
  
  if st.button("Delete Card"):
      # Delete the selected business card from the database
      access.execute("DELETE FROM bizcard_details WHERE name=%s", (select_card_name,))
      db.commit()
      st.snow()
      st.success("Card Data Deleted")
                                        