from flask import Flask,jsonify,request
from flask_cors import CORS
from database.user_db import *
from database.task_db import *
from database.collaborate_db import*

def db_error(e,code):return {"status": code,"message": str(e),"return":[]}

def editor_add_edit_delete(data,method):   # add,edit,remove row from user_task_joiner
    try:        # data acess and user authentication
        user_id,user_password= data["user_id"].strip(),data["user_password"].strip()
        task_id,task_editor=data["task_id"],data["task_editor"].strip()
        res,status_code=verify_user(user_id,user_password)
        if status_code !=200:
            return res,status_code
    except Exception as e:
        return db_error(e,400),400
    verified_msg="verification successful, "
    # after authentication
    try:
        conn=create_connection()
        cursor=conn.cursor()
        cursor.execute(f"""SELECT task_creator 
                       FROM task_table WHERE task_id=%s;""",(task_id,))
        rows=cursor.fetchall()
        print(rows)
        task_creator=rows[0][0]
        print(user_id==task_creator)

        if user_id==task_creator:       # attempt made by creator
            cursor.execute("""SELECT user_id,task_id from user_task_joiner 
                           WHERE user_id=%s AND task_id=%s ;""",(task_editor,task_id,)) # 
            rows=cursor.fetchall()
            print(rows)
            if rows:    # verified , creator and old data hence delete data  in DELETE
                if method=="POST":message,status_code="already shared hence ignored.",200
                else:
                    cursor.execute("""DELETE FROM user_task_joiner
                                   WHERE user_id=%s AND task_id=%s;""",(task_editor,task_id,))
                    conn.commit()
                    message,status_code=f"removed permission of '{task_editor}' from user_task_joiner",200
            else:       # verified , creator and new data hence add data  in POST
                if method=="POST":
                    cursor.execute("""INSERT INTO user_task_joiner (user_id,task_id) 
                                VALUES (%s,%s)""",(task_editor,task_id,))
                    conn.commit() # writing changes to the database
                    message,status_code=f"sharing with '{task_editor}', new row added in user_task_joiner.",201
                else:
                    message,status_code=f"enter a valid permission first for '{task_editor}' to remove it from user_task_joiner.",400
            print(message)
            return jsonify({
            "status":status_code,
            "message": message,
            "return": [task_id,task_creator,task_editor]
            }),status_code
        return jsonify({
            "status":401,
            "message": f"only the creator '{task_creator}' can add/delete editor '{task_editor}' to a task/routine.",
            "return": []
            }),401
    except Exception as e:
        print(verified_msg)
        return db_error(e,400),400
    finally:
        cursor.close()
