"""
run.py - start the development server:   python run.py
Then open http://127.0.0.1:5000 in your browser.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True reloads the server when you edit code and shows helpful errors.
    # Never use debug=True on a public server (see docs/DEPLOYMENT.md).
    app.run(debug=True)
