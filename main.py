import json
import datetime
from app import app
from db_conf import mysql
from flask import jsonify
from flask import flash, request, Flask
from flask_restful import Resource, Api
from flask_swagger_ui import get_swaggerui_blueprint
import os

app = Flask(__name__)
api = Api(app, prefix="/api/v1")

### swagger specific ###
SWAGGER_URL = '/api/v1/swagger'
API_URL = '/schema/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Contact_API_Code_Challenge"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)
### end swagger specific ###
#app.register_blueprint(request_api.get_blueprint())


# 1 Operations: POST / GET / PUT / PATCH / DELETE
# 2 Delete operation just updates the status in DB (Soft Delete). 
# 3 All queries involving the active flow (GET / PUT / PATCH)  will ignore all such entries with the condition ‘del_flag = true’
# 4 By default when a new record is created in database. del_flag is set to False
# 5 PUT and PATCH operation do not allow updating the primary fields(first_name, last_name, dob and gender)

#This class holds the functions for adding and retreiving Contact Collections. Input body is expected to be an arry 
class Contact_Collection(Resource):
    #This function adds Contact identifocation information in Identification table, gets the id and adds cmmunication and address information against that identification id.
    def post(self):
        try:
            sql1 = "INSERT INTO identification (first_name, last_name, dob, gender, title) VALUES (%s, %s, %s, %s, %s)"
            sql2 = "SELECT id FROM address WHERE type = %s AND num = %s AND street = %s AND unit = %s AND city = %s AND state = %s AND zipcode = %s"
            sql3 = "INSERT INTO address(type, num, street, unit, city, state, zipcode) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            sql4 = "INSERT INTO identification_address(identification_id, address_id) VALUES (%s, %s)"
            sql5 = "INSERT INTO communication(identification_id, type, preferred, value)VALUES(%s, %s, %s, %s)"
           
            json_arr = request.json
            for _json in json_arr:
                identification_data = (_json['Identification']['FirstName'], _json['Identification']['LastName'], _json['Identification']['DOB'], _json['Identification']['Gender'], _json['Identification']['Title'])
                conn = mysql.connect()
                cursor = conn.cursor()
                #insert indentification
                cursor.execute(sql1, identification_data)
                conn.commit()
                #get identification id
                identification_id = cursor.lastrowid
                #insert addresses
                for a in _json['Address']:
                    address_data = (a['type'], a['number'], a['street'], a['Unit'], a['City'], a['State'], a['zipcode'])
                    cursor.execute(sql2, address_data)
                    add_result = cursor.fetchall()
                    if len(add_result) > 0:
                        address_id = add_result[0]
                    else:
                        cursor.execute(sql3, address_data)
                        conn.commit()
                        #get address_id
                        address_id = cursor.lastrowid
                    #insert identity_address
                    identity_address_data = (identification_id, address_id )
                    cursor.execute(sql4, identity_address_data)
                    conn.commit()


                #insert communication
                for c in _json['Communication']:
                    if 'preferred' in  c:
                        preference = c['preferred']
                    else:
                         preference = 'false'
                    communication_data = (identification_id, c['type'], preference, c['value'])
                    cursor.execute(sql5, communication_data)
                    conn.commit()
            
            try:
                resp = jsonify("Contact Added successfully")
                resp.status_code = 200
                return resp  
            except Exception as e:
                print(e)
                return internal_error(e)     

        except Exception as e:
            print(e)
            return internal_error(e)

        finally:
            cursor.close() 
            conn.close()

    #This function gets List of all Active Contactswith del_flag =  false) . Query parameter "limit" is used to limit the number of rows returned 
    def get(self):
        try:
            #get identification details
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM identification WHERE del_flag=%s Limit "+request.args.get('limit'), "False")
            rows = cursor.fetchall()
            if rows == None:
                return not_found()
            else:
                contact_list = []
                for identification_row in rows:
                    i = 0
                    json_i = {"FirstName": identification_row[1] , "LastName": identification_row[2], "DOB": identification_row[3].strftime('%m/%d/%Y'), "Gender": identification_row[4], "Title": identification_row[5]}
                    identification_id = identification_row[0]  
                    sel_data = ('False', identification_id)
                    #get contact details
                    cursor.execute("SELECT type, preferred, value FROM communication WHERE del_flag=%s AND identification_id=%s", sel_data)
                    row_headers = [y[0] for y in cursor.description]
                    contact_rows = cursor.fetchall()
                    json_c = []
                    for row in contact_rows:
                        json_c.append(dict(zip(row_headers,row)))
  
                    #get address details
                    cursor.execute("SELECT a.type, a.num, a.street, a.unit, a.city, a.state, a.zipcode FROM address a, identification_address ad WHERE a.id = ad.address_id  AND del_flag=%s AND ad.identification_id=%s", sel_data)
                    row_headers = [y[0] for y in cursor.description]
                    address_rows = cursor.fetchall()
                    json_d = []
                    for row in address_rows:
                        json_d.append(dict(zip(row_headers,row)))
            
                    get_dict = {
                      " Identification": json_i,
                      "Address": json_d,
                      "Communication": json_c
                    }  
                
                    contact_list.append(get_dict)
            
                resp = jsonify(contact_list)
                resp.status_code = 200
                return resp


        except Exception as e:
            print(e)
            return internal_error(e)

        finally:
            cursor.close() 
            conn.close()


