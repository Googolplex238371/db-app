from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_cors import cross_origin
from . import db
from .models import Data,User,Query
import json
import random
from flask import jsonify
import string
import os
from sqlalchemy.sql import func
import pandas as pd
from datetime import datetime
import numpy as np
import math
from werkzeug.utils import secure_filename
import mimetypes
from email.mime.multipart import MIMEMultipart
import secrets
def validate_date(date_text):
    try:
        datetime.strptime(date_text, '%d/%m/%Y')
        return True
    except ValueError:
        return False
def validate_time(time_text):
    try:
        datetime.strptime(time_text, '%H:%M:%S')
        return True
    except ValueError:
        return False
views = Blueprint('views', __name__)
@views.route('/')
@login_required
def home():
  try:
    raw_data = Data.query.filter_by(user_id=current_user.id)
  except:
    raw_data = []
  data = []
  for index in raw_data: 
    data.append([index.name,index.apikey,index.data,index.last_change,index.columns,index.requests,index.types])
  raw_queries = []
  queries = []
  if raw_data !=[]:
    raw_queries = Query.query.filter_by(user_id=current_user.id)
    for query in raw_queries:
      db = Data.query.filter_by(apikey=query.apikey).first()
      queries.append([query.id,query.name,query.criteria,query.data,query.apikey,db.columns,db.name])
  return render_template("home.html",user=current_user,data=data,queries=queries)
@views.route('/add-database',methods=["GET","POST"])
@login_required
def add_db():
  if request.method == "POST":
    x = 1
    while request.form.get("field"+str(x)) != None:
      x+=1
    x-=1
    api = (''.join(random.choices(string.ascii_letters + string.digits, k=30)))
    daba = Data.query.filter_by(apikey=api).first()
    while daba: 
      api = (''.join(random.choices(string.ascii_letters + string.digits, k=30)))
      daba = Data.query.filter_by(apikey=api).first()
    columns = ""
    for i in range(1,x+1):
      columns+=(request.form.get("field"+str(i)))+","
    types = ""
    for i in range(1,x+1):
      types+=(request.form.get("type"+str(i)))+","
    if len(set(tuple(columns.split(",")))) != len(columns.split(",")):
      flash("Duplicate column names are not allowed",category="error")
      return redirect(url_for("views.add_db"))
    if not '#' in columns and not "%" in columns and not "$" in columns and not "@" in columns and not "/" in columns and not "'" in columns and not '"' in columns:  
      do = True
      for user_database in Data.query.filter_by(user_id=current_user.id):
        if user_database.name == request.form["name"]:
          do = False
      if do:
        db.session.add(Data(name=request.form["name"],apikey=api,columns=columns,primary_key=int(request.form["primary_key"].split("field")[1]),data="[]",user_id=current_user.id,requests="",types=types))
        db.session.commit()
        flash("Added database with key "+api,category = "success")
        return redirect(url_for("views.home"))
      else:
        flash("Database with this name already exists",category = "danger")
    else: 
      flash("No special symbols are allowed",category="error")
  return render_template("add.html",user=current_user)
@views.route('/edit-database/<api>',methods=["GET","POST"])
@login_required
def edit_db(api):
  if request.method == "POST":
    daba = Data.query.filter_by(apikey=api).first()
    if not daba:
      return redirect(url_for("views.nopage"))
    x = 1
    while request.form.get("field"+str(x)) != None:
      x+=1
    x-=1
    columns = ""
    for i in range(1,x+1):
      columns+=(request.form.get("field"+str(i)))+","
    if not '#' in columns and not "%" in columns and not "$" in columns and not "@" in columns and not "/" in columns and not "'" in columns and not '"' in columns:  
      do = True
      for user_database in Data.query.filter_by(user_id=current_user.id):
        if user_database.name == request.form["name"] and user_database.apikey != daba.apikey:
          do = False
      if do:
        daba.name=request.form["name"]
        daba.columns=columns
        db.session.commit()
        flash("Edited database successfully",category = "success")
        return redirect(url_for("views.home"))
      else:
        flash("Database with this name already exists",category = "danger")
        return redirect(url_for("views.edit_db",api=api))
    else: 
      flash("No special symbols are allowed",category="error")
  daba = Data.query.filter_by(apikey=api).first()
  if not daba:
    flash("No such database found",category="error")
    return redirect(url_for("views.home"))
  return render_template("edit.html",user=current_user,db = daba,columns=[[i+1,daba.columns.split(",")[i]] for i in range(len(daba.columns.split(",")))])
