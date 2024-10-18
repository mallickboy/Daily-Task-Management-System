from database.connect_db import *
from database.user_db import verify_user
from flask import jsonify
TASK_TABLE=""" tt.task_id, tt.task_name, tt.task_priority,
            tt.task_iscollaborative, tt.task_start, tt.task_end,
            tt.task_creator, tt.task_executor, tt.task_status,
            tt.task_comment, tt.task_parent """


def show_table(table_name):
    table_name=table_name.strip()
    cursor = create_connection().cursor()
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        return rows,200
    except Error as e:
        return db_error(e,400),400
    finally:
        cursor.close()

def get_user_tasks(user_id):
    user_id=user_id.strip()
    conn=create_connection()
    cursor=conn.cursor()
    try:
        query=f"""SELECT {TASK_TABLE} FROM task_table tt 
                JOIN user_task_joiner utj ON utj.task_id=tt.task_id 
                WHERE utj.user_id=%s ORDER BY tt.task_start;"""
        cursor.execute(query,(user_id,))
        rows=cursor.fetchall()
        if rows:return jsonify(rows),200
        else:return jsonify(rows),204
    except Error as e:
        return jsonify(db_error(e,400)),400
    finally:
        cursor.close()

def task_subtask_table_entry(data):
    REQUIRED_TASK_FIELD=('task_name','task_priority',
                    "task_creator",
                    "task_comment","task_parent")
    ADD_TASK_DB=""" task_name, task_priority,
                    task_creator,
                    task_comment ,task_parent """
    
    for field in REQUIRED_TASK_FIELD:
        if field not in data:
            return jsonify({"error": f"'{field}' is required."}), 400
    name,priority=data["task_name"],data["task_priority"]
    creator=data["task_creator"].strip()
    comment,parent=data["task_comment"],data["task_parent"]

    conn=create_connection()
    cursor=conn.cursor()
    try:
        query=f"""INSERT INTO task_table ({ADD_TASK_DB}) VALUES (%s,%s,%s,%s,%s);"""
        cursor.execute(query,(name,priority,creator,comment,parent,))
        conn.commit()
        task_id=cursor.lastrowid
        cursor.execute(f"SELECT {TASK_TABLE} from task_table as tt WHERE tt.task_id=%s",(task_id,))
        rows=cursor.fetchall()
        message="task added successfully."
        if parent: # incase of new task is a subtask    parent != null,0
            cursor.execute("INSERT INTO task_subtask_joiner (task_id,subtask_id) VALUES (%s,%s);",
                        (parent,task_id,))
            conn.commit()
            message="inserted new subtask in task_subtask_joiner and "+message
        else:# in case of new task is base task Update user_task_joiner
            cursor.execute("INSERT INTO user_task_joiner (user_id,task_id) VALUES (%s,%s);",
                        (creator,task_id,))
            conn.commit()
            message="inserted new task in user_task_joiner and "+message

        return jsonify({
        "status":201,
        "message": message,
        "return": rows
        }),201
    except Error as e:
        return jsonify(db_error(e,400)),400
    finally:
        cursor.close()

