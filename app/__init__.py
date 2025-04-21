from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

from app import routes