class Contact(Resource):
    def get(self):
        try:
            #get idnetification details
            req_params = (request.args.get('fname'),request.args.get('lname'),request.args.get('dob'),'False')
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM identification WHERE first_name=%s AND last_name=%s AND dob=%s AND del_flag=%s", req_params)
            identification_row = cursor.fetchone()
            if identification_row == None:
                return not_found()
            else:
                json_i = {"FirstName": identification_row[1] , "LastName": identification_row[2], "DOB": identification_row[3].strftime('%m/%d/%Y'), "Gender": identification_row[4], "Title": identification_row[5]}
                identification_id = identification_row[0]  
                sel_data = ('False', identification_id)
                #get contact details
                cursor.execute("SELECT type, preferred, value FROM communication WHERE del_flag=%s AND identification_id=%s", sel_data)
                row_headers = [y[0] for y in cursor.description]
                contact_rows = cursor.fetchall()
                json_c = []
                for row in contact_rows:
                    json_c.append(dict(zip(row_headers,row)))
  
                #get address details
                cursor.execute("SELECT a.type, a.num, a.street, a.unit, a.city, a.state, a.zipcode FROM address a, identification_address ad WHERE a.id = ad.address_id  AND del_flag=%s AND ad.identification_id=%s", sel_data)
                row_headers = [y[0] for y in cursor.description]
                address_rows = cursor.fetchall()
                json_d = []
                for row in address_rows:
                    json_d.append(dict(zip(row_headers,row)))
            
                get_dict =	{
                  " Identification": json_i,
                  "Address": json_d,
                  "Communication": json_c
                }   
            
                resp = jsonify(get_dict)
                resp.status_code = 200
                return resp

        except Exception as e:
                print(e)

        finally:
            cursor.close() 
            conn.close()


    def delete(self):
        try:
            #get identification details
            req_params = (request.args.get('fname'),request.args.get('lname'),request.args.get('dob'),'False')
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM identification WHERE first_name=%s AND last_name=%s AND dob=%s AND del_flag = %s", req_params)
            row = cursor.fetchone()
            if row == None:
                return not_found()
            else:
                identification_id = row[0]
                del_data = ('True', identification_id)
                #soft delete identification table(sets del_flag t0 true)
                cursor.execute("UPDATE identification SET del_flag = %s WHERE id=%s", del_data)
                conn.commit()
                 # soft delete all communication data for Contact (sets del_flag to true)
                cursor.execute("UPDATE communication SET del_flag = %s WHERE identification_id=%s", del_data)
                conn.commit()
                #soft delete all adress data for Contact (sets del_flag to true)
                cursor.execute("UPDATE identification_address SET del_flag = %s WHERE identification_id=%s", del_data)
                conn.commit()
                resp = jsonify("Contact Deleted Succesfully")
                resp.status_code = 200
                return resp

        except Exception as e:
                print(e)

        finally:
            cursor.close() 
            conn.close()