def task_subtask_table_edit(data):
    EDIT_TASK_FIELD=('task_name','task_priority',
                    "task_creator","task_iscollaborative",
                    "task_end","task_executor","task_status",
                    "task_comment","task_parent")
    
    EDIT_TASK_DB=""" task_name, task_priority,
                    task_creator, task_iscollaborative,
                    task_end, task_executor, task_status,
                    task_comment ,task_parent """
    conn=create_connection()
    cursor=conn.cursor()
    if "task_id" not in data or not data["task_id"]:
        return jsonify({"error": f"task_id is required."}), 400
    else:
        id=data["task_id"]
        cursor.execute(f"SELECT {EDIT_TASK_DB} FROM task_table WHERE task_id=%s;",(id,))
        rows=cursor.fetchall()[0]

    new_row=[]
    for i,field in enumerate(EDIT_TASK_FIELD):
        if field not in data:
            data[field]=rows[i]
        new_row.append(data[field])

    if tuple(new_row)==rows: # no changes spotted hence update ignored
        cursor.execute(f"SELECT {TASK_TABLE} from task_table as tt WHERE tt.task_id=%s",(id,))
        rows=cursor.fetchall()
        message="no changes,hence task update ignored."
        return jsonify({
        "status":207,
        "message": message,
        "return": rows
        }),207
    name,priority=data["task_name"],data["task_priority"]
    creator,iscollaborative=data["task_creator"],data["task_iscollaborative"]
    end,executor,status=data["task_end"],data["task_executor"],data["task_status"]
    comment,parent=data["task_comment"],data["task_parent"]

    try:
        update = "task_name = %s, task_priority = %s, task_iscollaborative = %s, task_end = %s, task_executor = %s, task_status = %s, task_comment = %s, task_parent = %s"

        # Prepare the SQL query
        query = f"""UPDATE task_table SET {update} WHERE task_id = %s;"""
        params = (name, priority, iscollaborative, end, executor, status, comment, parent, id,)
        cursor.execute(query, params)
        message="updated task/subtask successfully."

        if parent != rows[-1]: # incase of new parent != old parent   parent changed
            if not parent:
                cursor.execute("DELETE FROM task_subtask_joiner WHERE subtask_id=%s;", (id,))
                # Commit the changes
                conn.commit()
                message=f"deleted row with subtask_id={id} from task_subtask_joiner and "+message
            else:
                cursor.execute("UPDATE task_subtask_joiner SET task_id=%s WHERE subtask_id=%s;",
                            (parent,id,))
                if cursor.rowcount == 0:# If no rows were affected, insert a new record
                    insert_query = """INSERT INTO task_subtask_joiner (task_id, subtask_id) VALUES (%s, %s);"""
                    cursor.execute(insert_query, (parent,id))
                    conn.commit()
                    message="inserted new record in task_subtask_joiner and "+message
                else:message="updated task_subtask_joiner and "
                conn.commit()
        conn.commit()

        cursor.execute(f"SELECT {TASK_TABLE} from task_table as tt WHERE tt.task_id=%s",(id,))
        rows=cursor.fetchall()
        return jsonify({
        "status":200,
        "message": message,
        "return": rows
        }),200
    except Error as e:
        return jsonify(db_error(e,400)),400
    finally:
        cursor.close()
        
def get_task_subtasks(task_id):
    conn=create_connection()
    cursor=conn.cursor()
    try:
        query=f"""select {TASK_TABLE} from task_subtask_joiner tsj 
                JOIN task_table tt ON tt.task_id=tsj.subtask_id 
                WHERE tsj.task_id=%s ORDER BY tt.task_start;"""
        cursor.execute(query,(task_id,))
        rows=cursor.fetchall()
        if rows:return jsonify(rows),200
        else:return jsonify(rows),204
    except Error as e:
        return jsonify(db_error(e,400)),400
    finally: 
        cursor.close()

def delete_task_subtask(data): # need : task_id, user_id (of current user)
    conn=create_connection()
    cursor=conn.cursor()
    for field in ("task_id","user_id"):
        if field not in data:
            return jsonify({"error": f"'{field}' is required."}), 400
    try:
        id,curr_user=data["task_id"],data["user_id"].strip()
        cursor.execute("SELECT task_id,task_name,task_creator,task_parent from task_table WHERE task_id=%s;",(id,))
        rows=cursor.fetchall()
        if rows:
            rows=rows[0]
            creator,parent=rows[-2],rows[-1]
        else:return jsonify({
        "status":400,
        "message": "row not found.",
        "return": []
        }),400

        if curr_user==creator:
            if parent : # is a subtask/child of a parent
                cursor.execute("DELETE from  task_subtask_joiner WHERE subtask_id=%s;",(id,))
                conn.commit()
                msg="deleted from task_subtask_joiner and "
            else:
                cursor.execute("DELETE from  user_task_joiner WHERE user_id=%s and task_id=%s;",(creator,id,))
                conn.commit()
                msg="deleted from user_task_joiner and "
            cursor.execute("DELETE from  task_table WHERE task_id=%s;",(id,))
            conn.commit()
            return jsonify({
        "status":200,
        "message": msg+"task row deleted successfully.",
        "return": rows
        }),200
        else:
            return jsonify({
        "status":401,
        "message": "unautorized action terminated.",
        "return": []
        }),401
    except Error as e:
        return jsonify(db_error(e,400)),400
    finally: 
        cursor.close()