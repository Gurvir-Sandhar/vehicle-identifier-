"""
Vehicle recognition app
Gurvir Sandhar
"""
import json
import os
import ssl
import http.client as httplib
import wikipedia
from flask import Flask, redirect, request, url_for, render_template
from google.cloud import datastore, storage
from datetime import datetime

app = Flask(__name__)

API_Token = "uo6UJKOpXGTVOXpugWdOwjfZvQXYMV44MoWi"


@app.route('/')
@app.route('/index.html')
def index():
    """
    Default route.
    List all previous uploads from 
    Datastore to webpage.
    Renders HTML

    """
    datastore_client = datastore.Client('cs430-gurvir-sandhar')
    query = datastore_client.query(kind='CarID')
    image_entities = list(query.fetch())
    #image_entities.reverse()
    
    return render_template('index.html', image_entities=image_entities)


@app.route('/upload_photo', methods=['GET','POST'])
def upload_photo():
    """
    Uploads photo to datastore
    Sends link of photo to API
    Recieves and parses API response
    Uploads data to datastore
    Redirects to default route

    """
    #get and store photo from forum
    try:
        photo = request.files['file']
    except:
        photo = None
    storage_client = storage.Client()

    bucket = storage_client.get_bucket('cs430-gurvir-sandhar')
    blob = bucket.blob(photo.filename)
    blob.upload_from_string(photo.read(), content_type=photo.content_type)
    blob.make_public()
    
    #API request code
    headers = {"Content-type": "application/json", "X-Access-Token": API_Token}
    conn = httplib.HTTPSConnection("dev.sighthoundapi.com", 
                                   context=ssl.SSLContext(ssl.PROTOCOL_TLSv1))
    image_data = blob.public_url
    params = json.dumps({"image": image_data})
    conn.request("POST", "/v1/recognition?objectType=vehicle", params, headers)
    response = conn.getresponse()
    results = json.loads(response.read())
    print(results)
   
   #loop through data and append make/model of recognized vehicles into list
   #I am only using the first/main one for this project
    mylist = []
    for obj in results["objects"]:
        if obj["objectType"] == "vehicle":
            make  = obj["vehicleAnnotation"]["attributes"]["system"]["make"]["name"]
            model = obj["vehicleAnnotation"]["attributes"]["system"]["model"]["name"]
            mylist.append(make + " " + model)

    #getting the wikipedia summary
    wiki_summary = wikipedia.summary(mylist[0])

    #code to save data in datastore
    datastore_client = datastore.Client()
    current_datetime = datetime.now()
    kind = "CarID"
    key = datastore_client.key(kind,blob.name)

    entity = datastore.Entity(key)
    entity['blob_name'] = blob.name
    entity['image_public_url'] = blob.public_url
    entity['timestamp'] = current_datetime
    entity['car_models'] = mylist[0]
    entity['summary'] = wiki_summary

    datastore_client.put(entity)

    return redirect('index.html')



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)



