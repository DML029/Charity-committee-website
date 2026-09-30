import datetime
import pickle
import os
import csv
from flask import Flask, render_template, request, redirect, url_for, send_file

app = Flask(__name__)


event_arr = []
class Event:
    _id = 0
    def __init__(self, name, cause, amount, charity):
        self.id = Event._id
        Event._id += 1
        self.name = name
        self.date = str(datetime.datetime.now())
        self.cause = cause
        self.amount = amount
        self.display_amount = f"{float(self.amount):.2f}  Dhs"
        self.charity = charity


@app.route("/", methods = ["GET"])
def home():
    school = "NLCS"
    return render_template("index.html", school_name = school)
    

@app.route("/edit", methods = ["GET", "POST"])
def edit(): 
    if request.method == "POST":
        errors = []

        event_name = request.form["event_name"].strip()
        event_cause = request.form["event_cause"].strip()
        event_charity = request.form["event_charity"].strip()
        event_amount = request.form["event_amount"].strip()

        if event_cause == "":
            event_cause = "N/A"

        if event_charity == "":
            event_charity = "N/A"

        MAX_LENGTH = 75
        if (
            len(event_name) > MAX_LENGTH or
            len(event_cause) > MAX_LENGTH or
            len(event_charity) > MAX_LENGTH
        ):
            errors.append("EVENT INFORMATION ENTERED IS TOO LONG, MAXIMUM 75 CHARACTERS")

        if event_name == "":
            errors.append("NO NAME SPECIFIED, PLEASE RE-NAME EVENT")

        for event in event_arr:
            if event.name == event_name:
                errors.append("EVENT ALREADY EXISTS")
                break

        try:
            if event_amount == "":
                event_amount = "0"
            event_amount = float(event_amount)

        except Exception:
            errors.append("AMOUNT ENTERED MUST BE A VALID NUMBER")
            event_amount = None

        if event_amount != None and event_amount < 0:
            errors.append("AMOUNT CANNOT BE NEGATIVE")

        if len(errors) > 0:
            return render_template("edit.html", errors = errors)
        else:
            event = Event(event_name, event_cause, event_amount, event_charity)
            event_arr.append(event)

            return redirect ("/events")
        
    return render_template("edit.html")


@app.route("/report", methods = ["GET", "POST"])
def report(): 
    if request.method == "POST":
        return redirect("/csv")
    else: 
        total_funds = 0
        try:
            for event in event_arr:
                total_funds += event.amount
        except Exception as excp:
            print(excp)
            return redirect("/") 
        return render_template("report.html", total_funds=f"{total_funds:.2f}")

@app.route("/events", methods=["GET","POST"])
def events():
    if request.method == "POST":
        if request.form["data"] == "Save Data":
            return redirect("/save")
        elif request.form["data"] == "Load Data":
            return redirect("/load")               
    else:
        return render_template("event.html", event_array = event_arr)


@app.route("/update/<int:id>", methods = ["GET", "POST"])
def update(id):
    errors = []

    event = None
    for i in event_arr:
        if i.id == id: 
            event = i
            break
    if event == None:
        return
    
    if request.method == 'POST':
        new_name = request.form['content']

        if new_name == "":
            errors.append("EVENT NAME CANNOT BE EMPTY")

        for i in event_arr:
            if i.name == new_name:
                errors.append("EVENT NAME IS ALREADY IN USE")
                break
        event.name = new_name   
        if len(errors) > 0:
            return render_template('update.html', event = event, errors = errors)
        else:
            return redirect('/events')

    else:
        return render_template('update.html', event = event)
    
@app.route("/delete/<int:id>", methods = ["GET", "POST"])
def delete(id):
    event = None
    for i in event_arr:
        if i.id == id: 
            event = i
            break
    if event == None:
        return redirect('/events')
    else:       
        Event._id -= 1
        idx = event_arr.index(event)
        for i in range (idx+1, len(event_arr)):
            shift_event = event_arr[i]
            shift_event.id -= 1

        event_arr.remove(event)
        return redirect('/events')

    
@app.route("/save")
def save():
    errors = []
    try:
        with open("data/database.pkl", "wb") as file:
            pickle.dump(event_arr, file)
    except Exception:
        errors.append("UNABLE TO SAVE DATA INTO PICKLE FILE")

    if len(errors) > 0:
        return render_template("events.html", errors = errors)
    else:
        return redirect("/events")

@app.route("/load")
def load():
    global event_arr

    errors = []

    if os.path.exists("data/database.pkl"):
        try:
            with open("data/database.pkl", "rb") as file:
                event_arr = pickle.load(file)
        except Exception:
            errors.append("UNABLE TO LOAD DATA FROM PICKLE FILE")

    Event._id = len(event_arr)

    if len(errors) > 0:
        return render_template("events.html", errors = errors)
    else:
        return redirect("/events")
    
@app.route("/csv")
def csv_writing():
    errors = []
    try:
        with open("data/export.csv", "w", newline='') as csvfile:
            headers = ['Name', 'Date', 'Cause', 'Amount', 'Charity', 'ID']

            csvwriter = csv.DictWriter(csvfile, delimiter=',', fieldnames = headers)
            csvwriter.writeheader()

            for event in event_arr:
                csvwriter.writerow({
                    "Name": event.name,
                    "Date": event.date,
                    "Cause": event.cause,
                    "Amount": event.amount,
                    "Charity": event.charity,
                    "ID": event.id,
                })
    except Exception:
        errors.append("UNABLE TO WRITE DATA TO A CSV FILE, pls contact tech support")

    if len(errors) > 0:
        return render_template("/report.html", errors = errors)
    else:
        return send_file(
            "data/export.csv",
            as_attachment=True,
            download_name="charity_events.csv"
        )







if __name__ == "__main__":
    app.run(debug=True)


