"""
PromptVault - application factory.

`create_app()` builds and configures the Flask app. Keeping this in a function
(the "factory pattern") makes the project easy to test and to deploy.
"""
import os

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__)

    # Where the repository lives on GitHub. Change this once you create your repo.
    app.config.update(
        SITE_NAME="PromptVault",
        GITHUB_REPO=os.environ.get("PV_GITHUB_REPO", "your-username/promptvault"),
        SITE_URL=os.environ.get("PV_SITE_URL", "http://127.0.0.1:5000"),
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    )
    if test_config:
        app.config.update(test_config)

    from . import routes
    app.register_blueprint(routes.bp)
    routes.register_helpers(app)
    return app