@views.route("/get-query",methods = ["POST","GET"])
@cross_origin()
def get_query():
  if request.data:
    id = json.loads(request.data)["id"]
    query = Query.query.filter_by(id=id).first()
    database = Data.query.filter_by(apikey=query.apikey).first()
    if query:
      data_split=list(query.data)
      if len(data_split)>2:
        for i in range(2):
          data_split.pop(0)
          data_split.pop(len(data_split)-1)
        data_split="".join(data_split).split("],[")
        d=[]
        types = database.types.split(",")
        for i in range(len(data_split)):
          d.append([])
          for j in range(len(data_split[i].split(","))):
            if types[j] == "int":
              d[i].append(int(data_split[i].split(",")[j]))
            elif types[j] == "float":
              d[i].append(float(data_split[i].split(",")[j]))
            elif types[j] == "bool":
              if data_split[i].split(",")[j].lower() in ["true","y","yes"]:
                d[i].append(True)
              else:
                d[i].append(False)
            else:
              d[i].append(data_split[i].split(",")[j])
      else:
        d = []
      return jsonify({"data":d})
    else:
      return jsonify({"error":"No query with this key found"})
  else:
    return redirect(url_for("views.nopage"))
@views.route("/access-data",methods = ["POST","GET"])
@cross_origin()
def access():
  if request.data:
    data = json.loads(request.data)
    if data["request"] in ["write","update"] and True in ["[" in d or "]" in d or "," in d or "\n" in d for d in data["data"]]:
      return jsonify({"error":"Data cannot contain special characters"})
    if data["request"] in ["update","delete"]:
      try:
        int(data["index"])
      except:
        return jsonify({"error":"Invalid index"})
    if data["request"] in ["update","write"]:
      try:
        1/len(data["data"])
        for i in range(len(data["data"])):
          data["data"][i] = str(data["data"][i])
      except:
        return jsonify({"error":"No data given"})
    api = data['api_key']
    database = Data.query.filter_by(apikey=api).first()
    if database:
      print(database.types)
      length = len(database.columns.split(","))-1
      if data["request"] == "write":
        for idx,entry in enumerate(data["data"]):
          if database.types.split(",")[idx] == "date":
            if not validate_date(entry):
              return jsonify({"error":"Invalid date format"})
          if database.types.split(",")[idx] == "time":
            if not validate_time(entry):
              return jsonify({"error":"Invalid time format"})
          if database.types.split(",")[idx] == "float":
            try:
              float(entry)
            except:
              return jsonify({"error":"Invalid number format"})
          if database.types.split(",")[idx] == "int":
            try:
              int(entry)
            except:
              return jsonify({"error":"Invalid number format"})
          if database.types.split(",")[idx] == "bool":
            if entry.lower() not in ["true","false","y","n","yes","no"]:
              return jsonify({"error":"Invalid boolean format"})
            if entry.lower() in ["y","yes","true"]:
              data["data"][idx] = "true"
            else:
              data["data"][idx] = "false"
        d = list(database.data)
        d.pop(len(d)-1)
        add = ""
        data_split = list(database.data)
        p_key = (data["data"])[database.primary_key-1]
        if len(data["data"]) != length:
            return jsonify({"error":"Invalid record size"})
        if len(data_split)>2:
          for i in range(2):
            data_split.pop(0)
            data_split.pop(len(data_split)-1)
          data_split = ("".join(data_split)).split("],[")
          rows = []
          for row in data_split:
            rows.append(row.split(",")[database.primary_key-1])
          if p_key in rows:
            return jsonify({"error":"Primary key already exists"})
        if d !=["["]:
            add = ","
        d = "".join(d)
        d+=add+"["+",".join(data["data"])+"]"
        d+="]"
        database.data = d
        database.last_change = func.now()
        columns = database.columns.split(",")
        types = database.types.split(",")
        if "" in columns:
          columns.pop(len(columns)-1)
          types.pop(len(types)-1)
      elif data["request"] == "update":
        for idx,entry in enumerate(data["data"]):
          if database.types.split(",")[idx] == "date":
            if not validate_date(entry):
              return jsonify({"error":"Invalid date format"})
          if database.types.split(",")[idx] == "time":
            if not validate_time(entry):
              return jsonify({"error":"Invalid time format"})
          if database.types.split(",")[idx] == "float":
            try:
              float(entry)
            except:
              return jsonify({"error":"Invalid number format"})
          if database.types.split(",")[idx] == "float":
            try:
              float(entry)
            except:
              return jsonify({"error":"Invalid number format"})
          if database.types.split(",")[idx] == "int":
            try:
              if "." in entry:
                return jsonify({"error":"Invalid number format"})
              int(entry)
            except:
              return jsonify({"error":"Invalid number format"})
          if database.types.split(",")[idx] == "bool":
            if entry.lower() not in ["true","false","y","n","yes","no"]:
              return jsonify({"error":"Invalid boolean format"})
            if entry.lower() in ["y","yes","true"]:
              data["data"][idx] = "true"
            else:
              data["data"][idx] = "false"
        data_split = list(database.data)
        p_key = (data["data"])[database.primary_key-1]
        if len(data["data"]) != length:
          return jsonify({"error":"Invalid record size"})
        if len(data_split)>2:
          for i in range(2):
            data_split.pop(0)
            data_split.pop(len(data_split)-1)
          data_split = ("".join(data_split)).split("],[")
          rows = []
          for row in data_split:
            rows.append(row.split(",")[database.primary_key-1])
          if p_key in rows and rows.index(p_key) != int(data["index"]):
            return jsonify({"error":"Primary key already exists"})
          data_split[int(data["index"])] = ",".join(data["data"])
        else:
          return jsonify({"error":"No data to update"})
        database.data = "[["+"],[".join(data_split)+"]]"
        database.last_change = func.now()
        db.session.commit()
      elif data["request"] == "delete":
        data_split = list(database.data)
        if len(data_split)>2:
          for i in range(2):
            data_split.pop(0)
            data_split.pop(len(data_split)-1)
          data_split = ("".join(data_split)).split("],[")
          data_split.pop(int(data["index"]))
        else:
          return jsonify({"error":"No data to delete"})
        database.data = "[["+"],[".join(data_split)+"]]"
        database.last_change = func.now()
        db.session.commit()
        columns = database.columns.split(",")
        types = database.types.split(",")
        if "" in columns:
          columns.pop(-1)
          types.pop(-1)
        requests = database.requests
        requests +=datetime.now().strftime("%d/%m/%Y %H:%M:%S")+","+data["request"]+";"
        database.requests = requests
        db.session.commit()
      if data["request"] == "read" or data["request"] == "update" or data["request"] == "write" or data["request"] == "delete": 
        data_split=list(database.data)
        requests = database.requests
        requests +=datetime.now().strftime("%d/%m/%Y %H:%M:%S")+","+data["request"]+";"
        database.requests = requests
        db.session.commit()
        if len(data_split)>2:
          for i in range(2):
            data_split.pop(0)
            data_split.pop(len(data_split)-1)
          data_split="".join(data_split).split("],[")
          d=[]
          types = database.types.split(",")
          for i in range(len(data_split)):
            d.append([])
            for j in range(len(data_split[i].split(","))):
              if types[j] == "int":
                d[i].append(int(data_split[i].split(",")[j]))
              elif types[j] == "float":
                d[i].append(float(data_split[i].split(",")[j]))
              elif types[j] == "bool":
                if data_split[i].split(",")[j].lower() in ["true","y","yes"]:
                  d[i].append(True)
                else:
                  d[i].append(False)
              else:
                d[i].append(data_split[i].split(",")[j])
          if data["request"] =="read":
            return jsonify({"data":d,"last_updated":database.last_change,"records":len(database.data.split("],["))})
          else:
              columns = database.columns.split(",")
              types = database.types.split(",")
              if "" in columns:
                columns.pop(len(columns)-1)
                types.pop(len(types)-1)
              queries = Query.query.filter_by(apikey=database.apikey).all()
              for query in queries:
                data = database.data
                data = data[1:len(data)-1]
                if data != "":
                  data = data[1:len(data)-1]
                data = data.split("],[")
                db_criteria = query.criteria
                if data[0] == "":
                  data = []
                  query.data = "[]"
                else:
                  for i in range(len(data)):
                    data[i] = data[i].split(",")
                for i in range(len(data)):
                  for j in range(len(data[i])):
                    if types[j] == "bool":
                      if data[i][j].lower() in ["true","y","yes"]:
                        data[i][j] = "True"
                      else:
                        data[i][j] = "False"
                criteria = db_criteria.split(";")
                criteria.remove("")
                to_remove = []
                for i in data:
                  for j in criteria:
                    if j.split(":")[1] == "equal" and i[int(j.split(":")[0])] != j.split(":")[2]:
                        to_remove.append(i)
                        break
                    if j.split(":")[1] == "nequal" and i[int(j.split(":")[0])] == j.split(":")[2]:
                        to_remove.append(i)
                        break
                    if types[int(j.split(":")[0])] == "date":
                      if j.split(":")[1] == "greater":
                        if datetime.strptime(i[int(j.split(":")[0])],'%d/%m/%Y') <= datetime.strptime(j.split(":")[2],'%d/%m/%Y'):
                          to_remove.append(i)
                          break
                      if j.split(":")[1] == "less":
                        if datetime.strptime(i[int(j.split(":")[0])],'%d/%m/%Y') >= datetime.strptime(j.split(":")[2],'%d/%m/%Y'):
                          to_remove.append(i)
                          break
                    if types[int(j.split(":")[0])] == "time":
                      if j.split(":")[1] == "greater":
                        if datetime.strptime(i[int(j.split(":")[0])],'HH:MM:SS') <= datetime.strptime(j.split(":")[2],'HH:MM:SS'):
                          to_remove.append(i)
                          break
                      if j.split(":")[1] == "less":
                        if datetime.strptime(i[int(j.split(":")[0])],'HH:MM:SS') >= datetime.strptime(j.split(":")[2],'HH:MM:SS'):
                          to_remove.append(i)
                          break
                    if j.split(":")[1] == "greater" and float(i[int(j.split(":")[0])]) <= float(j.split(":")[2]):
                        to_remove.append(i)
                        break
                    if j.split(":")[1] == "less" and float(i[int(j.split(":")[0])]) >= float(j.split(":")[2]):
                        to_remove.append(i)
                        break
                    if j.split(":")[1] == "contains" and j.split(":")[2] not in i[int(j.split(":")[0])]:
                        to_remove.append(i)
                        break
                    if j.split(":")[1] == "startswith" and not i[int(j.split(":")[0])].startswith(j.split(":")[2]):
                        to_remove.append(i)
                        break
                    if j.split(":")[1] == "endswith" and not i[int(j.split(":")[0])].endswith(j.split(":")[2]):
                        to_remove.append(i)
                        break
                for i in to_remove:
                  data.remove(i)
                data = [",".join([str(j) for j in i]) for i in data]  
                data = "[["+"],[".join(data)+"]]"
                if data == "[[]]":
                  data = "[]"
                query.data = data
              db.session.commit()
              return jsonify({"data":d})
        else:
          return jsonify({"data":[],"last_updated":database.last_change,"records":0})
      else:
        return jsonify({"error":"Invalid request"})
    else:
      return jsonify({"error":"No database"})
  else:
    return redirect(url_for("views.nopage"))
