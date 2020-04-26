from flask import Flask, escape, request, send_from_directory, send_file
from playhouse.sqlite_ext import *
from werkzeug.utils import secure_filename
from marshmallow import Schema, fields, validate, ValidationError
import json
import os

from peewee import *
from datetime import date

app = Flask(__name__)

db = SqliteDatabase('scantron.db')

class Test(Model):
    subject = CharField()
    answer_keys = JSONField()

    class Meta:
    	database = db

class Submission(Model):
    test_id = IntegerField()
    scantron_url = TextField()
    name = CharField()
    subject = CharField()
    score = IntegerField()
    result = JSONField()

    class Meta:
    	database = db

#Validation schema Marshmallow
class TestSchema(Schema):
	subject = fields.String(required=True)
	#keys = fields.String(required=True)

	#@validates("keys")
	#def validate_keys(self, value):
		#if len(val) > 1:
			#raise ValidationError("Not a valid key")


# For creating test
@app.route('/api/tests', methods = ['POST'])
def create_test():
	db.connect()
	db.create_tables([Test])
	content = request.json
	sub = content["subject"]
	ans_keys = content["answer_keys"]
	dataValidation = {"subject" : ""}
	TestSchema.load(dataValidation)
	test = Test(subject = sub, answer_keys=ans_keys)
	test.save()
	db.close()
	return {
        "test_id" : test.id,
        "subject" : test.subject,
        "answer_keys" : test.answer_keys
    }, 201


# After retrieving from pdf we should build the content and do it accordingly
@app.route('/api/tests/<tid>/scantrons', methods = ['POST'])
def write_scantrons(tid):
	rcvdData = request.files['data'].read()
	fmtData = rcvdData.decode('utf-8')
	if(fmtData == ""):
		return "Upload valid file"
	jsonData = json.loads(fmtData)
	file = request.files['data']
	db.connect()
	db.create_tables([Submission])
	if not os.path.exists("./files/"):
		os.makedirs("./files/")
	with open(os.path.join("./files/", file.filename), "wb") as fp:
		fp.write(rcvdData)
	url = "http://localhost:5000/files/"+file.filename
	name = jsonData["name"]
	sub = jsonData["subject"]
	score = 0
	result = {}
	return_test = Test.get(Test.id == tid)
	for i in range(1,51):
		var = str(i)
		result[var] = {"actual" : jsonData["answers"][var], "exected": return_test.answer_keys[var]}
		if(jsonData["answers"][var] == return_test.answer_keys[var]):
			score = score + 1
	submit = Submission(test_id = tid, scantron_url = url, name = name, subject = sub, score = score, result=result)
	submit.save()
	db.close()
	return {
        "scantron_id" : submit.id,
        "scantron_url" : submit.scantron_url,
        "name" : submit.name,
        "subject" : submit.subject,
        "score" : submit.score,
        "result" : submit.result
    }, 201

#For checking all scantron submissions
@app.route('/api/tests/<tid>')
def check_all_scantron_submissions(tid):
	db.connect()
	return_test = Test.get(Test.id == tid)
	submission = []
	for query in Submission.select().join(Test, on = (Submission.test_id == Test.id)).where(Test.id == tid).dicts():
		submission.append(query)
	db.close()
	refSubmission = [] * len(submission)
	for i in range(len(submission)):
		jsonObj = {}
		jsonObj["scantron_id"] = submission[i]["id"]
		jsonObj["scantron_url"] = submission[i]["scantron_url"]
		jsonObj["name"] = submission[i]["name"]
		jsonObj["subject"] = submission[i]["subject"]
		jsonObj["score"] = submission[i]["score"]
		jsonObj["result"] = submission[i]["result"]
		refSubmission.append(jsonObj)
	return {
        "test_id" : return_test.id,
        "subject" : return_test.subject,
        "answer_keys" : return_test.answer_keys,
        "submissions" : refSubmission
        }

#Downloading the content from scantronURL
@app.route('/files/<fName>')
def download_file(fName):
	print("inside")
	path = "./files/"
	print(path)
	return send_from_directory(path,fName, as_attachment=True)

    
