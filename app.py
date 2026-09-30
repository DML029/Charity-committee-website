import datetime
import os
import csv
import json
import math
from flask import Flask, render_template, request, redirect, url_for, send_file, session
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = "secret-passcode-cookie"

HOUSES = ["Jais", "Javi", "Yibir", "Hafeet"]
MAX_LENGTH = 75
MAX_AMOUNT = 1000000 #one mil

DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_FOLDER, exist_ok=True)
DATA_FILE = os.path.join(DATA_FOLDER, "database.json")
CSV_FILE = os.path.join(DATA_FOLDER, "export.csv")

event_arr = []
class Event:
    _id = 0
    def __init__(self, name, cause, amount, charity, house):
        self.id = Event._id
        Event._id += 1
        self.name = name
        self.date = str(datetime.datetime.now())[:16]
        self.cause = cause
        self.amount = amount
        self.display_amount = f"{float(self.amount):.2f}  Dhs"
        self.charity = charity
        self.house = house
        self.type = "General"

    def calculate_progress(self):
        return "N/A" #General event has no specific goal

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date,
            "cause": self.cause,
            "amount": self.amount,
            "charity": self.charity,
            "house": self.house,
            "type": self.type,
        }
class FundraisingEvent(Event):#inherits everything from Event + adds fundraising goals
    def __init__(self, name, cause, amount, charity, house, goal):
        super().__init__(name, cause, amount, charity, house)
        self.goal = goal
        self.type = "Fundraising"

    def calculate_progress(self):
        progress = (self.amount / self.goal)*100
        return f"{progress:.1f}% complete"

    def to_dict(self):
        data = super().to_dict()
        data["goal"] = self.goal
        return data

def find_event(id):
    #EZ linear search
    for event in event_arr:
        if event.id == id:
            return event
    return None


def validate_event(form, current_event):
    errors = []

    event_name = form["event_name"].strip()
    event_cause = form["event_cause"].strip()
    event_charity = form["event_charity"].strip()
    event_amount = form["event_amount"].strip()
    event_house = form["event_house"]
    event_type = form["event_type"]
    event_goal = form["event_goal"].strip()

    if event_cause == "":
         event_cause = "N/A"

    if event_charity == "":
        event_charity = "N/A"

    if (
        len(event_name) > MAX_LENGTH or
        len(event_cause) > MAX_LENGTH or
        len(event_charity) > MAX_LENGTH 
    ):
        errors.append("EVENT INFORMATION ENTERED IS TOO LONG, MAX CHARACTER COUNT IS 75")

    if event_name == "":
        errors.append("NO NAME SPECIFIED, PLEASE RE-NAME EVENT")

    for event in event_arr:
        if event != current_event and event.name.lower() == event_name.lower():
            errors.append("EVENT ALREADY EXISTS")
            break

    if event_house not in HOUSES:
        errors.append("PLEASE SELECT A VALID HOUSE")

    try:
        if event_amount == "":
            event_amount = "0"
        event_amount = float(event_amount)
        if math.isnan(event_amount) or math.isinf(event_amount):
            errors.append("PLEASE ENTER A VALID NUMBER")
            event_amount = None
    except Exception:
        errors.append("AMOUNT ENTERED MUST BE A VALID NUMBER, PLEASE TRY AGAIN")
        event_amount = None

    if event_amount != None and event_amount < 0:
        errors.append("AMOUNT CANNOT BE NEGATIVE")

    if event_amount != None and event_amount > MAX_AMOUNT:
        errors.append("AMOUNT CANNOT EXCEED 1,000,000 DHS")

    if event_type == "Fundraising":
        try:
            event_goal = float(event_goal)
            if math.isnan(event_goal) or math.isinf(event_goal) or event_goal <= 0:
                errors.append("FUNDRAISING GOAL MUST BE A NUMBER GREATER THAN 0")
        except Exception:
            errors.append("FUNDRAISING GOAL MUST BE A NUMBER GREATER THAN 0")
    else:
        event_goal = None

    if event_amount != None:
        event_amount = round(event_amount, 2)

    cleaned = {
        "name": event_name,
        "cause": event_cause,
        "charity": event_charity,
        "amount": event_amount,
        "house": event_house,
        "type": event_type,
        "goal": event_goal,
    }
    return errors, cleaned

