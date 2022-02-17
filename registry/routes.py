from flask import Flask
from app import app
from registry.models import Registry

@app.route('/upload/', methods=['POST', 'GET'])
def upload():
    return Registry().add_data()
