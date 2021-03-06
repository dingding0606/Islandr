import os
import sys
import click
from flask_migrate import Migrate, upgrade
from app import faker
from app import search
from app import create_app, db, scheduler
from app.models import User, Post, Group, Join, Message
import json

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

application = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(application, db)

@application.cli.command()
def deploy():
    '''Run deployment tasks'''
    upgrade()
    search.create_index()
    faker.test_user()
    search.update_index()



@application.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Post=Post, Group=Group, Join=Join, Message=Message)

@application.cli.command()
@click.option('--coverage/--no-coverage', default=False,
              help='Run tests under code coverage.')
def test(coverage):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()

@application.cli.command()
@click.option('--length', default=25,
                help='Number of functions to include in the profiler report.')
@click.option('--profile-dir', default=None,
                help='Directory where profiler data files are saved.')
def profile(length, profile_dir):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    application.wsgi_app = ProfilerMiddleware(application.wsgi_app, restrictions=[length],
        profile_dir=profile_dir)
    application.run(debug=False)

@application.template_filter() # Jinja2 custom filter
def str_to_dic(str):
    return json.loads(str)

@application.template_filter() # Jinja2 custom filter: remove ".jpg" part or any extension of a file
def remove_ext(file_name):
    components = file_name.split(".")
    return components[0]
