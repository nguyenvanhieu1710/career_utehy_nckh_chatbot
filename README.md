# Career Chatbot Service

## Tính năng

- **Intent Classification**: Phân loại ý định người dùng (tư vấn chung vs gợi ý công việc)
- **Semantic Search**: Tìm kiếm công việc bằng Milvus Cloud vector search
- **Question Validation**: Kiểm tra câu hỏi có trong phạm vi tư vấn nghề nghiệp
- **Streaming Response**: Trả lời real-time từ Gemini AI (Google GenAI SDK)
- **Category Optimization**: Tối ưu tìm kiếm theo lĩnh vực công việc

## Cấu trúc

```
app/
├── main.py                    # FastAPI application
├── api/v1/chat.py            # Chat endpoints
├── core/                     # Core configuration
├── models/chat.py            # Pydantic models
├── services/                 # Business logic
│   ├── llm_service.py        # Gemini AI integration (SDK 2.0)
│   ├── intent_classifier.py  # Intent classification
│   ├── question_validator.py # Question validation
│   ├── vector_service.py     # Milvus Cloud vector search
│   ├── hybrid_search_service.py # Vector + SQL Hybrid Search
│   └── parallel_hybrid_search.py # Optimized parallel execution
└── prompt_engine/            # Prompt building
    ├── system_prompt.py
    └── prompt_builder.py
```

## Cài đặt

### 1. Local Development

```bash
# Clone và cài đặt dependencies
cd career_utehy_nckh_chatbot
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

### Milvus Statistics

```
GET /api/v1/chat/milvus-stats
```

### Sync Data to Milvus

```
POST /api/v1/chat/sync-milvus
```

### Health Check

```
GET /health
```

## Cấu hình

### Environment Variables

- `MILVUS_URL`: Milvus Cloud endpoint
- `MILVUS_TOKEN`: Milvus Cloud authentication token
- `MILVUS_COLLECTION`: Collection name for job vectors
- `GEMINI_API_KEY`: Google Gemini API Key
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

### Dependencies

- **PostgreSQL**: Primary job data storage
- **Milvus Cloud**: Vector similarity search (Zilliz)
- **Gemini AI**: LLM for response generation and Text Embeddings
- **FastAPI**: Modern web framework