# Updates the Contact details with the new details if contact exists already with del_flag as False. Creates a new contact if it doesn't exist already or is not active
# 1. Supports only add and remove operations for Communication and Address
# 2. Suports only replace operation for Identification data. Allows to replace only the Title value
# 3. Incase of add operation for Address and Communication, existing communication and address information is not flagged as deleted
# 4. for value, a json object withh all address or commincation details is passed
    def put(self):
        conn = mysql.connect()
        cursor = conn.cursor()
        try:
            #get identification details
            req_params = (request.args.get('fname'),request.args.get('lname'),request.args.get('dob'), "False")
            _json = request.json
            #queries
            sql1 = "INSERT INTO identification (first_name, last_name, dob, gender, title) VALUES (%s, %s, %s, %s, %s)"
            sql2 = "SELECT id FROM address WHERE type = %s AND num = %s AND street = %s AND unit = %s AND city = %s AND state = %s AND zipcode = %s"
            sql3 = "INSERT INTO address(type, num, street, unit, city, state, zipcode) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            sql4 = "INSERT INTO identification_address(identification_id, address_id) VALUES (%s, %s)"
            sql5 = "INSERT INTO communication(identification_id, type, preferred, value)VALUES(%s, %s, %s, %s)"      
            #get identification_id
            cursor.execute("SELECT id FROM identification WHERE first_name=%s AND last_name=%s AND dob=%s AND del_flag=%s", req_params)
            row = cursor.fetchone()
            if row == None: #Add the contact if does not exist already
                identification_data = (_json['Identification']['FirstName'], _json['Identification']['LastName'], _json['Identification']['DOB'], _json['Identification']['Gender'], _json['Identification']['Title'])
                conn = mysql.connect()
                cursor = conn.cursor()
                #insert indentification
                cursor.execute(sql1, identification_data)
                conn.commit()
                #get identification id
                identification_id = cursor.lastrowid
                #insert addresses
                for a in _json['Address']:
                    address_data = (a['type'], a['number'], a['street'], a['Unit'], a['City'], a['State'], a['zipcode'])
                    cursor.execute(sql2, address_data)
                    add_result = cursor.fetchall()
                    if len(add_result) > 0:
                        address_id = add_result[0]
                    else:
                        cursor.execute(sql3, address_data)
                        conn.commit()
                        #get address_id
                        address_id = cursor.lastrowid
                    #insert identity_address
                    identity_address_data = (identification_id, address_id )
                    cursor.execute(sql4, identity_address_data)
                    conn.commit()


                #insert communication
                for c in _json['Communication']:
                    communication_data = (identification_id, c['type'], c['preferred'], c['value'])
                    cursor.execute(sql5, communication_data)
                    conn.commit()
                    resp = jsonify("Contact Added Succesfully")
                    resp.status_code = 200

            else: #update the contact if exists already
                identification_id = row[0]
                identification_data = (_json['Identification']['Title'], identification_id)
                #soft delete identification table
                cursor.execute("UPDATE identification SET title = %s WHERE id=%s", identification_data)
                conn.commit()
                 # soft del old communication data for contact
                del_data = ('True', identification_id)
                cursor.execute("UPDATE communication SET del_flag = %s WHERE identification_id=%s", del_data)
                conn.commit()
                #add new communication data
                for c in _json['Communication']:
                    communication_data = (identification_id, c['type'], c['preferred'] , c['value'])
                    cursor.execute(sql5, communication_data)
                    conn.commit()

                #soft delete all adress data for contact
                cursor.execute("UPDATE identification_address SET del_flag = %s WHERE identification_id=%s", del_data)
                conn.commit()
                 #insert addresses
                for a in _json['Address']:
                    address_data = (a['type'], a['number'], a['street'], a['Unit'], a['City'], a['State'], a['zipcode'])
                    cursor.execute(sql2, address_data)
                    add_result = cursor.fetchall()
                    if len(add_result) > 0:
                        address_id = add_result[0]
                    else:
                        cursor.execute(sql3, address_data)
                        conn.commit()
                        #get address_id
                        address_id = cursor.lastrowid
                    #insert identity_address
                    identity_address_data = (identification_id, address_id )
                    cursor.execute(sql4, identity_address_data)
                    conn.commit()


            resp = jsonify("Contact Updated Succesfully")
            resp.status_code = 200
            return resp

        except Exception as e:
                print(e)

        finally:
            cursor.close() 
            conn.close()
