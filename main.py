import os
import csv
import requests
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, Response
from requests_toolbelt import MultipartEncoder

app = Flask(__name__)


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/display_cohort_table', methods=['POST'])
def display_cohort_table():
  data = request.get_json()  # get the request data as a dictionary
  csvFile = data.get('csv')  # get the csv value from the dictionary
  if csvFile is None:  # if the csv value is not present in the request
    return 'csv value is empty'  # return an error message

  url = 'https://api.tinybird.co/v0/datasources?mode=replace&name=cohortanomimized2&format=csv'
  headers = {
    'Authorization':
    'Bearer p.eyJ1IjogIjE2ZjM5MGRhLTdiYWQtNGMyNy04YjlkLTIyNjIxOGZkOTQ5NiIsICJpZCI6ICI2NGUxOTc1OC1iZDJlLTQ2MTItOTM5Ny1lY2ZlMTZmOGViMGUifQ.CgarsY961PFxUpv3c_kxcvVrkb0KreRLSZO_V5B9tJ0'
  }
  data = MultipartEncoder(fields={'csv': ('filename', csvFile, 'text/plain')})

  # Send the POST request
  response = requests.post(url, headers=headers, data=data)
  response = response.text

  # Send an HTTP GET request to the
  url = 'https://api.tinybird.co/v0/pipes/cohortdata.json'
  params = {
    "token":
    "p.eyJ1IjogIjE2ZjM5MGRhLTdiYWQtNGMyNy04YjlkLTIyNjIxOGZkOTQ5NiIsICJpZCI6ICI3ZDRhMjg5YS05YjVkLTQ5NjctOTdhZi03MmRhYWFiYTczZTQifQ.Hb9ZqN9fLAucqWs7oC--LkM1LLFt7xwJ6r-eypsxmdI"
  }
  tinytable = requests.get(url, params=params)

  # Parse the JSON data
  tinytable = tinytable.json()['data']

  # Specify the column names
  columns = ['date', 'totalCustomers', 'uniqueCustomers', 'partition']

  # Transform the data into a dataframe
  df = pd.DataFrame(tinytable, columns=columns)

  # Calculate the retention rate
  retention = df['uniqueCustomers'] / df['totalCustomers']

  # Add the retention column to the dataframe
  df = df.assign(retention=retention)

  # create a pivot table
  cohort_table = df.pivot(index='date',
                          columns=['partition'],
                          values='retention')

  # Calculate the maximum totalCustomers value for each date
  max_totalCustomers = df.groupby('date')['totalCustomers'].max()

  # Add the maximum value of totalCustomers as a new column
  cohort_table2 = cohort_table.assign(total=max_totalCustomers)
    cohort_table2=cohort_table2.sort_values('date',ascending=False)
  # Convert the dataframe to an HTML table
  html_table = cohort_table2.to_html()

  # Return the processed file as a response
  return html_table


app.run(host='0.0.0.0', port=81)
