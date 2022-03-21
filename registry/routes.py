from flask import Flask, redirect
from app import app
from registry.models import Registry

@app.route('/upload/', methods=['POST', 'GET'])
def upload():
    Registry().add_data()
    return redirect('/')
