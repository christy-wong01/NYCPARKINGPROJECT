from sodapy import Socrata
import requests
from requests.auth import HTTPBasicAuth
import argparse
import sys
import os
import json
 
parser = argparse.ArgumentParser(description='Process data from parking violations.')
parser.add_argument('--page_size', type=int, help='how many rows to get per page', required=True)
parser.add_argument('--num_pages', type=int, help='how many pages to get in total')
args = parser.parse_args(sys.argv[1:])
print(args)


#DATASET_ID="nc67-uf89"
#APP_TOKEN="0JDiKzy1OwfhlzCfB1NMcNGUZ"
#ES_HOST="https://search-cis9760-christy-wong-sitwsncumvujzdzooyxcgqwksi.us-east-1.es.amazonaws.com"
#ES_USERNAME="christywong"
#ES_PASSWORD="Pokemon2132#"
#INDEX_NAME="parkingnycproject"

DATASET_ID=os.environ["DATASET_ID"]
APP_TOKEN=os.environ["APP_TOKEN"]
ES_HOST=os.environ["ES_HOST"]
ES_USERNAME=os.environ["ES_USERNAME"]
ES_PASSWORD=os.environ["ES_PASSWORD"]
INDEX_NAME=os.environ["INDEX_NAME"]


if __name__ == '__main__': 
    try:
        resp = requests.put(f"{ES_HOST}/{INDEX_NAME}",auth=HTTPBasicAuth(ES_USERNAME, ES_PASSWORD),
            json={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1
                },
                "mappings": {
                    "properties":{
                        "plate":{"type":"keyword"},
                        "state":{"type":"keyword"}, 
                        "license_type":{"type":"keyword"}, 
                        "summons_number":{"type":"keyword"}, 
                        "issue_date":{"type":"date","format":"MM/DD/YYYY"},
                        "violation": {"type":"keyword"},
                        "fine_amount":{"type":"float"},
                        "penalty_amount":{"type":"float"},
                        "interest_amount":{"type":"float"},
                        "reduction_amount":{"type":"float"},
                        "payment_amount":{"type":'float'},
                        "amount_due":{"type":"float"},
                        "precinct":{"type":"keyword"},
                        "county":{"type":"keyword"},
                    }
                },
            }
        )
        resp.raise_for_status()
        print(resp.json())


    except Exception as e:
        print("Index already exist! Skipping")
    
    client = Socrata("data.cityofnewyork.us", APP_TOKEN,)
    rows = client.get(DATASET_ID, limit= args.page_size, offset=1000000,order='summons_number')
    
    es_rows=[]
    
    for row in rows:
        try:
            es_row={}
            es_row["plate"]=row["plate"]
            es_row["state"] =row["state"]
            es_row["license_type"]=row["license_type"]
            es_row["summons_number"]=row["summons_number"]
            es_row["issue_date"]=row["issue_date"]
            es_row["violation"]=row["violation"]
            es_row["fine_amount"]=float(row["fine_amount"])
            es_row["penalty_amount"]=float(row["penalty_amount"])
            es_row["interest_amount"]=float(row["interest_amount"])
            es_row["reduction_amount"]=float(row["reduction_amount"])
            es_row["payment_amount"]=float(row["payment_amount"])
            es_row["amount_due"]=float(row["amount_due"])
            es_row["precinct"]=row["precinct"]
            es_row["county"]=row["county"]
            #print(es_row)
            
        except Exception as e:
            print (f"Error!: {e}, skipping row: {row}")
            continue
        es_rows.append(es_row)
    
    bulk_upload_data = ""
    for line in es_rows:
        print(f'Handling row {line["summons_number"]}')
        action = '{"index": {"_index": "' + INDEX_NAME + '", "_type": "_doc", "_id": "' + line["summons_number"] + '"}}'
        data = json.dumps(line)
        bulk_upload_data += f"{action}\n"
        bulk_upload_data += f"{data}\n"
        
    try:
            # Upload to Elasticsearch by creating a document
        resp = requests.post(f"{ES_HOST}/_bulk",
            # We upload es_row to Elasticsearch
                    data=bulk_upload_data,auth=HTTPBasicAuth(ES_USERNAME, ES_PASSWORD), headers = {"Content-Type": "application/x-ndjson"})
        resp.raise_for_status()
        print ('Done')
            
        # If it fails, skip that row and move on.
    except Exception as e:
        print(f"Failed to insert in ES: {e}, skipping row: {row}")  
        
        
        #try:
            # Upload to elasticsearch by creating a doc
            # This is the URL to create a new payroll document which is our "row" in elasticsearch databse/table
            #resp = requests.post(f"{ES_HOST}/{INDEX_NAME}/_doc",
                    #json=es_row,auth=HTTPBasicAuth(ES_USERNAME, ES_PASSWORD),)
            #resp.raise_for_status()
        #except Exception as e:
            #print(f"Failed to insert in ES: {e}, skipping row: {row}")
            #continue
        