from base import create_app,db
app =  create_app()
# new test
if __name__ == '__main__':
    app.run(port=7070,threaded=True, debug=True)
