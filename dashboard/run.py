import uvicorn
uvicorn.run('backend.app:app',host='127.0.0.1',port=3000,reload=False)
