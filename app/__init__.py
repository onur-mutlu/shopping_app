from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.secret_key = 'my-ultra-strong-and-unique-key'

from app import routes
