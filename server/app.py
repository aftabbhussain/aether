from fastapi import FastAPI

app = FastAPI(title='Aether API')

@app.get('/health')
def health():
    return {'status': 'ok'}