@views.route("/add-query",methods = ["GET","POST"])
@login_required
def add_query():
  if request.method == "POST":
    id = secrets.token_urlsafe(16)
    while Query.query.filter_by(id=id).first():
      id = secrets.token_urlsafe(16)
    database = Data.query.filter_by(name=request.form.get("database")).first()
    if not database:
      flash("No such database",category="error")
      return redirect(url_for("views.home"))
    for query in Query.query.filter_by(user_id=current_user.id).all():
      if query.name == request.form.get("/name"):
        flash("Query with this name already exists",category="error")
        return redirect(url_for("views.add_query"))
    columns = database.columns.split(",")
    types = database.types.split(",")
    if "" in columns:
      columns.pop(len(columns)-1)
      types.pop(len(types)-1)
    data = database.data
    data = data[1:len(data)-1]
    if data != "":
      data = data[1:len(data)-1]
    data = data.split("],[")
    db_criteria = ""
    idx = 0
    for column in columns:
      if request.form.get(column) != "none":
        db_criteria+=str(idx)+":"+request.form.get(column)+":"+request.form.get("criterion-"+column)+";"
      idx+=1
    if db_criteria == "":
      flash("No criteria",category="error")
      return redirect(url_for("views.add_query"))
    if data[0] == "":
      data = []
      query = Query(id=id,criteria=db_criteria,user_id=current_user.id,apikey=database.apikey,name=request.form.get("name"),data="[]")
    else:
      for i in range(len(data)):
        data[i] = data[i].split(",")
    for i in range(len(data)):
      for j in range(len(data[i])):
        if types[j] == "bool":
          if data[i][j].lower() in ["true","y","yes"]:
            data[i][j] = "True"
          else:
            data[i][j] = "False"
    criteria = db_criteria.split(";")
    criteria.remove("")
    to_remove = []
    for i in data:
      for j in criteria:
        if j.split(":")[1] == "equal" and i[int(j.split(":")[0])] != j.split(":")[2]:
            to_remove.append(i)
            break
        if j.split(":")[1] == "nequal" and i[int(j.split(":")[0])] == j.split(":")[2]:
            to_remove.append(i)
            break
        if types[int(j.split(":")[0])] == "date":
          if j.split(":")[1] == "greater":
            if datetime.strptime(i[int(j.split(":")[0])],'%d/%m/%Y') <= datetime.strptime(j.split(":")[2],'%d/%m/%Y'):
              to_remove.append(i)
              break
          if j.split(":")[1] == "less":
            if datetime.strptime(i[int(j.split(":")[0])],'%d/%m/%Y') >= datetime.strptime(j.split(":")[2],'%d/%m/%Y'):
              to_remove.append(i)
              break
        if types[int(j.split(":")[0])] == "time":
          if j.split(":")[1] == "greater":
            if datetime.strptime(i[int(j.split(":")[0])],'HH:MM:SS') <= datetime.strptime(j.split(":")[2],'HH:MM:SS'):
              to_remove.append(i)
              break
          if j.split(":")[1] == "less":
            if datetime.strptime(i[int(j.split(":")[0])],'HH:MM:SS') >= datetime.strptime(j.split(":")[2],'HH:MM:SS'):
              to_remove.append(i)
              break
        if j.split(":")[1] == "greater" and float(i[int(j.split(":")[0])]) <= float(j.split(":")[2]):
            to_remove.append(i)
            break
        if j.split(":")[1] == "less" and float(i[int(j.split(":")[0])]) >= float(j.split(":")[2]):
            to_remove.append(i)
            break
        if j.split(":")[1] == "contains" and j.split(":")[2] not in i[int(j.split(":")[0])]:
            to_remove.append(i)
            break
        if j.split(":")[1] == "startswith" and not i[int(j.split(":")[0])].startswith(j.split(":")[2]):
            to_remove.append(i)
            break
        if j.split(":")[1] == "endswith" and not i[int(j.split(":")[0])].endswith(j.split(":")[2]):
            to_remove.append(i)
            break
    for i in to_remove:
      data.remove(i)
    data = [",".join([str(j) for j in i]) for i in data]
    print(data)
    data = "[["+"],[".join(data)+"]]"
    if data == "[[]]":
      data = "[]"
    query = Query(id=id,criteria=db_criteria,user_id=current_user.id,apikey=database.apikey,name=request.form.get("/name"),data=data)
    db.session.add(query)
    db.session.commit()
    flash("Added query",category="success")
    return redirect(url_for("views.home"))
  databases=Data.query.filter_by(user_id=current_user.id).all()
  if databases == []:
      flash("Please add a database first",category="warning")
      return redirect(url_for("views.add_db"))
  return render_template("add_query.html",user=current_user,databases=databases)
