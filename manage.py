# manage.py
import os
import sys
from app import create_app
from database import db

def create_db():
    """Creates the database tables."""
    app = create_app()
    with app.app_context():
        # Retrieve the database URI from the app config
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"DEBUG: SQLALCHEMY_DATABASE_URI from config: {db_uri}") # NEW DEBUG PRINT

        if db_uri.startswith('sqlite:///'):
            # Extract the file path part (which should now be absolute and with forward slashes)
            db_file_path = db_uri[len('sqlite:///'):]
            
            # Get the directory of the database file
            db_dir = os.path.dirname(db_file_path)
            
            # Ensure the directory exists
            os.makedirs(db_dir, exist_ok=True)
            print(f"Ensured directory exists: {db_dir}")

            db.create_all() # This is the critical call
            print("Database tables created!")
        else:
            print(f"Unsupported database URI scheme: {db_uri}. This manage.py script only handles SQLite file path creation.")
            sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'create_db':
            create_db()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python manage.py create_db")
    else:
        print("No command provided. Usage: python manage.py create_db")