#Partial Update 
# To handle partial updates for the contact
# 1. Supports only add and remove operations for Communication and Address
# 2. Suports only replace operation for Identification data. Allows to replace only the Title value
# 3. Incase of add operation for Address and Communication, existing communication and address information is not flagged as deleted
# 4. for value, a json object withh all address or commincation details is passed
    def patch(self):
        conn = mysql.connect()
        cursor = conn.cursor()
        try:
            resp = jsonify("Contact Updated Succesfully")
            resp.status_code = 200
            #get identification details
            req_params = (request.args.get('fname'),request.args.get('lname'),request.args.get('dob'),'False')
            cursor.execute("SELECT id FROM identification WHERE first_name=%s AND last_name=%s AND dob=%s AND del_flag=%s", req_params)
            row = cursor.fetchone()
            if row == None:
                return not_found()
            else:
                identification_id = row[0]
                json_arr = request.json
                for item in json_arr:
                    operation = item['op']
                    path = (item['path'].split("/"))
                    if operation == "add" and path[1] == "Address":
                        #in patch we will not update the existing address data for contact/ Put method available for that
                        #insert addresses
                        address_data = (item['value']['type'], item['value']['number'], item['value']['street'], item['value']['Unit'], item['value']['City'], item['value']['State'], item['value']['zipcode'])
                        cursor.execute("SELECT id FROM address WHERE type = %s AND num = %s AND street = %s AND unit = %s AND city = %s AND state = %s AND zipcode = %s", address_data)
                        add_result = cursor.fetchall()
                        if len(add_result) > 0:
                            address_id = add_result[0]
                        else:
                            cursor.execute("INSERT INTO address(type, num, street, unit, city, state, zipcode) VALUES (%s, %s, %s, %s, %s, %s, %s)", address_data)
                            conn.commit()
                            #get address_id
                            address_id = cursor.lastrowid
                            #insert identity_address
                            identity_address_data = (identification_id, address_id )
                            cursor.execute("INSERT INTO identification_address(identification_id, address_id) VALUES (%s, %s)", identity_address_data)
                            conn.commit()
                        
                    elif operation == "add" and path[1] == "Communication":
                        communication_data = (identification_id, item['value']['type'], item['value']['preferred'], item['value']['value'])
                        cursor.execute("INSERT INTO communication(identification_id, type, preferred, value)VALUES(%s, %s, %s, %s)", communication_data)
                        conn.commit()
                    elif operation == "remove" and path[1] == "Communication":
                         # soft del old communication data for contact
                        del_data = ('True', identification_id)
                        cursor.execute("UPDATE communication SET del_flag = %s WHERE identification_id=%s", del_data)
                        conn.commit()
                    elif operation == "remove" and path[1] == "Address":
                         #soft delete all adress data for contact
                        del_data = ('True', identification_id)
                        cursor.execute("UPDATE identification_address SET del_flag = %s WHERE identification_id=%s", del_data)
                        conn.commit()
                    elif operation == "replace" and path[1] == "Title":
                        identification_data = (item['value'], identification_id)
                        #soft delete identification table
                        cursor.execute("UPDATE identification SET title = %s WHERE id=%s", identification_data)
                        conn.commit()
                    elif operation == "remove" and path[1] == "Title":
                        identification_data = ("", identification_id)
                        #soft delete identification table
                        cursor.execute("UPDATE identification SET title = %s WHERE id=%s", identification_data)
                        conn.commit()
                    else:
                        resp = jsonify("Operation not supported")
                        resp.status_code = 400
       
            return resp
        except Exception as e:
                print(e)
          

        finally:
            cursor.close() 
            conn.close()

#Resource Routing
api.add_resource(Contact_Collection, '/contacts')
api.add_resource(Contact, '/contact')

@app.errorhandler(404)
def not_found(error=None):
    message = {
        'status': 404,
        'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp

def internal_error(e):
    message = {
        'status': 500,
        'message': 'Internal Server error occured ',
    }
    resp = jsonify(message)
    resp.status_code = 500

    return resp

if __name__ == '__main__':
    app.run(debug=True)
