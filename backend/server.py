from flask import Flask,jsonify,request
from flask_cors import CORS
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from database.user_db import *
from database.task_db import *
from database.collaborate_db import*
from database.background_db import *
from components.suggestion import *

app = Flask(__name__)

CORS(app)

# first handeling background tasks      
scheduler = BackgroundScheduler() ## used for : tasks status update 
scheduler.add_job(update_missed_task_status, 'interval', seconds=60)  # calling in each minute
scheduler.start()

def shutdown_scheduler():
    print("\n\nbackground task stopped")
    scheduler.shutdown()

atexit.register(shutdown_scheduler) # stopping function on exit

## base url setup

@app.route('/')
def home():
    return "hello tamal"

@app.route('/<user_id>')
def get_table(user_id):
    return get_user_tasks(user_id)


## get & update User log in ,sign up , update details

@app.route('/signin',methods=["POST"])  #    POST     http://127.0.0.1:8080/signin
def user_signin():
    form_data = request.json
    return sign_in(form_data) # sending json data

@app.route('/signup',methods=["POST"]) #    POST     http://127.0.0.1:8080/signup 
def user_signup():
    form_data = request.json
    return create_new_user(form_data)

@app.route('/user_update',methods=["PUT"])  #    PUT     http://127.0.0.1:8080/user_update
def update_user_details():
    form_data = request.json
    return update_existing_user_details(form_data)



## get and update daily tasks and its subtasks

@app.route("/task",methods=["GET"]) # http://127.0.0.1:8080/task?user_id=sus123
def get_tasks(): 
    user_id = request.args.get('user_id', type=str)
    return get_user_tasks(user_id)

@app.route("/task",methods=["POST","PUT","DELETE"]) # http://127.0.0.1:8080/task
def create_edit_task(): 
    task_data=request.json
    if request.method=="POST":  # 'task_name','task_priority',"task_creator","task_comment","task_parent"
        return task_subtask_table_entry(task_data)  
    
    elif request.method=="PUT": 
        return task_subtask_table_edit(task_data)   # required "task_id"
# MAX EDITABLE task_name, task_priority,task_creator, task_iscollaborative,task_end, task_executor, 
# task_status, task_comment ,task_parent

    elif request.method=="DELETE":  # "task_id","user_id","user_password"
        # return delete_task_subtask(task_data)       
        return nested_delete_task_by_parent_creator(task_data)
    
@app.route("/subtask",methods=["GET"])              # http://127.0.0.1:8080/subtask
def get_subtask(): 
    task_id = request.args.get('task_id', type=str)
    return get_task_subtasks(task_id)

## Add give permission to collaborator
@app.route("/team_update",methods=["POST","DELETE","PUT"])   # http://127.0.0.1:8080/team_update
def editor_add_edit_delete_operation():                   # required user_id, user_password, task_id, task_editor
    auth_editor=request.json                                    
    return editor_add_edit_delete(auth_editor,request.method)

@app.route("/status_comment",methods=["PUT"])                # http://127.0.0.1:8080/status_comment
def status_comment_edit_operation(): # required user_id, user_password, task_id, task_status,task_comment
    auth_editor=request.json
    return status_comment_edit_creator_editor_dynamic(auth_editor)




## adding suggestions
@app.route("/suggestion",methods=["GET"])                # http://127.0.0.1:8080/suggestion
def stggest(): # required user_id, user_password, task_id, task_status,task_comment
    return suggestion_based_on_real_time()
     
if __name__ == '__main__':
    app.run(debug=True, port=8080)
