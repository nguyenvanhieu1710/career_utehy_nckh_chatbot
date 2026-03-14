# Career Chatbot Service

## Tính năng

- **Intent Classification**: Phân loại ý định người dùng (tư vấn chung vs gợi ý công việc)
- **Semantic Search**: Tìm kiếm công việc bằng FAISS vector search
- **Question Validation**: Kiểm tra câu hỏi có trong phạm vi tư vấn nghề nghiệp
- **Streaming Response**: Trả lời real-time từ Ollama LLM
- **Category Optimization**: Tối ưu tìm kiếm theo lĩnh vực công việc

## Cấu trúc

```
app/
├── main.py                    # FastAPI application
├── api/v1/chat.py            # Chat endpoints
├── core/                     # Core configuration
├── models/chat.py            # Pydantic models
├── services/                 # Business logic
│   ├── llm_service.py        # Ollama integration
│   ├── intent_classifier.py  # Intent classification
│   ├── question_validator.py # Question validation
│   ├── vector_service.py     # FAISS vector search
│   └── optimized_vector_service.py
└── prompt_engine/            # Prompt building
    ├── system_prompt.py
    └── prompt_builder.py
```

## Cài đặt

### 1. Local Development

```bash
# Clone và cài đặt dependencies
cd Project/chatbot
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Chỉnh sửa .env với cấu hình của bạn

# Khởi chạy môi trường ảo
.\venv\Scripts\activate

# Chạy service
python run.py
```

## API Endpoints

### Chat Streaming

```
POST /api/v1/chat/stream
Content-Type: application/json

{
  "message": "Tìm việc lập trình Python"
}
```

### FAISS Statistics

```
GET /api/v1/chat/faiss-stats
```

### Rebuild Index

```
POST /api/v1/chat/rebuild-index
```

### Health Check

```
GET /health
```

## Cấu hình

### Environment Variables

- `MONGODB_URL`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name
- `OLLAMA_URL`: Ollama API endpoint
- `OLLAMA_MODEL`: Model name (e.g., llama2)
- `OLLAMA_TIMEOUT`: Request timeout in seconds
- `FAISS_INDEX_DIR`: Directory for FAISS storage
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

### Dependencies

- **MongoDB**: Job data storage
- **Ollama**: LLM for response generation
- **FAISS**: Vector similarity search
- **Sentence Transformers**: Text embeddings
