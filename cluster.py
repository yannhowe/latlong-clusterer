from __future__ import print_function
import pickle
import os
import logging
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
import csv

import numpy as np
import pandas as pd
#import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
#from collections import Counter


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = os.environ['SAMPLE_SPREADSHEET_ID']
SAMPLE_RANGE_NAME = os.environ['SAMPLE_RANGE_NAME']

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.DEBUG)

# Transform the postal code data to use postal code as key
def refresh_postal_code():
    # Singapore Postal code data from here - https://github.com/xkjyeah/singapore-postal-codes/blob/master/buildings.json
    data_transformed = {}
    with open('buildings.json') as json_file:  
        data = json.load(json_file)
        for p in data:
            data_transformed[p['POSTAL']] = {
                'LATITUDE': p['LATITUDE'],
                'LONGITUDE': p['LONGITUDE']
            }
            
    with open('postal-codes.json', 'w') as outfile:  
        json.dump(data_transformed, outfile, indent=4)


def get_values_from_sheets():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    # Write to file
    with open("user-postal-codes.csv",'w') as resultFile:
        wr = csv.writer(resultFile, dialect='excel')
        for row in values:
            wr.writerow(row)

    return values


def convert_to_latlong(values):
    if not values:
        logging.error('No data found in user-postal-codes.csv. Is there data in google sheets? (https://docs.google.com/spreadsheets/d/%s/).' % SAMPLE_SPREADSHEET_ID)
    else:
        postal_codes = {}
        if not os.path.exists('postal-codes.json'):
            refresh_postal_code()

        with open('postal-codes.json') as json_file:  
            data = json.load(json_file)
            
        for row in values[1:]:
            try:
                postal_codes[row[1]] = {
                    'LATITUDE': data[row[1]]['LATITUDE'],
                    'LONGITUDE': data[row[1]]['LONGITUDE']
                }
                logging.debug(json.dumps(postal_codes, indent=4))
            except(KeyError):
                logging.warning("Postal Code: %s doesn't exist." % row[1])

        with open("latlongs.csv",'w') as resultFile:
            wr = csv.writer(resultFile, dialect='excel')
            wr.writerow(["Timestamp","Postal Code","Latitude","Longitude"])
            for row in values[1:]:
                latlong = data[row[1]]
                row = row + [latlong["LATITUDE"]] + [latlong["LONGITUDE"]]
                logging.debug("row: %s" % row)
                wr.writerow(row)


def main():
    # Get postal codes from google sheets
    values = []
    if not os.path.exists('user-postal-codes.csv'):
        logging.info("getting data from sheets into user-postal-codes.csv")
        get_values_from_sheets()
    with open('user-postal-codes.csv') as csv_file:
        values = list(csv.reader(csv_file))

    # Convert postal codes to latlongs
    logging.info("getting data from latlongs.csv")
    convert_to_latlong(values)
    
    # Start doing stuff
    df = pd.read_csv('latlongs.csv')
    logging.info("df: %s" % df)

    latlongs_df = df.loc[:,['Latitude','Longitude']]
    logging.info("latlongs_df: %s" % latlongs_df)

    # run KMeans
    id_n = 3
    kmeans = KMeans(n_clusters=id_n, random_state=0).fit(latlongs_df)
    df['Group'] = kmeans.labels_
    logging.info("df: %s" % df)

    # put postal codes back into google sheets
    


if __name__ == '__main__':
    main()