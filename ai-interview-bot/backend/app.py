from flask import Flask
from flask_cors import CORS

from routes.interview import interview_bp
from routes.aptitude  import aptitude_bp
from routes.report    import report_bp
from routes.verification import verify_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(interview_bp, url_prefix="/api/interview")
app.register_blueprint(aptitude_bp,  url_prefix="/api/aptitude")
app.register_blueprint(report_bp,    url_prefix="/api/report")
app.register_blueprint(verify_bp,    url_prefix="/api/verify")

@app.route("/health")
def health():
    return {"status": "running"}

if __name__ == "__main__":
    app.run(debug=True, port=5001)