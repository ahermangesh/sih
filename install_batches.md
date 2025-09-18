# FloatChat Dependency Installation Plan

## Batch Installation Strategy

### Batch 1: Core Utilities & Configuration (10 packages)
```
python-dotenv==1.1.1
pyyaml==6.0.1
toml==0.10.2
python-dateutil==2.8.2
pytz==2023.3
marshmallow==3.20.1
cerberus==1.3.5
pathlib2==2.3.7
structlog==25.4.0
sqlparse==0.4.4
```

### Batch 2: Database Core (5 packages)
```
sqlalchemy==2.0.43
alembic==1.13.1
psycopg2-binary==2.9.10
asyncpg==0.29.0
redis==6.4.0
```

### Batch 3: HTTP & API (5 packages)
```
httpx==0.28.1
aiohttp==3.9.1
requests==2.31.0
python-multipart==0.0.6
python-json-logger==2.0.7
```

### Batch 4: Security & Auth (4 packages)
```
cryptography==46.0.1
passlib==1.7.4
python-jose[cryptography]==3.5.0
prometheus-client==0.19.0
```

### Batch 5: Data Processing Core (5 packages)
```
pandas==2.3.2
numpy==2.2.2
scipy==1.14.1
pyproj==3.6.1
shapely==2.0.2
```

### Batch 6: Google AI Services (3 packages)
```
google-generativeai==0.3.2
google-ai-generativelanguage==0.4.0
langdetect==1.0.9
```

### Batch 7: Vector Database (3 packages)
```
faiss-cpu==1.12.0
chromadb==1.1.0
sentence-transformers==5.1.0
```

### Batch 8: ARGO Data Processing (4 packages)
```
argopy==0.1.15
netCDF4==1.7.2
xarray==2025.9.0
geoalchemy2==0.14.2
```

### Batch 9: Frontend & Visualization (4 packages)
```
streamlit==1.28.2
plotly==5.17.0
folium==0.15.1
Pillow==11.0.0
```

### Batch 10: Optional Voice Processing (4 packages)
```
SpeechRecognition==3.10.0
gTTS==2.4.0
pydub==0.25.1
deep-translator==1.11.4
```

## Installation Commands

Each batch can be installed with:
```bash
pip install package1==version1 package2==version2 ...
```

Test server after each batch to identify exactly where issues occur.
