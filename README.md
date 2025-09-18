# FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data

**SIH 25 Problem Statement ID: 25040**  
**Organization:** Ministry of Earth Sciences (MoES) - Indian National Centre for Ocean Information Services (INCOIS)

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🌊 Overview

FloatChat is an enterprise-grade AI-powered conversational system that democratizes access to ARGO oceanographic data through natural language processing and voice interaction. Users can explore complex ocean datasets through intuitive conversations in multiple languages (English/Hindi).

### Key Features

- 🤖 **AI-Powered Chat**: Natural language queries using Google Gemini Studio API
- 🎤 **Voice Interface**: Multilingual voice input/output with real-time processing
- 🗺️ **Interactive Visualizations**: Geospatial maps and scientific charts
- 📊 **6-Year Dataset**: 2,056 NetCDF files (9.77GB) from 2020-2025
- 🔍 **RAG Pipeline**: Vector similarity search with FAISS/ChromaDB
- 🌐 **Multilingual**: Support for English, Hindi, and regional languages
- 📈 **Real-time Analytics**: Temporal trend analysis and pattern recognition

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 16+ (for React frontend)
- PostgreSQL 15+ with PostGIS
- Redis 6+
- Docker & Docker Compose

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-org/floatchat.git
cd floatchat
```

2. **Backend Setup**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

3. **Install backend dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

4. **Frontend Setup**
```bash
cd react-dashboard
npm install
cd ..
```

5. **Configure environment**
```bash
cp env.example .env
# Edit .env with your API keys and database credentials

# Configure frontend
cd react-dashboard
cp .env.example .env
# Edit with backend URLs (default: http://localhost:8000)
cd ..
```

6. **Start services**
```bash
docker-compose up -d postgres redis
```

7. **Initialize database**
```bash
python scripts/init_database.py
python scripts/load_sample_data.py
```

8. **Run the applications**

**Backend:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (in a new terminal):**
```bash
cd react-dashboard
npm start
```

9. **Access the applications**
- **Modern React Dashboard**: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- Legacy Frontend: http://localhost:8501
- Health Check: http://localhost:8000/health

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FloatChat System                        │
├─────────────────────────────────────────────────────────────────┤
│  Frontend Layer (Streamlit/Dash)                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Voice UI      │  │   Chat Widget   │  │  Visualization  │ │
│  │  - Microphone   │  │  - Text Input   │  │  - Maps         │ │
│  │  - Speaker      │  │  - History      │  │  - Charts       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway Layer (FastAPI)                                   │
│  /api/chat | /api/voice/* | /api/floats | /api/visualize       │
├─────────────────────────────────────────────────────────────────┤
│  AI Processing Layer                                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Speech Engine  │  │   Gemini LLM    │  │   RAG Pipeline  │ │
│  │  - STT/TTS      │  │  - Query Parse  │  │  - Vector DB    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   PostgreSQL    │  │   Vector DB     │  │   ARGO Data     │ │
│  │  + PostGIS      │  │  FAISS/Chroma   │  │   2,056 Files   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Dataset

### ARGO Float Data (2020-2025)
- **Files:** 2,056 NetCDF files
- **Size:** 9.77 GB
- **Coverage:** Daily ocean profiles
- **Parameters:** Temperature, Salinity, Pressure, BGC data
- **Regions:** Focus on Indian Ocean with global coverage

### Example Queries
- "Show me temperature trends in Arabian Sea over the last 3 years"
- "Compare salinity patterns between 2020 and 2024 monsoon seasons"
- "मुझे बंगाल की खाड़ी में तापमान प्रोफाइल दिखाओ" (Hindi)
- "What were ocean conditions during Cyclone Amphan in 2020?"

## 🛠️ Development

### Project Structure
```
floatchat/
├── app/                          # Main application code
│   ├── main.py                   # FastAPI app entry point
│   ├── core/                     # Core configuration
│   ├── api/                      # API routes
│   ├── services/                 # Business logic
│   ├── models/                   # Data models
│   └── utils/                    # Utilities
├── frontend/                     # Frontend application
├── data/                         # Data storage
├── scripts/                      # Utility scripts
├── tests/                        # Test suite
├── docs/                         # Documentation
├── docker/                       # Docker configurations
└── .github/                      # CI/CD workflows
```

### Development Commands
```bash
# Run tests
pytest tests/ -v --cov=app

# Code formatting
black app/ tests/
isort app/ tests/

# Linting
flake8 app/ tests/
mypy app/

# Security scan
bandit -r app/
safety check

# Start development server
uvicorn app.main:app --reload

# Database migrations
alembic upgrade head

# Load test data
python scripts/load_sample_data.py
```

### API Endpoints

#### Chat & Conversation
- `POST /api/v1/chat/query` - Process natural language queries
- `GET /api/v1/chat/history` - Retrieve conversation history
- `POST /api/v1/chat/feedback` - Submit user feedback

#### Voice Processing
- `POST /api/v1/voice/transcribe` - Speech-to-text conversion
- `POST /api/v1/voice/synthesize` - Text-to-speech generation
- `GET /api/v1/voice/languages` - Supported languages

#### ARGO Float Data
- `GET /api/v1/floats/search` - Search floats by criteria
- `GET /api/v1/floats/{float_id}` - Get specific float data
- `GET /api/v1/floats/{float_id}/profiles` - Get float profiles

#### Data Visualization
- `POST /api/v1/visualize/map` - Generate map visualizations
- `POST /api/v1/visualize/profile` - Create profile plots
- `POST /api/v1/visualize/timeseries` - Time-series charts

## 🧪 Testing

### Test Categories
- **Unit Tests:** Fast, isolated component tests
- **Integration Tests:** Component interaction tests
- **E2E Tests:** End-to-end workflow validation
- **Performance Tests:** Load and stress testing

### Running Tests
```bash
# All tests
pytest

# Specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=app --cov-report=html

# Performance tests
pytest tests/performance/ -v
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run
docker-compose up -d

# Scale services
docker-compose up -d --scale app=3

# View logs
docker-compose logs -f app
```

### Production Deployment
```bash
# Build production image
docker build -t floatchat:latest .

# Deploy to Railway/Render
# See deployment documentation in docs/deployment/
```

## 📚 Documentation

- [API Documentation](docs/api/) - Comprehensive API reference
- [User Guide](docs/user_guide/) - End-user documentation
- [Developer Guide](docs/developer_guide/) - Development setup and guidelines
- [Deployment Guide](docs/deployment/) - Production deployment instructions

## 🔒 Security

- JWT-based authentication
- API rate limiting
- Input validation and sanitization
- HTTPS enforcement
- Security headers (CSP, HSTS, etc.)
- SQL injection prevention

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **INCOIS** for oceanographic data and domain expertise
- **ARGO Program** for global ocean observation data
- **Google Gemini** for AI/LLM capabilities
- **Open Source Community** for excellent tools and libraries

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/your-org/floatchat/issues)
- **Documentation:** [Project Wiki](https://github.com/your-org/floatchat/wiki)
- **Email:** floatchat-support@your-org.com

---

**Built with ❤️ for the oceanographic community and Smart India Hackathon 2025**
