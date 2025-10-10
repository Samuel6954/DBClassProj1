from flask import Blueprint

bp = Blueprint('api', __name__)

from . import api  # noqa: E402,F401

