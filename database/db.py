from flask_sqlalchemy import SQLAlchemy

# Centralized SQLAlchemy database instance
# Exported here to prevent circular imports between app.py and models
db = SQLAlchemy()
