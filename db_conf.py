from app import app
from flaskext.mysql import MySQL

mysql = MySQL()
 
# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'HeniMeni1'
app.config['MYSQL_DATABASE_DB'] = 'contact_api'
app.config['MYSQL_DATABASE_HOST'] = 'contact-api-db.cwskymllgfao.us-east-1.rds.amazonaws.com'
app.config['PORT'] = 3306
mysql.init_app(app)