#
@views.route("/edit-query/<id>",methods = ["GET","POST"])
@login_required
def edit_query(id):
  query = Query.query.filter_by(id=id).first()
  if not query:
    flash("No such query",category="error")
    return redirect(url_for("views.home"))
  database = Data.query.filter_by(apikey=query.apikey).first()
  if request.method == "POST":
    if not database:
      flash("No such database",category="error")
      return redirect(url_for("views.home"))
    for check in Query.query.filter_by(user_id=current_user.id).all():
      if check.name == request.form.get("/name") and check.id != id:
        flash("Query with this name already exists",category="error")
        return redirect(url_for("views.edit_query",id=id))
    columns = database.columns.split(",")
    types = database.types.split(",")
    if "" in columns:
      columns.pop(len(columns)-1)
      types.pop(len(types)-1)
    data = database.data
    data = data[1:len(data)-1]
    if data != "":
      data = data[1:len(data)-1]
    data = data.split("],[")
    db_criteria = ""
    idx = 0
    for column in columns:
      if request.form.get(column) != "none":
        db_criteria+=str(idx)+":"+request.form.get(column)+":"+request.form.get("criterion-"+column)+";"
      idx+=1
    if db_criteria == "":
      flash("No criteria",category="error")
      return redirect(url_for("views.edit_query",id=id))
    if data[0] == "":
      data = []
      query.name=request.form.get("/name")
      query.criteria=db_criteria
      query.data="[]"
      db.session.commit()
      flash("Edited query",category="success")
      return redirect(url_for("views.home"))
    else:
      for i in range(len(data)):
        data[i] = data[i].split(",")
    for i in range(len(data)):
      for j in range(len(data[i])):
        if types[j] == "bool":
          if data[i][j].lower() in ["true","y","yes"]:
            data[i][j] = "True"
          else:
            data[i][j] = "False"
    criteria = db_criteria.split(";")
    criteria.remove("")
    to_remove = []
    for i in data:
      for j in criteria:
        if j.split(":")[1] == "equal" and i[int(j.split(":")[0])] != j.split(":")[2]:
            to_remove.append(i)
            break
        if j.split(":")[1] == "nequal" and i[int(j.split(":")[0])] == j.split(":")[2]:
            to_remove.append(i)
            break
        if types[int(j.split(":")[0])] == "date":
          if j.split(":")[1] == "greater":
            if datetime.strptime(i[int(j.split(":")[0])],'%d/%m/%Y') <= datetime.strptime(j.split(":")[2],'%d/%m/%Y'):
              to_remove.append(i)
              break
          if j.split(":")[1] == "less":
            if datetime.strptime(i[int(j.split(":")[0])],'%d/%m/%Y') >= datetime.strptime(j.split(":")[2],'%d/%m/%Y'):
              to_remove.append(i)
              break
        if types[int(j.split(":")[0])] == "time":
          if j.split(":")[1] == "greater":
            if datetime.strptime(i[int(j.split(":")[0])],'HH:MM:SS') <= datetime.strptime(j.split(":")[2],'HH:MM:SS'):
              to_remove.append(i)
              break
          if j.split(":")[1] == "less":
            if datetime.strptime(i[int(j.split(":")[0])],'HH:MM:SS') >= datetime.strptime(j.split(":")[2],'HH:MM:SS'):
              to_remove.append(i)
              break
        if j.split(":")[1] == "greater" and float(i[int(j.split(":")[0])]) <= float(j.split(":")[2]):
            to_remove.append(i)
            break
        if j.split(":")[1] == "less" and float(i[int(j.split(":")[0])]) >= float(j.split(":")[2]):
            to_remove.append(i)
            break
        if j.split(":")[1] == "contains" and j.split(":")[2] not in i[int(j.split(":")[0])]:
            to_remove.append(i)
            break
        if j.split(":")[1] == "startswith" and not i[int(j.split(":")[0])].startswith(j.split(":")[2]):
            to_remove.append(i)
            break
        if j.split(":")[1] == "endswith" and not i[int(j.split(":")[0])].endswith(j.split(":")[2]):
            to_remove.append(i)
            break
    for i in to_remove:
      data.remove(i)
    data = [",".join([str(j) for j in i]) for i in data]
    data = "[["+"],[".join(data)+"]]"
    if data == "[[]]":
      data = "[]"
    query.name=request.form.get("/name")
    query.criteria=db_criteria
    query.data = data
    db.session.commit()
    flash("Edited query",category="success")
    return redirect(url_for("views.home"))
  databases=Data.query.filter_by(user_id=current_user.id).all()
  if databases == []:
      flash("Please add a database first",category="warning")
      return redirect(url_for("views.add_db"))
  return render_template("edit_query.html",user=current_user,database=database,criteria=query.criteria.split(";"),name=query.name)
#
@views.route("/terms_and_conditions")
def tandc():
  return render_template("t_c.html",user=current_user)
@views.route('/404')
def nopage():
  return render_template("404.html",user=current_user)
@views.route('/tutorial')
def tutorial():
  return render_template("tutorial.html",user=current_user)
@views.route("/delete-db",methods = ["POST","GET"])
def delete_database():
  if request.data:
    api_key = json.loads(request.data)["api_key"]
    db.session.delete(Data.query.filter_by(apikey=api_key).first())
    for query in Query.query.filter_by(apikey=api_key).all():
      db.session.delete(query)
    db.session.commit()
    return jsonify({})
  else:
    return redirect(url_for("views.nopage"))
@views.route("/delete-query",methods = ["POST","GET"])
def delete_query():
  if request.data:
    id = json.loads(request.data)["id"]
    db.session.delete(Query.query.filter_by(id=id).first())
    db.session.commit()
    return jsonify({})
  else:
    return redirect(url_for("views.nopage"))
