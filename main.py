import numpy as np
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
  return render_template('index.html')
  
@app.route('/display_cohort_table', methods=['POST'])
def display_cohort_table():
  data = request.get_json()  # get the request data as a dictionary
  data = data.get('csv')  # get the csv value from the dictionary
  csvFile = data.get('data')  # get the csv value from the dictionary

  if csvFile is None:  # if the csv value is not present in the request
    return 'csv value is empty'  # return an error message
  
  df = pd.DataFrame(csvFile[1:], columns=csvFile[0])
  df = df.rename(columns={'orderdate':'order_date','customer':'customer_id','order':'Sequence'})
  # First CTE: orders_invoiced
  df_invoiced = df[df[['Sequence', 'order_date', 'customer_id']].notnull().all(axis=1)]
  df_invoiced = df_invoiced.groupby(['Sequence', 'order_date', 'customer_id']).size().reset_index(name='count')
  # Second CTE: order_sequence
  df_sequence = df_invoiced.assign(customer_order_sequence=lambda x: x.groupby('customer_id')['order_date'].rank(method='first', ascending=True))
  df_sequence = df_sequence.assign(first_order_date=lambda x: x.groupby('customer_id')['order_date'].transform('min'))
  # Third CTE: time_between_orders
  df_month_partition = df_sequence.assign(partition=lambda x: np.where(x['customer_order_sequence'] == 1, 0, np.trunc(((pd.to_datetime(x['order_date']) - pd.to_datetime(x['first_order_date'])).dt.days / 30.416) + 1).astype(int)))
  # Final SELECT statement partition to unique months
  df_month_partition = df_month_partition.assign(month=pd.to_datetime(df_month_partition['first_order_date'], errors='coerce').dt.strftime('%Y-%m'))
  # Unique customers per partition
  df_month_partitioned = df_month_partition.groupby(['month','partition']).agg({'customer_id': lambda x: x.nunique()}).reset_index()
  # Unique customers on month 0: Total unique customers for month
  df_partitioned_month0_unique_customers = df_month_partitioned[df_month_partitioned['partition']==0][['month','customer_id']]
  df_partitioned_month0_unique_customers = pd.merge(df_month_partitioned, df_partitioned_month0_unique_customers, on='month', how='left')
  df_partitioned_month0_unique_customers = df_partitioned_month0_unique_customers.rename(columns={'customer_id_x':'uniqueCustomers','customer_id_y':'totalCustomers','month':'date'})
  df_partitioned_month0_unique_customers = df_partitioned_month0_unique_customers.sort_values(['date', 'partition'], ascending=[False, False])
  print(df_partitioned_month0_unique_customers)  

  # Calculate the retention rate
  retention = df_partitioned_month0_unique_customers['uniqueCustomers'] / df_partitioned_month0_unique_customers['totalCustomers']

  # Add the retention column to the dataframe
  df = df_partitioned_month0_unique_customers.assign(retention=retention)

  # create a pivot table
  cohort_table = df.pivot(index='date',
                          columns=['partition'],
                          values='retention').fillna(0).round(decimals=2)

  # Calculate the maximum totalCustomers value for each date
  max_totalCustomers = df.groupby('date')['totalCustomers'].max()

  # Add the maximum value of totalCustomers as a new column
  cohort_table2 = cohort_table.assign(total=max_totalCustomers)
  cohort_table2=cohort_table2.sort_values('date',ascending=False)
  # Convert the dataframe to an HTML table
  html_table = cohort_table2.to_html()

  # Return the processed file as a response
  return html_table

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81)