def bubble_sort(a):
    a = a.copy() #sorts events without actually rearranging my real event_arr
    n = len(a)
    for i in range (n-1):
        swapped = False #at the start, nothing has happened yet
        for j in range (n - 1 - i):
            if a[j].amount < a[j + 1].amount:
                a[j], a[j + 1] = a[j +1], a[j]
                swapped = True
        if swapped == False:
            break
    return a

def search_events(arr, search_text):
    results = []
    for event in arr:
        if search_text.lower() in event.name.lower():
            results.append(event)
    return results

def save_data():
    #Criteria 5 -- saves every event to a JSON file. Called automatically after every change
    try:
        data = []
        for event in event_arr:
            data.append(event.to_dict())
        with open(DATA_FILE, "w") as file:
            json.dump(data, file, indent = 4)
        return True
    except Exception:
        return False

def load_data():
    #Criteria file -- load events from JSON when programme starts
    global event_arr
    event_arr = []
    if not os.path.exists(DATA_FILE):
        return "OK"
    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)
        for item in data:
            if item["type"] == "Fundraising":
                event = FundraisingEvent(item["name"], item["cause"], item["amount"], item["charity"], item["house"], item["goal"])
            else:
                event = Event(item["name"], item["cause"], item["amount"], item["charity"], item["house"])

            event.id = item["id"]
            event.date = item["date"]
            event_arr.append(event)
    except Exception:
        os.replace(DATA_FILE, DATA_FILE + ".backup")
        event_arr = []
        return "ERROR"

    highest = -1
    for event in event_arr:
        if event.id > highest:
            highest = event.id
    Event._id = highest + 1
    return "OK"

load_status = load_data()

#home function: display home page
@app.route("/", methods = ["GET"])
def home():
    school = "NLCS"
    return render_template("index.html", school_name = school)
    
#edit function: errors, and adding event info
@app.route("/edit", methods = ["GET", "POST"])
def edit(): 

    if request.method == "POST":
        errors, data = validate_event(request.form, None)

        if len(errors) > 0:
            return render_template("edit.html", errors = errors, houses = HOUSES)
        else:
            if data["type"] == "Fundraising":
                event = FundraisingEvent(data["name"], data["cause"], data["amount"], data["charity"], data["house"], data["goal"])
            else:
                event = Event(data["name"], data["cause"], data["amount"], data["charity"], data["house"])
            event_arr.append(event)
            save_data()
            return redirect("/events")

    return render_template("edit.html", houses = HOUSES)

        
#report function: displays funds
@app.route("/report", methods = ["GET", "POST"])
def report(): 
    if request.method == "POST":
        return redirect("/csv")
    else: 
        total_funds = 0
        try:
            for event in event_arr:
                total_funds += event.amount
        except Exception:
            return redirect("/") 
        return render_template("report.html", total_funds=f"{total_funds:.2f}")

#events function: redirects user to save / load
@app.route("/events", methods=["GET", "POST"])
def events():
    results = event_arr
    search_text = ""

    if request.method == "POST":
        search_text = request.form["search"].strip()
        results = search_events(event_arr, search_text)
        if request.form["action"] == "Sort by amount":
            results = bubble_sort(results)

    errors = []
    if load_status == "ERROR":
        errors.append("THE SAVED DATA COULD NOT BE LOADED, THE FILE MAY BE DAMAGED")
    return render_template('event.html', event_array = results, search = search_text, errors = errors)

#update function: enables ammendments wihtin events
@app.route("/update/<int:id>", methods = ["GET", "POST"])
def update(id):
    event = find_event(id)
    if event == None:
        return redirect('/events')

    if request.method == 'POST':
        errors, data = validate_event(request.form, event)

        if len(errors) > 0:
            return render_template('update.html', event = event, errors = errors, houses = HOUSES)

        event.name = data["name"]
        event.cause = data["cause"]
        event.charity = data["charity"]
        event.house = data["house"]
        event.amount = data["amount"]
        event.display_amount = f"{float(event.amount):.2f} Dhs"
        if event.type == "Fundraising":
            event.goal = data["goal"]
        save_data()
        return redirect('/events')
    else:
        return render_template('update.html', event = event, houses = HOUSES)

#delete function: enables events to be deleted    
@app.route("/delete/<int:id>", methods = ["POST"])
def delete(id):
    event = find_event(id)
    if event != None:
        event_arr.remove(event)
        save_data()
    return redirect('/events')


#CSV function: enables downloads of event data into device within CSV format 
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


