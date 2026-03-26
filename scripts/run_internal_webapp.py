from matanyone2.webapp.api.app import create_app
from matanyone2.webapp.config import WebAppSettings


app = create_app(settings=WebAppSettings())
